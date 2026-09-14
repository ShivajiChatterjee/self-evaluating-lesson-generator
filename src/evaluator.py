import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from src.state import LessonState


class RubricResult(BaseModel):
    criterion: str
    passed: bool
    reason: str
    evidence: str
    required_fix: str | None


class LessonEvaluation(BaseModel):
    checks: list[RubricResult]
    overall_pass: bool


EXPECTED_CRITERIA = {
    "ACCURATE_AND_GROUNDED",
    "BEGINNER_FRIENDLY",
    "TEACHES_BY_EXAMPLE",
    "JARGON_CONTROL",
    "KEY_POINTS_COVERED",
    "COHERENT_TEACHING_FLOW",
}

EVALUATOR_INSTRUCTION = """You are a strict evaluator of beginner educational content.
Decide whether this lesson is ready to ship to the intended learner. Evaluate exactly
the six supplied criteria as binary PASS or FAIL checks, with no partial credit. If
an important requirement is missing, fail that check. Give a concrete reason and
lesson evidence for every result. For a failure, state the exact required change;
for a pass, set required_fix to null. Judge factual accuracy against the trusted
grounding context rather than relying only on your internal knowledge. Do not rewrite
the lesson."""

RUBRIC = """1. ACCURATE_AND_GROUNDED
PASS only when RAG explanations are consistent with the trusted context, contain no
important unsupported technical claims, and do not describe standard RAG as retraining
or permanently changing model weights during each query.

2. BEGINNER_FRIENDLY
PASS only when a learner with no AI background can follow the lesson, the language is
simple enough for the stated audience, and no advanced technical knowledge is assumed.

3. TEACHES_BY_EXAMPLE
PASS only when the lesson has an understandable analogy and a practical RAG example,
and both genuinely help explain the concept.

4. JARGON_CONTROL
PASS only when important technical words are explained when first introduced,
unexplained terminology does not block understanding, and jargon is not unnecessary.

5. KEY_POINTS_COVERED
PASS only when the lesson adequately explains the problem RAG solves, what RAG is,
why it is useful, retrieval, retrieved context, generation, the basic question to
retrieval to context to answer flow, and how RAG context differs from model training.

6. COHERENT_TEACHING_FLOW
PASS only when ideas follow a sensible learning order, sections connect logically,
there are no major contradictions, the lesson ends with a useful recap, and grammar
or readability defects do not materially disrupt learning."""


def evaluate_lesson(state: LessonState) -> dict:
    lesson = state["lesson"].strip()
    grounding_context = state["grounding_context"].strip()
    if not lesson:
        raise ValueError("Lesson is empty and cannot be evaluated.")
    if not grounding_context:
        raise ValueError("Grounding context is empty and cannot support evaluation.")

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")

    model = os.getenv("EVALUATOR_MODEL") or "gemini-3.5-flash"
    evaluation_request = f"""Topic:
{state['topic']}

Trusted grounding context:
{grounding_context}

Lesson to evaluate:
{lesson}

Evaluation rubric:
{RUBRIC}"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=evaluation_request,
        config=types.GenerateContentConfig(
            system_instruction=EVALUATOR_INSTRUCTION,
            thinking_config=types.ThinkingConfig(thinking_level="medium"),
            response_mime_type="application/json",
            response_schema=LessonEvaluation,
        ),
    )

    evaluation_text = (response.text or "").strip()
    if not evaluation_text:
        raise ValueError("Gemini returned an empty evaluation.")

    evaluation = LessonEvaluation.model_validate_json(evaluation_text)
    criterion_names = [check.criterion for check in evaluation.checks]
    if len(criterion_names) != 6 or set(criterion_names) != EXPECTED_CRITERIA:
        raise ValueError("Evaluation must contain each required criterion exactly once.")

    evaluation.overall_pass = all(check.passed for check in evaluation.checks)
    return {"evaluation": evaluation.model_dump()}
