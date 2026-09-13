from typing import Any, TypedDict


class LessonState(TypedDict):
    topic: str
    grounding_context: str
    sources: list[str]
    lesson: str
    evaluation: dict[str, Any]
    retry_count: int
    rejection_history: list[dict[str, Any]]
