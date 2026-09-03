import asyncio
import re
import threading
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from langgraph.types import interrupt

from app.common.enums import (
    AgentDecision,
    AgentRiskLevel,
    ToolApprovalStatus,
    ToolExecutionStatus,
)
from app.modules.agent.llm import LLMClient
from app.modules.agent.policy import apply_agent_policy
from app.modules.agent.state import AgentState
from app.modules.knowledge.service import search_knowledge_chunks
from app.modules.organizations.models import Organization
from app.modules.tickets.models import Ticket
from app.modules.tools.models import ToolExecution
from app.modules.tools.service import execute_approved_tool_execution


def _run_async_from_sync(coro):
    """
    Run an async coroutine from synchronous code, regardless of whether
    the calling thread already has a running event loop.

    - No running loop in this thread (e.g. run_ticket_agent's sync route
      handler, executed in FastAPI's worker thread pool): asyncio.run()
      is safe and direct.
    - A running loop already exists in this thread (e.g. approve_approval,
      an async route, calling down through sync resume_agent_after_approval
      into this same sync node): asyncio.run() would raise
      "cannot be called from a running event loop". Instead, run the
      coroutine in a separate thread with its own fresh event loop, and
      block this thread until it completes.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop running in this thread — safe to drive one directly.
        return asyncio.run(coro)

    # A loop is already running in this thread. Spin up a dedicated
    # thread with its own loop, run the coroutine there, and wait.
    result_holder: dict = {}
    error_holder: dict = {}

    def _runner():
        try:
            result_holder["value"] = asyncio.run(coro)
        except Exception as exc:  # noqa: BLE001
            error_holder["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in error_holder:
        raise error_holder["error"]

    return result_holder["value"]


def load_ticket_context_node(db: Session, state: AgentState) -> AgentState:
    ticket = db.scalar(
        select(Ticket)
        .options(selectinload(Ticket.messages), selectinload(Ticket.internal_notes))
        .where(Ticket.id == state["ticket_id"])
        .where(Ticket.organization_id == state["organization_id"])
    )
    if not ticket:
        raise ValueError("Ticket not found for agent run.")

    state["ticket"] = {
        "id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "category": ticket.category,
        "customer_name": ticket.customer_name,
        "customer_email": ticket.customer_email,
        "external_order_id": ticket.external_order_id,
    }
    state["messages"] = [
        {"sender_type": m.sender_type, "body": m.body, "created_at": m.created_at.isoformat()}
        for m in ticket.messages
    ]
    state["internal_notes"] = [
        {"body": n.body, "created_at": n.created_at.isoformat()}
        for n in ticket.internal_notes
    ]
    return state


def retrieve_knowledge_node(db: Session, state: AgentState) -> AgentState:
    ticket = state["ticket"]
    query = f"Subject: {ticket['subject']}\nDescription: {ticket['description']}\nCategory: {ticket['category']}\nOrder ID: {ticket.get('external_order_id') or ''}"
    results = search_knowledge_chunks(db, state["organization_id"], query, limit=5)
    state["knowledge_context"] = [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(document.id),
            "document_title": document.title,
            "document_type": document.document_type,
            "content": chunk.content,
            "score": score,
        }
        for chunk, document, score in results
    ]
    return state


def classify_ticket_node(state: AgentState) -> AgentState:
    llm = LLMClient()
    ticket = state["ticket"]

    ticket_category = str(ticket.get("category") or "").upper()
    ticket_priority = str(ticket.get("priority") or "").upper()

    if ticket_category == "LEGAL_RISK":
        state["detected_category"] = "LEGAL_RISK"
        state["detected_priority"] = "URGENT" if ticket_priority == "URGENT" else "HIGH"
        state["reasoning_summary"] = "Ticket was already marked as LEGAL_RISK, so classifier preserved legal escalation category."
        state["classification_confidence"] = 0.99
        return state

    prompt = f"""
You are SupportPilot, an AI support ticket classifier for an e-commerce/D2C support system.

Return ONLY valid JSON. Do not include markdown. Do not include explanation outside JSON.

Allowed categories:
- ORDER_STATUS
- PAYMENT_ISSUE
- REFUND_REQUEST
- RETURN_REQUEST
- DAMAGED_PRODUCT
- CANCEL_ORDER
- INVOICE_REQUEST
- WARRANTY_REQUEST
- GENERAL_FAQ
- LEGAL_RISK
- OTHER

Allowed priorities:
- LOW
- MEDIUM
- HIGH
- URGENT

