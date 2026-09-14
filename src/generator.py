import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.state import LessonState


SYSTEM_INSTRUCTION = """You are a beginner-focused technical educator.
Teach a learner who completed 12th grade in India, may come from a non-English-medium
background, has limited English vocabulary, has no previous AI knowledge, and wants
to begin a career in AI. Use simple English, introduce ideas before technical terms,
explain technical words when first used, and prefer short, clear sentences.

Keep factual explanations consistent with the supplied trusted reference. You may
simplify and reorganize its facts and create analogies or beginner examples, but do
not introduce unsupported technical claims. If the reference does not support a
technical claim, leave it out."""

LESSON_REQUIREMENTS = """Write a standalone beginner-friendly Markdown lesson.
Aim for roughly 1000-1400 words, but prioritize clarity and complete beginner understanding over exact length.
Avoid unnecessary repetition and unnecessary advanced detail.
Use clear headings and include at least one simple text-based workflow showing the RAG process.
Include at least one everyday analogy and at least one practical RAG example.
Follow this teaching flow:
1. What problem are we trying to solve?
2. What is RAG?
3. Why is RAG useful?
4. How does RAG work?
5. Simple analogy.
6. Practical example.
7. Important points to remember.
8. Short recap."""


def _request_lesson(generation_request: str) -> str:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")

    model = os.getenv("GENERATOR_MODEL") or "gemini-3.6-flash"
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=generation_request,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.4,
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )

    generated_lesson = (response.text or "").strip()
    if not generated_lesson:
        raise ValueError("Gemini returned an empty lesson.")

    return generated_lesson


def generate_lesson(state: LessonState) -> dict:
    generation_request = f"""Topic:
{state['topic']}

Lesson requirements:
{LESSON_REQUIREMENTS}

Trusted grounding context:
{state['grounding_context']}"""
    return {"lesson": _request_lesson(generation_request)}


def regenerate_lesson(state: LessonState) -> dict:
    failed_feedback = "\n\n".join(
        f"Criterion: {check['criterion']}\n"
        f"Reason: {check['reason']}\n"
        f"Evidence: {check['evidence']}\n"
        f"Required fix: {check['required_fix']}"
        for check in state["evaluation"]["checks"]
        if not check["passed"]
    )
    regeneration_request = f"""Topic:
{state['topic']}

Lesson requirements:
{LESSON_REQUIREMENTS}

Trusted grounding context:
{state['grounding_context']}

Current lesson to replace:
{state['lesson']}

Failed checks and required corrections:
{failed_feedback}

Produce a complete standalone replacement lesson in Markdown, not a patch or diff.
Correct every failed criterion while preserving good parts of the current lesson where possible.
Avoid unnecessary rewrites and remain consistent with the trusted grounding context.
Do not mention the evaluator, retry process, rejection, rubric, feedback, or previous attempt."""

    regenerated_lesson = _request_lesson(regeneration_request)
    return {
        "lesson": regenerated_lesson,
        "retry_count": state["retry_count"] + 1,
    }
