from langgraph.graph import END, START, StateGraph

from src.state import LessonState


# This node will be replaced by the real lesson workflow in later milestones.
def temporary_node(state: LessonState) -> LessonState:
    return state


workflow = StateGraph(LessonState)
workflow.add_node("temporary", temporary_node)
workflow.add_edge(START, "temporary")
workflow.add_edge("temporary", END)

graph = workflow.compile()
