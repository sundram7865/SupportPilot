from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.common.enums import AgentDecision, AgentRiskLevel
from app.modules.agent.llm import LLMClient
from app.modules.agent.state import AgentState
from app.modules.knowledge.service import search_knowledge_chunks
from app.modules.tickets.models import Ticket


def load_ticket_context_node(db: Session, state: AgentState) -> AgentState:
    ticket = db.scalar(
        select(Ticket)
        .options(
            selectinload(Ticket.messages),
            selectinload(Ticket.internal_notes),
        )
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
        {
            "sender_type": message.sender_type,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }
        for message in ticket.messages
    ]

    state["internal_notes"] = [
        {
            "body": note.body,
            "created_at": note.created_at.isoformat(),
        }
        for note in ticket.internal_notes
    ]

    return state


def retrieve_knowledge_node(db: Session, state: AgentState) -> AgentState:
    ticket = state["ticket"]

    query = f"""
Subject: {ticket["subject"]}
Description: {ticket["description"]}
Category: {ticket["category"]}
Order ID: {ticket.get("external_order_id") or ""}
""".strip()

    results = search_knowledge_chunks(
        db=db,
        organization_id=state["organization_id"],
        query=query,
        limit=5,
    )

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
        "category": "OTHER",
        "priority": "MEDIUM",
        "confidence": 0.5,
        "summary": "Fallback classification used because LLM response was invalid.",
    }

    result = llm.generate_json(prompt, fallback=fallback)

    allowed_categories = {
        "ORDER_STATUS",
        "PAYMENT_ISSUE",
        "REFUND_REQUEST",
        "RETURN_REQUEST",
        "DAMAGED_PRODUCT",
        "CANCEL_ORDER",
        "INVOICE_REQUEST",
        "WARRANTY_REQUEST",
        "GENERAL_FAQ",
        "LEGAL_RISK",
        "OTHER",
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
    state["risk_reasons"] = [str(reason) for reason in reasons]

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

    return any(
        keyword in lower_text
        for keyword in [
            "consumer court",
            "legal notice",
            "legal",
            "lawyer",
            "court",
            "police",
            "regulator",
            "file a case",
            "sue",
        ]
    )


def _infer_category_from_text(text: str, current_category: str) -> str:
    lower_text = text.lower()
    normalized_current_category = str(current_category or "OTHER").upper()

    if _has_legal_keywords(text):
        return "LEGAL_RISK"

    if any(
        keyword in lower_text
        for keyword in [
            "payment deducted",
            "money deducted",
            "amount deducted",
            "payment debited",
            "money debited",
            "debited",
            "charged",
            "payment failed",
            "payment issue",
            "money cut",
            "amount cut",
        ]
    ):
        return "PAYMENT_ISSUE"

    if "refund" in lower_text:
        return "REFUND_REQUEST"

    if any(
        keyword in lower_text
        for keyword in [
            "where is my order",
            "order status",
            "delivery",
            "shipment",
            "tracking",
            "track order",
            "out for delivery",
        ]
    ):
        return "ORDER_STATUS"

    if any(
        keyword in lower_text
        for keyword in [
            "damaged",
            "broken",
            "wrong product",
            "defective",
            "not working",
        ]
    ):
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


def plan_tools_node(state: AgentState) -> AgentState:
    print("DEBUG_PLAN_TOOLS_NODE_CALLED", flush=True)

    ticket = state.get("ticket", {})

    subject = str(ticket.get("subject") or "")
    description = str(ticket.get("description") or "")

    message_text = " ".join(
        str(message.get("body") or "")
        for message in state.get("messages", [])
        if isinstance(message, dict)
    )

    full_text = f"{subject}\n{description}\n{message_text}"

    raw_category = str(
        state.get("detected_category")
        or ticket.get("category")
        or "OTHER"
    ).upper()

    category = _infer_category_from_text(full_text, raw_category)

    risk_level = str(state.get("risk_level") or "LOW").upper()

    has_legal_risk = category == "LEGAL_RISK" or _has_legal_keywords(full_text)

    # Important fix:
    # CRITICAL should block tools only when it is actually legal/escalation risk.
    # Refund/payment can be high risk, but still should create an approval tool.
    if risk_level == "CRITICAL" and not has_legal_risk:
        print(
            "DEBUG_PLAN_TOOLS_DOWNGRADE_CRITICAL_TO_HIGH_FOR_NON_LEGAL_TICKET",
            flush=True,
        )
        risk_level = "HIGH"
        state["risk_level"] = "HIGH"

    order_id = (
        ticket.get("external_order_id")
        or ticket.get("order_id")
        or ticket.get("external_reference")
        or _extract_order_id_from_text(full_text)
    )

    planned_tools: list[dict] = []

    print("DEBUG_PLAN_TOOLS_RAW_CATEGORY:", raw_category, flush=True)
    print("DEBUG_PLAN_TOOLS_INFERRED_CATEGORY:", category, flush=True)
    print("DEBUG_PLAN_TOOLS_RISK:", risk_level, flush=True)
    print("DEBUG_PLAN_TOOLS_ORDER_ID:", order_id, flush=True)
    print("DEBUG_PLAN_TOOLS_FULL_TEXT:", full_text[:500], flush=True)

    if has_legal_risk:
        state["planned_tools"] = []
        state["decision"] = "ESCALATE_TO_MANAGER"
        state["reasoning_summary"] = (
            "Legal or critical escalation risk detected, so no tools were planned."
        )

        print("DEBUG_PLAN_TOOLS_EARLY_RETURN_LEGAL_RISK", flush=True)
        print("DEBUG_PLAN_TOOLS_RESULT:", [], flush=True)

        return state

    order_context_categories = {
        "ORDER_STATUS",
        "PAYMENT_ISSUE",
        "REFUND_REQUEST",
        "RETURN_REQUEST",
        "DAMAGED_PRODUCT",
        "CANCEL_ORDER",
        "INVOICE_REQUEST",
        "WARRANTY_REQUEST",
    }

    if category in order_context_categories:
        if not order_id:
            state["planned_tools"] = []
            state["decision"] = "ASK_CUSTOMER_FOR_MORE_INFO"
            state["reasoning_summary"] = (
                "Order ID is required before running UrbanKart tools."
            )

            print("DEBUG_PLAN_TOOLS_EARLY_RETURN_MISSING_ORDER_ID", flush=True)
            print("DEBUG_PLAN_TOOLS_RESULT:", [], flush=True)

            return state

        planned_tools.append(
            {
                "tool_name": "urbankart_get_order_context",
                "risk_level": "LOW",
                "requires_approval": False,
                "reason": "Fetch verified order, payment, shipment, and customer context.",
                "args": {
                    "order_id": order_id,
                },
            }
        )

    if category in {"PAYMENT_ISSUE", "REFUND_REQUEST"} and order_id:
        planned_tools.append(
            {
                "tool_name": "urbankart_request_refund",
                "risk_level": "HIGH",
                "requires_approval": True,
                "reason": "Refund/payment issue requires human approval before execution.",
                "args": {
                    "order_id": order_id,
                },
            }
        )

    if category == "DAMAGED_PRODUCT" and order_id:
        planned_tools.append(
            {
                "tool_name": "urbankart_request_replacement",
                "risk_level": "HIGH",
                "requires_approval": True,
                "reason": "Damaged product replacement requires human approval before execution.",
                "args": {
                    "order_id": order_id,
                    "reason": "Customer reported damaged product.",
                },
            }
        )

    state["planned_tools"] = planned_tools

    if planned_tools:
        state["reasoning_summary"] = (
            f"Planned {len(planned_tools)} tool(s) for category {category}."
        )
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

    prompt = f"""
You are SupportPilot decision engine.

Return ONLY valid JSON. Do not include markdown. Do not include explanation outside JSON.

Allowed decisions:
- AUTO_REPLY_DRAFT
- NEEDS_HUMAN_APPROVAL
- ESCALATE_TO_MANAGER
- ASK_CUSTOMER_FOR_MORE_INFO
- NO_ACTION

Decision rules:
- If risk_level is CRITICAL → ESCALATE_TO_MANAGER.
- If detected_category is LEGAL_RISK → ESCALATE_TO_MANAGER.
- If planned tools include any requires_approval=true → NEEDS_HUMAN_APPROVAL.
- If ticket involves refund, payment, cancellation, replacement, money movement → NEEDS_HUMAN_APPROVAL.
- If required information is missing, like order_id for order/payment/refund issue → ASK_CUSTOMER_FOR_MORE_INFO.
- If low risk and enough information exists → AUTO_REPLY_DRAFT.
- If unsure → NEEDS_HUMAN_APPROVAL.

Return JSON in this exact shape:
{{
  "decision": "NEEDS_HUMAN_APPROVAL",
  "reasoning_summary": "short reason"
}}

Category: {state.get("detected_category")}
Priority: {state.get("detected_priority")}
Risk level: {state.get("risk_level")}
Risk reasons: {state.get("risk_reasons")}
Planned tools: {state.get("planned_tools")}
Draft response: {state.get("draft_response")}
Ticket: {state.get("ticket")}
""".strip()

    fallback = {
        "decision": "NEEDS_HUMAN_APPROVAL",
        "reasoning_summary": "Fallback decision used because LLM response was invalid.",
    }

    result = llm.generate_json(prompt, fallback=fallback)

    allowed_decisions = {
        "AUTO_REPLY_DRAFT",
        "NEEDS_HUMAN_APPROVAL",
        "ESCALATE_TO_MANAGER",
        "ASK_CUSTOMER_FOR_MORE_INFO",
        "NO_ACTION",
    }

    decision = str(result.get("decision", "NEEDS_HUMAN_APPROVAL")).upper()

    if decision not in allowed_decisions:
        decision = "NEEDS_HUMAN_APPROVAL"

    state["decision"] = decision
    state["reasoning_summary"] = str(
        result.get(
            "reasoning_summary",
            state.get("reasoning_summary", ""),
        )
    )

    return state