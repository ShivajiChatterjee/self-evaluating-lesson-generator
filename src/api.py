from fastapi import FastAPI, HTTPException
from google.genai import errors
from pydantic import BaseModel, field_validator

from src.evaluator import LessonEvaluation
from src.grounding import ResearchError
from src.workflow import run_lesson_workflow


app = FastAPI(title="Self-Evaluating Lesson Content Generator API")


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


class GenerateLessonResponse(BaseModel):
    topic: str
    lesson: str
    evaluation: LessonEvaluation
    retry_count: int
    rejection_history: list[RejectionRecord]
    sources: list[str]
    memory_guidance: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/lessons/generate", response_model=GenerateLessonResponse)
def generate_lesson(request: GenerateLessonRequest) -> GenerateLessonResponse:
    try:
        result = run_lesson_workflow(request.topic)
        return GenerateLessonResponse.model_validate(result)
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
