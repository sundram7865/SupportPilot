from typing import Any

from app.common.enums import AgentDecision


LEGAL_KEYWORDS = {
    "consumer court",
    "legal notice",
    "legal",
    "lawyer",
    "court",
    "police",
    "regulator",
    "file a case",
    "sue",
}

MONEY_OR_ACTION_CATEGORIES = {
    "PAYMENT_ISSUE",
    "REFUND_REQUEST",
    "RETURN_REQUEST",
    "RETURN_REPLACEMENT",
    "DAMAGED_PRODUCT",
    "CANCEL_ORDER",
    "CANCELLATION",
    "REPLACEMENT_REQUEST",
}

ORDER_ID_REQUIRED_CATEGORIES = {
    "ORDER_STATUS",
    "PAYMENT_ISSUE",
    "REFUND_REQUEST",
    "RETURN_REQUEST",
    "RETURN_REPLACEMENT",
    "DAMAGED_PRODUCT",
    "CANCEL_ORDER",
    "INVOICE_REQUEST",
    "WARRANTY_REQUEST",
}


def _as_upper(value: Any, default: str = "") -> str:
    if value is None:
        return default

    return str(value).upper()


def _ticket_text(ticket: dict[str, Any]) -> str:
    return " ".join(
        [
            str(ticket.get("subject") or ""),
            str(ticket.get("description") or ""),
            str(ticket.get("customer_email") or ""),
            str(ticket.get("external_order_id") or ""),
        ]
    ).lower()


def _has_legal_keywords(ticket: dict[str, Any]) -> bool:
    text = _ticket_text(ticket)
    return any(keyword in text for keyword in LEGAL_KEYWORDS)


def _has_order_id(ticket: dict[str, Any]) -> bool:
    return bool(
        ticket.get("external_order_id")
        or ticket.get("order_id")
        or ticket.get("external_reference")
    )


def _has_approval_tool(planned_tools: list[dict[str, Any]]) -> bool:
    for tool in planned_tools:
        if not isinstance(tool, dict):
            continue

        if bool(tool.get("requires_approval")):
            return True

    return False


def _approval_tools_are_resolved(state: dict[str, Any]) -> bool:
    """
    True when every planned tool that required approval has already been
    decided on and (if approved) executed. Prevents decision_node from
    re-flagging "needs approval" for a tool a human has already acted on.
    """
    planned_tools = state.get("planned_tools") or []
    approval_tool_ids = {
        tool.get("tool_execution_id")
        for tool in planned_tools
        if isinstance(tool, dict) and tool.get("requires_approval") and tool.get("tool_execution_id")
    }

    if not approval_tool_ids:
        return True

    if state.get("approval_decision") != "approved":
        return False

    executed_ids = {
        result.get("tool_execution_id")
        for result in (state.get("tool_execution_results") or [])
        if isinstance(result, dict)
    }

    return approval_tool_ids.issubset(executed_ids)


def _resolve_policy_category(state: dict[str, Any]) -> str:
    ticket = state.get("ticket") or {}

    ticket_category = _as_upper(ticket.get("category"), "OTHER")
    detected_category = _as_upper(state.get("detected_category"), "OTHER")

    # Existing ticket LEGAL_RISK must always win.
    if ticket_category == "LEGAL_RISK":
        return "LEGAL_RISK"

    if detected_category == "LEGAL_RISK":
        return "LEGAL_RISK"

    if detected_category not in {"OTHER", "NONE", "NULL", ""}:
        return detected_category

    return ticket_category


def apply_agent_policy(state: dict[str, Any]) -> dict[str, Any]:
    ticket = state.get("ticket") or {}
    planned_tools = state.get("planned_tools") or []

    category = _resolve_policy_category(state)
    risk_level = _as_upper(state.get("risk_level"), "LOW")

    try:
        confidence = float(state.get("classification_confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    approval_already_resolved = _approval_tools_are_resolved(state)

    if _has_legal_keywords(ticket) or category == "LEGAL_RISK":
        return {
            "decision": AgentDecision.ESCALATE_TO_MANAGER.value,
            "policy_reasons": [
                "Legal or regulatory escalation risk was detected.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if risk_level == "CRITICAL":
        return {
            "decision": AgentDecision.ESCALATE_TO_MANAGER.value,
            "policy_reasons": [
                "Critical risk tickets must be escalated.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if category in ORDER_ID_REQUIRED_CATEGORIES and not _has_order_id(ticket):
        return {
            "decision": AgentDecision.ASK_CUSTOMER_FOR_MORE_INFO.value,
            "policy_reasons": [
                "Order ID is required before this ticket can be handled safely.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if _has_approval_tool(planned_tools) and not approval_already_resolved:
        return {
            "decision": AgentDecision.NEEDS_HUMAN_APPROVAL.value,
            "policy_reasons": [
                "At least one planned tool requires human approval.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if _has_approval_tool(planned_tools) and approval_already_resolved:
        return {
            "decision": AgentDecision.NEEDS_HUMAN_APPROVAL.value,
            "policy_reasons": [
                "Tool execution was approved and completed; the customer reply still requires human sign-off.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if category in MONEY_OR_ACTION_CATEGORIES:
        return {
            "decision": AgentDecision.NEEDS_HUMAN_APPROVAL.value,
            "policy_reasons": [
                "Money movement or customer-impacting action requires human approval.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if risk_level == "HIGH":
        return {
            "decision": AgentDecision.NEEDS_HUMAN_APPROVAL.value,
            "policy_reasons": [
                "High-risk ticket requires human approval.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if confidence and confidence < 0.8:
        return {
            "decision": AgentDecision.NEEDS_HUMAN_APPROVAL.value,
            "policy_reasons": [
                f"Classification confidence is low: {confidence}.",
            ],
            "policy_blocked_auto_reply": True,
        }

    if risk_level == "MEDIUM":
        return {
            "decision": AgentDecision.NEEDS_HUMAN_APPROVAL.value,
            "policy_reasons": [
                "Medium-risk ticket requires human review.",
            ],
            "policy_blocked_auto_reply": True,
        }

    return {
        "decision": AgentDecision.AUTO_REPLY_DRAFT.value,
        "policy_reasons": [
            "Low-risk ticket is eligible for AI draft response.",
        ],
        "policy_blocked_auto_reply": False,
    }