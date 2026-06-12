"""Executable 10-node ExamGuard LangGraph StateGraph."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

AGENT_NODES = [
    "paper_config_agent",
    "material_ingestion_agent",
    "orchestrator_agent",
    "question_generation_agent",
    "proctoring_agent",
    "stylometric_agent",
    "security_agent",
    "evaluation_agent",
    "report_agent",
    "review_agent",
]

EDGES = [
    ("paper_config_agent", "question_generation_agent"),
    ("material_ingestion_agent", "question_generation_agent"),
    ("question_generation_agent", "orchestrator_agent"),
    ("proctoring_agent", "orchestrator_agent"),
    ("stylometric_agent", "orchestrator_agent"),
    ("security_agent", "orchestrator_agent"),
    ("evaluation_agent", "orchestrator_agent"),
    ("orchestrator_agent", "report_agent"),
    ("orchestrator_agent", "review_agent"),
]


class ExamGuardState(TypedDict, total=False):
    workflow: str
    payload: dict[str, Any]
    completed_agents: list[str]
    integrity_status: str
    error: str


def _node(name: str):
    def run(state: ExamGuardState) -> ExamGuardState:
        return {**state, "completed_agents": [*state.get("completed_agents", []), name]}
    run.__name__ = name
    return run


def _entry_route(state: ExamGuardState) -> str:
    return {
        "ingest": "material_ingestion_agent",
        "generate": "paper_config_agent",
        "proctor": "proctoring_agent",
        "answer": "stylometric_agent",
        "finish": "evaluation_agent",
    }.get(state.get("workflow", "generate"), "paper_config_agent")


def _after_orchestrator(state: ExamGuardState) -> str:
    return "review_agent" if state.get("integrity_status") == "FLAGGED" else "report_agent"


def build_graph():
    graph = StateGraph(ExamGuardState)
    for name in AGENT_NODES:
        graph.add_node(name, _node(name))
    graph.set_conditional_entry_point(_entry_route, {
        "material_ingestion_agent": "material_ingestion_agent", "paper_config_agent": "paper_config_agent",
        "proctoring_agent": "proctoring_agent", "stylometric_agent": "stylometric_agent",
        "evaluation_agent": "evaluation_agent",
    })
    graph.add_edge("material_ingestion_agent", "question_generation_agent")
    graph.add_edge("paper_config_agent", "question_generation_agent")
    graph.add_edge("question_generation_agent", "orchestrator_agent")
    graph.add_edge("proctoring_agent", "orchestrator_agent")
    graph.add_edge("stylometric_agent", "security_agent")
    graph.add_edge("security_agent", "orchestrator_agent")
    graph.add_edge("evaluation_agent", "orchestrator_agent")
    graph.add_conditional_edges("orchestrator_agent", _after_orchestrator, {
        "review_agent": "review_agent", "report_agent": "report_agent",
    })
    graph.add_edge("review_agent", "report_agent")
    graph.add_edge("report_agent", END)
    return graph.compile()


examguard_graph = build_graph()


def run_workflow(workflow: str, payload: dict[str, Any], integrity_status: str = "CLEAN") -> ExamGuardState:
    return examguard_graph.invoke({
        "workflow": workflow, "payload": payload, "integrity_status": integrity_status, "completed_agents": [],
    })
