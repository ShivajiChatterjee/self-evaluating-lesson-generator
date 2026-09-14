from pathlib import Path

from src.state import LessonState


REFERENCE_PATH = Path(__file__).resolve().parent.parent / "data" / "rag_reference.md"


def load_grounding_context(state: LessonState) -> dict:
    if not REFERENCE_PATH.is_file():
        raise FileNotFoundError(f"Grounding reference not found: {REFERENCE_PATH}")

    return {
        "grounding_context": REFERENCE_PATH.read_text(encoding="utf-8"),
        "sources": [
            "Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            "Microsoft Learn, Retrieval augmented generation and indexes",
            "AWS, Retrieval Augmented Generation",
            "Google Cloud, What is Retrieval-Augmented Generation?",
        ],
    }
