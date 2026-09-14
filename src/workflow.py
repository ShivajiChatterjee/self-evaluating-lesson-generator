from src.graph import graph
from src.state import LessonState


def run_lesson_workflow(topic: str) -> LessonState:
    normalized_topic = topic.strip()
    if not normalized_topic:
        raise ValueError("Topic cannot be blank.")

    initial_state: LessonState = {
        "topic": normalized_topic,
        "grounding_context": "",
        "sources": [],
        "memory_guidance": [],
        "lesson": "",
        "evaluation": {},
        "retry_count": 0,
        "rejection_history": [],
    }
    return graph.invoke(initial_state)
