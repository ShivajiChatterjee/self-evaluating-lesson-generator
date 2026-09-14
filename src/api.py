from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.genai import errors
from pydantic import BaseModel, field_validator

from src.artifacts import OUTPUT_DIRECTORY, create_lesson_artifacts
from src.evaluator import LessonEvaluation
from src.grounding import ResearchError
from src.workflow import run_lesson_workflow


STATIC_DIRECTORY = Path(__file__).resolve().parent.parent / "static"
OUTPUT_DIRECTORY.mkdir(exist_ok=True)

app = FastAPI(title="Self-Evaluating Lesson Content Generator API")
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIRECTORY), name="outputs")


class GenerateLessonRequest(BaseModel):
    topic: str

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, topic: str) -> str:
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise ValueError("Topic cannot be blank.")
        return normalized_topic


class RejectedCheck(BaseModel):
    criterion: str
    reason: str
    evidence: str
    required_fix: str | None


class RejectionRecord(BaseModel):
    attempt: int
    failed_checks: list[RejectedCheck]
    rejected_lesson: str


class ArtifactLinks(BaseModel):
    pdf_url: str
    markdown_url: str
    rejection_log_url: str
    cleanup_applied: bool


class GenerateLessonResponse(BaseModel):
    topic: str
    lesson: str
    evaluation: LessonEvaluation
    retry_count: int
    rejection_history: list[RejectionRecord]
    sources: list[str]
    memory_guidance: list[str]
    artifacts: ArtifactLinks | None = None


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/lessons/generate", response_model=GenerateLessonResponse)
def generate_lesson(request: GenerateLessonRequest) -> GenerateLessonResponse:
    try:
        result = run_lesson_workflow(request.topic)
        artifacts = create_lesson_artifacts(result)
        response_data = dict(result)
        if artifacts:
            run_folder = artifacts["run_directory"].name
            response_data["lesson"] = artifacts["presentation_lesson"]
            response_data["artifacts"] = {
                "pdf_url": f"/outputs/{run_folder}/lesson.pdf",
                "markdown_url": f"/outputs/{run_folder}/final_lesson.md",
                "rejection_log_url": f"/outputs/{run_folder}/rejection_log.json",
                "cleanup_applied": artifacts["cleanup_applied"],
            }
        else:
            response_data["artifacts"] = None
        return GenerateLessonResponse.model_validate(response_data)
    except errors.APIError as error:
        if error.code == 503:
            raise HTTPException(
                status_code=503,
                detail="The AI model service is temporarily unavailable. Please try again.",
            ) from error
        if error.code == 429:
            raise HTTPException(
                status_code=429,
                detail="The AI model service rate limit has been reached. Please try again later.",
            ) from error
        raise HTTPException(
            status_code=502,
            detail="The AI model service returned an unexpected error.",
        ) from error
    except ResearchError as error:
        raise HTTPException(
            status_code=502,
            detail="The topic research did not return usable grounded information.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="The lesson workflow could not be completed.",
        ) from error
