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

LESSON_REQUIREMENTS = """Write a standalone Markdown lesson of approximately 800-1200 words.
Use clear headings, at least one everyday analogy, and at least one practical RAG example.
Follow this teaching flow:
1. What problem are we trying to solve?
2. What is RAG?
3. Why is RAG useful?
4. How does RAG work?
5. Simple analogy.
6. Practical example.
7. Important points to remember.
8. Short recap."""


def generate_lesson(state: LessonState) -> dict:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")

    model = os.getenv("GENERATOR_MODEL") or "gemini-3.8-flash"
    generation_request = f"""Topic:
{state['topic']}

Lesson requirements:
{LESSON_REQUIREMENTS}

Trusted grounding context:
{state['grounding_context']}"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=generation_request,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.4,
        ),
    )

    generated_lesson = (response.text or "").strip()
    if not generated_lesson:
        raise ValueError("Gemini returned an empty lesson.")

    return {"lesson": generated_lesson}