Classification rules:
- If current category is LEGAL_RISK, return LEGAL_RISK and URGENT.
- If customer asks where order is, shipment, tracking, delivery status → ORDER_STATUS.
- If customer says payment deducted, failed payment, charged, money debited → PAYMENT_ISSUE.
- If customer asks refund explicitly → REFUND_REQUEST unless it is mainly payment failure.
- If customer says damaged/broken/wrong product → DAMAGED_PRODUCT.
- If customer asks invoice/bill → INVOICE_REQUEST.
- If customer mentions legal notice, consumer court, lawyer, complaint to authority → LEGAL_RISK and URGENT.
- Use OTHER only when no category fits.

Return JSON in this exact shape:
{{
  "category": "ORDER_STATUS",
  "priority": "MEDIUM",
  "confidence": 0.0,
  "summary": "short factual summary"
}}

Ticket:
Subject: {ticket["subject"]}
Description: {ticket["description"]}
Current category: {ticket["category"]}
Current priority: {ticket["priority"]}
Customer email: {ticket.get("customer_email")}
Order ID: {ticket.get("external_order_id")}
""".strip()

    fallback = {
        "category": ticket_category if ticket_category else "OTHER",
        "priority": ticket_priority if ticket_priority else "MEDIUM",
        "confidence": 0.5,
        "summary": "Fallback classification used because LLM response was invalid.",
    }
    result = llm.generate_json(prompt, fallback=fallback)

    allowed_categories = {
        "ORDER_STATUS", "PAYMENT_ISSUE", "REFUND_REQUEST", "RETURN_REQUEST",
        "DAMAGED_PRODUCT", "CANCEL_ORDER", "INVOICE_REQUEST", "WARRANTY_REQUEST",
        "GENERAL_FAQ", "LEGAL_RISK", "OTHER",
    }
    allowed_priorities = {"LOW", "MEDIUM", "HIGH", "URGENT"}
    category = str(result.get("category", "OTHER")).upper()
    priority = str(result.get("priority", "MEDIUM")).upper()
    if category not in allowed_categories:
        category = "OTHER"
    if priority not in allowed_priorities:
        priority = "MEDIUM"

    state["detected_category"] = category
    state["detected_priority"] = priority
    state["reasoning_summary"] = str(result.get("summary", ""))
    state["classification_confidence"] = float(result.get("confidence", 0.5))
    return state


def detect_risk_node(state: AgentState) -> AgentState:
    llm = LLMClient()
    ticket = state["ticket"]
    context = state.get("knowledge_context", [])

    ticket_category = str(ticket.get("category") or "").upper()
    detected_category = str(state.get("detected_category") or "").upper()

    if ticket_category == "LEGAL_RISK" or detected_category == "LEGAL_RISK":
        state["risk_level"] = "CRITICAL"
        state["risk_reasons"] = ["Ticket is marked as LEGAL_RISK and must be escalated."]
        return state

    prompt = f"""
You are SupportPilot risk detection for an e-commerce customer support platform.

Return ONLY valid JSON. Do not include markdown. Do not include explanation outside JSON.

Allowed risk levels:
- LOW
- MEDIUM
- HIGH
- CRITICAL

Risk rules:
- Legal threats, consumer court, lawyer, police, regulator, public legal complaint → CRITICAL.
- If current/detected category is LEGAL_RISK → CRITICAL.
- Refund, payment deducted, money debited, replacement, cancellation → HIGH.
- Angry customer without legal/money impact → MEDIUM.
- Basic order status or FAQ → LOW.
- Never mark normal refund/payment issue as CRITICAL unless legal keywords are present.
- If unsure, choose MEDIUM.

Return JSON in this exact shape:
{{
  "risk_level": "LOW",
  "risk_reasons": ["short reason"]
}}

