from langgraph.graph import END, START, StateGraph

from src.grounding import load_grounding_context
from src.state import LessonState


workflow = StateGraph(LessonState)
workflow.add_node("load_grounding_context", load_grounding_context)
workflow.add_edge(START, "load_grounding_context")
workflow.add_edge("load_grounding_context", END)

graph = workflow.compile()
