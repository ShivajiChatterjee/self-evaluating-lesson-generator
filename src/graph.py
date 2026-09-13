from langgraph.graph import END, START, StateGraph

from src.generator import generate_lesson
from src.grounding import load_grounding_context
from src.state import LessonState


workflow = StateGraph(LessonState)
workflow.add_node("load_grounding_context", load_grounding_context)
workflow.add_node("generate_lesson", generate_lesson)
workflow.add_edge(START, "load_grounding_context")
workflow.add_edge("load_grounding_context", "generate_lesson")
workflow.add_edge("generate_lesson", END)

graph = workflow.compile()