Ticket:
Subject: {ticket["subject"]}
Description: {ticket["description"]}
Current category: {ticket.get("category")}
Detected category: {state.get("detected_category")}
Detected priority: {state.get("detected_priority")}
Knowledge context:
{context}
""".strip()

    fallback = {
        "risk_level": "MEDIUM",
        "risk_reasons": ["Fallback risk used because LLM response was invalid."],
    }
    result = llm.generate_json(prompt, fallback=fallback)

    allowed_risk_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    risk_level = str(result.get("risk_level", "MEDIUM")).upper()
    if risk_level not in allowed_risk_levels:
        risk_level = "MEDIUM"
    reasons = result.get("risk_reasons", [])
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    state["risk_level"] = risk_level
    state["risk_reasons"] = [str(r) for r in reasons]
    return state


def _extract_order_id_from_text(text: str) -> str | None:
    if not text:
        return None
    match = re.search(r"\bORD[-_ ]?\d+\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).replace(" ", "-").replace("_", "-").upper()


def _has_legal_keywords(text: str) -> bool:
    lower_text = text.lower()
    return any(kw in lower_text for kw in [
        "consumer court", "legal notice", "legal", "lawyer", "court",
        "police", "regulator", "file a case", "sue",
    ])


def _infer_category_from_text(text: str, current_category: str) -> str:
    lower_text = text.lower()
    normalized_current_category = str(current_category or "OTHER").upper()
    if normalized_current_category == "LEGAL_RISK":
        return "LEGAL_RISK"
    if _has_legal_keywords(text):
        return "LEGAL_RISK"
    if any(kw in lower_text for kw in [
        "payment deducted", "money deducted", "amount deducted", "payment debited",
        "money debited", "debited", "charged", "payment failed", "payment issue",
        "money cut", "amount cut",
    ]):
        return "PAYMENT_ISSUE"
    if "refund" in lower_text:
        return "REFUND_REQUEST"
    if any(kw in lower_text for kw in [
        "where is my order", "order status", "delivery", "shipment",
        "tracking", "track order", "out for delivery",
    ]):
        return "ORDER_STATUS"
    if any(kw in lower_text for kw in [
        "damaged", "broken", "wrong product", "defective", "not working",
    ]):
        return "DAMAGED_PRODUCT"
    if "cancel" in lower_text or "cancellation" in lower_text:
        return "CANCEL_ORDER"
    if "invoice" in lower_text or "bill" in lower_text:
        return "INVOICE_REQUEST"
    if "warranty" in lower_text:
        return "WARRANTY_REQUEST"
    if normalized_current_category not in {"OTHER", "NONE", "NULL", ""}:
        return normalized_current_category
    return "OTHER"


def plan_tools_node(db: Session, state: AgentState) -> AgentState:
    print("DEBUG_PLAN_TOOLS_NODE_CALLED", flush=True)
    ticket = state.get("ticket", {})
    subject = str(ticket.get("subject") or "")
    description = str(ticket.get("description") or "")
    message_text = " ".join(
        str(m.get("body") or "")
        for m in state.get("messages", [])
        if isinstance(m, dict)
    )
    full_text = f"{subject}\n{description}\n{message_text}"

    ticket_category = str(ticket.get("category") or "OTHER").upper()
    detected_category = str(state.get("detected_category") or "OTHER").upper()

    if ticket_category == "LEGAL_RISK":
        raw_category = "LEGAL_RISK"
    elif detected_category not in {"OTHER", "NONE", "NULL", ""}:
        raw_category = detected_category
    else:
        raw_category = ticket_category

    category = _infer_category_from_text(full_text, raw_category)
    risk_level = str(state.get("risk_level") or "LOW").upper()

    has_legal_risk = (
        ticket_category == "LEGAL_RISK"
        or detected_category == "LEGAL_RISK"
        or category == "LEGAL_RISK"
        or _has_legal_keywords(full_text)
    )
    if risk_level == "CRITICAL" and not has_legal_risk:
        risk_level = "HIGH"
        state["risk_level"] = "HIGH"

    order_id = (
        ticket.get("external_order_id")
        or ticket.get("order_id")
        or ticket.get("external_reference")
        or _extract_order_id_from_text(full_text)
    )

    planned_tools = []

    print("DEBUG_PLAN_TOOLS_TICKET_CATEGORY:", ticket_category, flush=True)
    print("DEBUG_PLAN_TOOLS_DETECTED_CATEGORY:", detected_category, flush=True)
    print("DEBUG_PLAN_TOOLS_RAW_CATEGORY:", raw_category, flush=True)
    print("DEBUG_PLAN_TOOLS_INFERRED_CATEGORY:", category, flush=True)
    print("DEBUG_PLAN_TOOLS_RISK:", risk_level, flush=True)
    print("DEBUG_PLAN_TOOLS_ORDER_ID:", order_id, flush=True)
    print("DEBUG_PLAN_TOOLS_FULL_TEXT:", full_text[:500], flush=True)

    if has_legal_risk:
        state["planned_tools"] = []
        state["decision"] = "ESCALATE_TO_MANAGER"
        state["reasoning_summary"] = "Legal or critical escalation risk detected, so no tools were planned."
        print("DEBUG_PLAN_TOOLS_EARLY_RETURN_LEGAL_RISK", flush=True)
        print("DEBUG_PLAN_TOOLS_RESULT:", [], flush=True)
        return state

    order_context_categories = {
        "ORDER_STATUS", "PAYMENT_ISSUE", "REFUND_REQUEST", "RETURN_REQUEST",
        "RETURN_REPLACEMENT", "DAMAGED_PRODUCT", "CANCEL_ORDER",
        "INVOICE_REQUEST", "WARRANTY_REQUEST",
    }
    if category in order_context_categories:
        if not order_id:
            state["planned_tools"] = []
            state["decision"] = "ASK_CUSTOMER_FOR_MORE_INFO"
            state["reasoning_summary"] = "Order ID is required before running UrbanKart tools."
            print("DEBUG_PLAN_TOOLS_EARLY_RETURN_MISSING_ORDER_ID", flush=True)
            print("DEBUG_PLAN_TOOLS_RESULT:", [], flush=True)
            return state
        planned_tools.append({
            "tool_name": "urbankart_get_order_context",
            "risk_level": "LOW",
            "requires_approval": False,
            "reason": "Fetch verified order, payment, shipment, and customer context.",
            "args": {"order_id": order_id},
        })

    if category in {"PAYMENT_ISSUE", "REFUND_REQUEST"} and order_id:
        planned_tools.append({
            "tool_name": "urbankart_request_refund",
            "risk_level": "HIGH",
            "requires_approval": True,
            "reason": "Refund/payment issue requires human approval before execution.",
            "args": {"order_id": order_id},
        })

    if category == "DAMAGED_PRODUCT" and order_id:
        planned_tools.append({
            "tool_name": "urbankart_request_replacement",
            "risk_level": "HIGH",
            "requires_approval": True,
            "reason": "Damaged product replacement requires human approval before execution.",
            "args": {"order_id": order_id, "reason": "Customer reported damaged product."},
        })

    # Create ToolExecution records for tools that require approval
    for tool in planned_tools:
        if tool.get("requires_approval", False):
            execution = ToolExecution(
                organization_id=UUID(state["organization_id"]),
                ticket_id=UUID(state["ticket_id"]),
                agent_run_id=UUID(state["agent_run_id"]),
                tool_name=tool["tool_name"],
                risk_level=tool["risk_level"],
                status=ToolExecutionStatus.BLOCKED_APPROVAL_REQUIRED.value,
                approval_status=ToolApprovalStatus.PENDING.value,
                input_args=tool.get("args", {}),
            )
            db.add(execution)
            db.flush()
            tool["tool_execution_id"] = str(execution.id)

    state["planned_tools"] = planned_tools
    if planned_tools:
        state["reasoning_summary"] = f"Planned {len(planned_tools)} tool(s) for category {category}."
    else:
        state["reasoning_summary"] = f"No tools planned for category {category}."
    print("DEBUG_PLAN_TOOLS_RESULT:", planned_tools, flush=True)
    return state


def draft_response_node(state: AgentState) -> AgentState:
    llm = LLMClient()
    ticket = state["ticket"]

    prompt = f"""
