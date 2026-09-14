from pathlib import Path


LEARNING_RESOURCES_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "learning_resources.md"
)


def load_learning_resources() -> str:
    if not LEARNING_RESOURCES_PATH.is_file():
        raise FileNotFoundError(
            f"Learning resources file not found: {LEARNING_RESOURCES_PATH}"
        )

    return LEARNING_RESOURCES_PATH.read_text(encoding="utf-8").strip()
