from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.modules.agent.nodes import (
    classify_ticket_node,
    decision_node,
    detect_risk_node,
    draft_response_node,
    load_ticket_context_node,
    plan_tools_node,
    retrieve_knowledge_node,
)
from app.modules.agent.state import AgentState
from app.modules.agent.step_logger import run_logged_step


def build_ticket_agent_graph(db: Session):
    graph = StateGraph(AgentState)

    def load_context(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="load_ticket_context",
            input_json={"ticket_id": state["ticket_id"]},
            fn=lambda: load_ticket_context_node(db, state),
        )

    def retrieve_knowledge(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="retrieve_knowledge",
            input_json={"ticket": state.get("ticket")},
            fn=lambda: retrieve_knowledge_node(db, state),
        )

    def classify_ticket(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="classify_ticket",
            input_json={"ticket": state.get("ticket")},
            fn=lambda: classify_ticket_node(state),
        )

    def detect_risk(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="detect_risk",
            input_json={
                "ticket": state.get("ticket"),
                "category": state.get("detected_category"),
            },
            fn=lambda: detect_risk_node(state),
        )

    def plan_tools(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="plan_tools",
            input_json={
                "ticket": state.get("ticket"),
                "category": state.get("detected_category"),
            },
            fn=lambda: plan_tools_node(state),
        )

    def draft_response(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="draft_response",
            input_json={
                "ticket": state.get("ticket"),
                "knowledge_context": state.get("knowledge_context"),
            },
            fn=lambda: draft_response_node(state),
        )

    def decide(state: AgentState) -> AgentState:
        return run_logged_step(
            db=db,
            organization_id=state["organization_id"],
            agent_run_id=state["agent_run_id"],
            ticket_id=state["ticket_id"],
            step_name="decision",
            input_json={
                "risk_level": state.get("risk_level"),
                "planned_tools": state.get("planned_tools"),
            },
            fn=lambda: decision_node(state),
        )

    graph.add_node("load_ticket_context", load_context)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("detect_risk", detect_risk)
    graph.add_node("plan_tools", plan_tools)
    graph.add_node("draft_response", draft_response)
    graph.add_node("decision", decide)

    graph.set_entry_point("load_ticket_context")

    graph.add_edge("load_ticket_context", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "classify_ticket")
    graph.add_edge("classify_ticket", "detect_risk")
    graph.add_edge("detect_risk", "plan_tools")
    graph.add_edge("plan_tools", "draft_response")
    graph.add_edge("draft_response", "decision")
    graph.add_edge("decision", END)

    return graph.compile()