You are SupportPilot, drafting a customer support response for UrbanKart.

Write only the customer-facing message. Do not include JSON.

Strict safety rules:
- Do not claim a refund has been completed.
- Do not claim a replacement has been created.
- Do not claim order data was checked unless tool results are present.
- Do not mention internal tools, agents, policies, risk levels, or approvals.
- For legal risk, say the issue is being escalated for review.
- For refund/payment cases, say the team will verify payment/order details.
- Keep tone professional, calm, concise.
- Maximum 120 words.

Ticket:
{ticket}

Messages:
{state.get("messages", [])}

Detected category: {state.get("detected_category")}
Detected priority: {state.get("detected_priority")}
Risk level: {state.get("risk_level")}
Risk reasons: {state.get("risk_reasons")}
Knowledge context: {state.get("knowledge_context")}
Planned tools: {state.get("planned_tools")}
""".strip()

    fallback = (
        "Hi, thanks for contacting UrbanKart support. We have received your request "
        "and our team will review it shortly. We will share an update as soon as we "
        "have verified the relevant details."
    )
    state["draft_response"] = llm.generate_text(prompt, fallback=fallback)
    return state


def decision_node(state: AgentState) -> AgentState:
    llm = LLMClient()
    policy_result = apply_agent_policy(state)

    policy_decision = policy_result["decision"]
    policy_reasons = policy_result.get("policy_reasons", [])
    policy_blocked_auto_reply = bool(policy_result.get("policy_blocked_auto_reply", False))

    state["policy_reasons"] = policy_reasons
    state["policy_blocked_auto_reply"] = policy_blocked_auto_reply

    if policy_decision in {
        AgentDecision.ESCALATE_TO_MANAGER.value,
        AgentDecision.NEEDS_HUMAN_APPROVAL.value,
        AgentDecision.ASK_CUSTOMER_FOR_MORE_INFO.value,
    }:
        state["decision"] = policy_decision
        state["reasoning_summary"] = " ".join(policy_reasons)
        return state

    prompt = f"""
