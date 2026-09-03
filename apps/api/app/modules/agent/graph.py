from uuid import UUID

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver  # <-- changed
from sqlalchemy.orm import Session

from app.modules.agent.nodes import (
    classify_ticket_node,
    decision_node,
    detect_risk_node,
    draft_response_node,
    load_ticket_context_node,
    plan_tools_node,
    retrieve_knowledge_node,
    approval_node,
    execute_tools_node,
)
from app.modules.agent.state import AgentState
from app.modules.agent.step_logger import run_logged_step
from app.core.config import get_settings


# Global checkpointer instance, lazily initialised
import re

_checkpointer = None
_checkpointer_cm = None

def _get_checkpointer():
    global _checkpointer, _checkpointer_cm
    if _checkpointer is None:
        settings = get_settings()
        db_url = settings.database_url

        # Convert SQLAlchemy URL to plain PostgreSQL URL
        if db_url.startswith("postgresql+psycopg://"):
            db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

        # Keep the context manager to close later
        _checkpointer_cm = PostgresSaver.from_conn_string(db_url)
        _checkpointer = _checkpointer_cm.__enter__()
        _checkpointer.setup()
    return _checkpointer


def build_ticket_agent_graph(db: Session):
    graph = StateGraph(AgentState)

    def ids(state: AgentState):
        return {
            "organization_id": UUID(state["organization_id"]),
            "agent_run_id": UUID(state["agent_run_id"]),
            "ticket_id": UUID(state["ticket_id"]),
        }

    # ---- Step wrappers (unchanged except for checkpointer) ----
    def load_context_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="load_ticket_context",
            input_json={"ticket_id": state["ticket_id"]},
            fn=lambda: load_ticket_context_node(db, state),
        )

    def retrieve_knowledge_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="retrieve_knowledge",
            input_json={"ticket": state.get("ticket")},
            fn=lambda: retrieve_knowledge_node(db, state),
        )

    def classify_ticket_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="classify_ticket",
            input_json={"ticket": state.get("ticket")},
            fn=lambda: classify_ticket_node(state),
        )

    def detect_risk_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="detect_risk",
            input_json={
                "ticket": state.get("ticket"),
                "category": state.get("detected_category"),
            },
            fn=lambda: detect_risk_node(state),
        )

    def plan_tools_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="plan_tools",
            input_json={
                "ticket": state.get("ticket"),
                "category": state.get("detected_category"),
            },
            fn=lambda: plan_tools_node(db, state),
        )

    def draft_response_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="draft_response",
            input_json={
                "ticket": state.get("ticket"),
                "knowledge_context": state.get("knowledge_context"),
            },
            fn=lambda: draft_response_node(state),
        )

    def decision_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="decision",
            input_json={
                "risk_level": state.get("risk_level"),
                "classification_confidence": state.get("classification_confidence"),
                "planned_tools": state.get("planned_tools"),
                "category": state.get("detected_category"),
            },
            fn=lambda: decision_node(state),
        )

    # ---- Approval and tool execution wrappers ----
    def approval_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="approval",
            input_json={"planned_tools": state.get("planned_tools")},
            fn=lambda: approval_node(db, state),
        )

    def execute_tools_step(state: AgentState) -> AgentState:
        parsed_ids = ids(state)
        return run_logged_step(
            db=db,
            organization_id=parsed_ids["organization_id"],
            agent_run_id=parsed_ids["agent_run_id"],
            ticket_id=parsed_ids["ticket_id"],
            step_name="execute_tools",
            input_json={
                "approval_decision": state.get("approval_decision"),
                "planned_tools": state.get("planned_tools"),
            },
            fn=lambda: execute_tools_node(db, state),
        )

    # ---- Register all nodes ----
    graph.add_node("load_context_step", load_context_step)
    graph.add_node("retrieve_knowledge_step", retrieve_knowledge_step)
    graph.add_node("classify_ticket_step", classify_ticket_step)
    graph.add_node("detect_risk_step", detect_risk_step)
    graph.add_node("plan_tools_step", plan_tools_step)
    graph.add_node("draft_response_step", draft_response_step)
    graph.add_node("decision_step", decision_step)
    graph.add_node("approval_node", approval_step)
    graph.add_node("execute_tools_node", execute_tools_step)

    # ---- Entry point and base edges ----
    graph.set_entry_point("load_context_step")
    graph.add_edge("load_context_step", "retrieve_knowledge_step")
    graph.add_edge("retrieve_knowledge_step", "classify_ticket_step")
    graph.add_edge("classify_ticket_step", "detect_risk_step")
    graph.add_edge("detect_risk_step", "plan_tools_step")

    # ---- Conditional routing ----
    def needs_approval(state: AgentState) -> bool:
        return any(
            tool.get("requires_approval", False)
            for tool in state.get("planned_tools", [])
        )

    graph.add_conditional_edges(
        "plan_tools_step",
        lambda state: "approval_node" if needs_approval(state) else "draft_response_step",
        {
            "approval_node": "approval_node",
            "draft_response_step": "draft_response_step",
        },
    )

    graph.add_edge("approval_node", "execute_tools_node")
    graph.add_edge("execute_tools_node", "draft_response_step")
    graph.add_edge("draft_response_step", "decision_step")
    graph.add_edge("decision_step", END)

    # ---- Use the shared PostgreSQL checkpointer ----
    checkpointer = _get_checkpointer()
    return graph.compile(checkpointer=checkpointer)