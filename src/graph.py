from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.evaluator import evaluate_lesson
from src.generator import generate_lesson, regenerate_lesson
from src.grounding import load_grounding_context
from src.memory import load_memory_guidance, persist_run_memory
from src.retry import MAX_RETRIES, record_rejection
from src.state import LessonState


def route_evaluation(state: LessonState) -> Literal["pass", "fail"]:
    return "pass" if state["evaluation"]["overall_pass"] else "fail"


def route_retry(state: LessonState) -> Literal["retry", "stop"]:
    return "retry" if state["retry_count"] < MAX_RETRIES else "stop"


workflow = StateGraph(LessonState)
workflow.add_node("load_grounding_context", load_grounding_context)
workflow.add_node("load_memory_guidance", load_memory_guidance)
workflow.add_node("generate_lesson", generate_lesson)
workflow.add_node("evaluate_lesson", evaluate_lesson)
workflow.add_node("record_rejection", record_rejection)
workflow.add_node("regenerate_lesson", regenerate_lesson)
workflow.add_node("persist_run_memory", persist_run_memory)
workflow.add_edge(START, "load_grounding_context")
workflow.add_edge("load_grounding_context", "load_memory_guidance")
workflow.add_edge("load_memory_guidance", "generate_lesson")
workflow.add_edge("generate_lesson", "evaluate_lesson")
workflow.add_conditional_edges(
    "evaluate_lesson",
    route_evaluation,
    {"pass": "persist_run_memory", "fail": "record_rejection"},
)
workflow.add_conditional_edges(
    "record_rejection",
    route_retry,
    {"retry": "regenerate_lesson", "stop": "persist_run_memory"},
)
workflow.add_edge("regenerate_lesson", "evaluate_lesson")
workflow.add_edge("persist_run_memory", END)

graph = workflow.compile()