You are SupportPilot decision engine.

Return ONLY valid JSON. Do not include markdown. Do not include explanation outside JSON.

Allowed decisions:
- AUTO_REPLY_DRAFT
- NEEDS_HUMAN_APPROVAL
- ESCALATE_TO_MANAGER
- ASK_CUSTOMER_FOR_MORE_INFO
- NO_ACTION

Important:
Backend policy already found this ticket safe for low-risk AI draft handling.
You may choose AUTO_REPLY_DRAFT or NEEDS_HUMAN_APPROVAL.
Do not choose ESCALATE_TO_MANAGER unless new legal risk is obvious.
Do not choose AUTO_REPLY_DRAFT for refund, payment, cancellation, replacement, or legal risk.

Return JSON in this exact shape:
{{
  "decision": "AUTO_REPLY_DRAFT",
  "reasoning_summary": "short reason"
}}

Category: {state.get("detected_category")}
Priority: {state.get("detected_priority")}
Risk level: {state.get("risk_level")}
Risk reasons: {state.get("risk_reasons")}
Classification confidence: {state.get("classification_confidence")}
Planned tools: {state.get("planned_tools")}
Policy reasons: {policy_reasons}
Draft response: {state.get("draft_response")}
Ticket: {state.get("ticket")}
""".strip()

    fallback = {
        "decision": policy_decision,
        "reasoning_summary": "Fallback decision used after policy check.",
    }
    result = llm.generate_json(prompt, fallback=fallback)

    allowed_decisions = {
        AgentDecision.AUTO_REPLY_DRAFT.value,
        AgentDecision.NEEDS_HUMAN_APPROVAL.value,
        AgentDecision.ESCALATE_TO_MANAGER.value,
        AgentDecision.ASK_CUSTOMER_FOR_MORE_INFO.value,
        AgentDecision.NO_ACTION.value,
    }
    decision = str(result.get("decision", policy_decision)).upper()
    if decision not in allowed_decisions:
        decision = policy_decision
    if decision == AgentDecision.NO_ACTION.value:
        decision = AgentDecision.NEEDS_HUMAN_APPROVAL.value

    state["decision"] = decision
    state["reasoning_summary"] = str(result.get("reasoning_summary", " ".join(policy_reasons)))
    return state


def approval_node(db: Session, state: AgentState) -> AgentState:
    approval_tools = [
        t for t in state.get("planned_tools", [])
        if t.get("requires_approval", False)
    ]
    if not approval_tools:
        state["approval_decision"] = "approved"
        return state

    payload = {
        "ticket_id": state["ticket_id"],
        "agent_run_id": state["agent_run_id"],
        "tools": approval_tools,
        "reason": "These tools require human approval before execution.",
        "risk_level": state.get("risk_level"),
        "category": state.get("detected_category"),
    }

    # Pause graph here; resumed via Command(resume=...) which makes
    # interrupt() return the resume value directly on re-entry.
    decision = interrupt(payload)

    state["approval_decision"] = "approved" if decision.get("approved") else "rejected"
    state["approval_reason"] = decision.get("reason")
    return state


def execute_tools_node(db: Session, state: AgentState) -> AgentState:
    if state.get("approval_decision") != "approved":
        state["tool_execution_results"] = []
        return state

    organization = db.get(Organization, UUID(state["organization_id"]))
    if not organization:
        raise ValueError(f"Organization {state['organization_id']} not found")

    approved_by_user_id = UUID(state["user_id"]) if state.get("user_id") else None

    results = []
    for tool in state.get("planned_tools", []):
        if not tool.get("requires_approval", False):
            continue

        execution_id = UUID(tool["tool_execution_id"])
        execution = db.get(ToolExecution, execution_id)
        if not execution:
            raise ValueError(f"Tool execution {execution_id} not found")

        # Runs the real UrbanKart tool call (async) safely from this sync
        # node, whether or not the calling thread already has an event
        # loop running (see _run_async_from_sync docstring).
        execution = _run_async_from_sync(
            execute_approved_tool_execution(
                db=db,
                organization=organization,
                execution=execution,
                approved_by_user_id=approved_by_user_id,
            )
        )

        results.append({
            "tool_execution_id": str(execution.id),
            "status": execution.status,
            "output": execution.output_json,
        })

    state["tool_execution_results"] = results
    return state