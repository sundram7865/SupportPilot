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
You classify customer support tickets.

Return JSON only:
{{
  "category": "ORDER_STATUS | PAYMENT_ISSUE | REFUND_REQUEST | RETURN_REPLACEMENT | PRODUCT_QUESTION | DELIVERY_ISSUE | ACCOUNT_ISSUE | COMPLAINT | LEGAL_RISK | OTHER",
  "priority": "LOW | MEDIUM | HIGH | URGENT",
  "summary": "short summary"
}}

Ticket:
Subject: {ticket["subject"]}
Description: {ticket["description"]}
Current category: {ticket["category"]}
Current priority: {ticket["priority"]}
"""

    result = llm.generate_json(prompt)

    state["detected_category"] = result.get("category", "OTHER")
    state["detected_priority"] = result.get("priority", "MEDIUM")
    state["reasoning_summary"] = result.get("summary", "")

    return state


def detect_risk_node(state: AgentState) -> AgentState:
    llm = LLMClient()
    ticket = state["ticket"]
    context = state.get("knowledge_context", [])

    prompt = f"""
You are detecting risk for a customer support ticket.

Return JSON only:
{{
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "risk_reasons": ["reason 1", "reason 2"]
}}

Ticket:
Subject: {ticket["subject"]}
Description: {ticket["description"]}
Detected category: {state.get("detected_category")}
Knowledge context:
{context}
"""

    result = llm.generate_json(prompt)

    state["risk_level"] = result.get("risk_level", AgentRiskLevel.LOW.value)
    state["risk_reasons"] = result.get("risk_reasons", [])

    return state


def plan_tools_node(state: AgentState) -> AgentState:
    ticket = state["ticket"]
    category = state.get("detected_category")

    planned_tools: list[dict] = []

    if ticket.get("external_order_id") and category in {
        "ORDER_STATUS",
        "PAYMENT_ISSUE",
        "REFUND_REQUEST",
        "DELIVERY_ISSUE",
    }:
        planned_tools.append(
            {
                "tool_name": "urbankart_get_order_context",
                "reason": "Ticket contains external order id and requires order/payment/shipment context.",
                "risk": "READ_ONLY",
                "requires_approval": False,
                "args": {
                    "order_id": ticket.get("external_order_id"),
                },
            }
        )

    if category in {"PAYMENT_ISSUE", "REFUND_REQUEST"}:
        planned_tools.append(
            {
                "tool_name": "urbankart_request_refund",
                "reason": "Potential refund action may be needed after verification.",
                "risk": "WRITE_ACTION",
                "requires_approval": True,
                "args": {
                    "order_id": ticket.get("external_order_id"),
                },
            }
        )

    state["planned_tools"] = planned_tools

    return state


def draft_response_node(state: AgentState) -> AgentState:
    llm = LLMClient()
    ticket = state["ticket"]

    prompt = f"""
Draft a customer support response.

Rules:
- Be polite and concise.
- Do not claim refund is completed.
- Do not say a risky action has been performed.
- If legal risk exists, say the case is escalated for review.
- Use provided knowledge context only as policy guidance.

Ticket:
{ticket}

Detected category: {state.get("detected_category")}
Detected priority: {state.get("detected_priority")}
Risk level: {state.get("risk_level")}
Risk reasons: {state.get("risk_reasons")}
Knowledge context: {state.get("knowledge_context")}
Planned tools: {state.get("planned_tools")}
"""

    state["draft_response"] = llm.generate_text(prompt)

    return state


def decision_node(state: AgentState) -> AgentState:
    llm = LLMClient()

    prompt = f"""
Make a support automation decision.

Return JSON only:
{{
  "decision": "AUTO_REPLY_DRAFT | NEEDS_HUMAN_APPROVAL | ESCALATE_TO_MANAGER | ASK_CUSTOMER_FOR_MORE_INFO | NO_ACTION",
  "reasoning_summary": "short reason"
}}

Category: {state.get("detected_category")}
Priority: {state.get("detected_priority")}
Risk level: {state.get("risk_level")}
Risk reasons: {state.get("risk_reasons")}
Planned tools: {state.get("planned_tools")}
Draft response: {state.get("draft_response")}
"""

    result = llm.generate_json(prompt)

    state["decision"] = result.get("decision", AgentDecision.NO_ACTION.value)
    state["reasoning_summary"] = result.get(
        "reasoning_summary",
        state.get("reasoning_summary", ""),
    )

    return state