import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.resources import load_learning_resources
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

LESSON_REQUIREMENTS = """Write a standalone beginner-friendly Markdown chapter that reads
like a short textbook chapter or educational technical documentation.
Aim for roughly 1000-1400 words, but treat this only as a soft guideline. Prioritize
clarity and complete beginner understanding, and modestly exceed the range when needed.
Avoid unnecessary repetition and unnecessary advanced detail.

Choose the section and subsection structure dynamically from the requested topic, the
learner's needs, and the important concepts supported by the trusted grounding context.
Build a natural progression by introducing prerequisite ideas before concepts that depend
on them. Give supported concepts enough depth, but do not invent material or add sections
merely to increase breadth or length.

Use descriptive topic titles for section and subsection headings. Avoid headings phrased as
questions, including forms such as "What is ...", "Why ...", "How does ...", "When ...",
and "What are ...". Do not structure the chapter as a sequence of questions and answers.
Use connected explanatory paragraphs as the primary teaching style. Use bullet or numbered
lists only when they genuinely improve clarity, and use subsections when deeper explanation
is useful.

Include at least one useful text-based workflow or diagram, at least one everyday analogy,
and at least one realistic practical example. Place them where they naturally support the
surrounding explanation. Include a clear concluding summary or set of key takeaways.

Near the end, include a clearly identifiable Further Learning section. Select only resources
that are relevant to concepts actually taught in the chapter. For each selected resource,
include its title as a clickable Markdown link and one short explanation of what the learner
can study there. Use only URLs supplied in the curated learning resources. Never invent,
reconstruct, guess, or modify a URL, and do not add irrelevant links for variety.

Before returning the lesson, ensure normal word spacing, punctuation, Markdown formatting,
and paragraph readability are clean. Do not merge adjacent words or remove spaces after
punctuation."""


def _format_memory_guidance(memory_guidance: list[str]) -> str:
    if not memory_guidance:
        return ""

    rules = "\n".join(f"- {rule}" for rule in memory_guidance)
    return f"""

Learned guidance from previous lesson failures:
{rules}

Use this historical guidance only to avoid repeating problems from previous runs.
It is supplemental; trusted grounding and fixed lesson requirements remain authoritative.
Do not refer to this guidance, previous runs, evaluation, rubrics, retries, or learned rules
in the lesson unless a term is genuinely required by the lesson topic."""


def _extract_response_text(response: types.GenerateContentResponse) -> str:
    if (
        not response.candidates
        or not response.candidates[0].content
        or not response.candidates[0].content.parts
    ):
        return ""

    text = ""
    for part in response.candidates[0].content.parts:
        if part.thought or not isinstance(part.text, str):
            continue
        if text and part.text and text[-1].isalnum() and part.text[0].isalnum():
            text += " "
        text += part.text

    return text


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

    generated_lesson = _extract_response_text(response).strip()
    if not generated_lesson:
        raise ValueError("Gemini returned an empty lesson.")

    return generated_lesson


def generate_lesson(state: LessonState) -> dict:
    memory_section = _format_memory_guidance(state["memory_guidance"])
    learning_resources = load_learning_resources()
    generation_request = f"""Topic:
{state['topic']}

Lesson requirements:
{LESSON_REQUIREMENTS}

Trusted grounding context:
{state['grounding_context']}

Curated learning resources (for Further Learning links only, not factual grounding):
{learning_resources}{memory_section}"""
    return {"lesson": _request_lesson(generation_request)}


def regenerate_lesson(state: LessonState) -> dict:
    memory_section = _format_memory_guidance(state["memory_guidance"])
    learning_resources = load_learning_resources()
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

Curated learning resources (for Further Learning links only, not factual grounding):
{learning_resources}

Current lesson to replace:
{state['lesson']}

Failed checks and required corrections:
{failed_feedback}{memory_section}

Produce a complete standalone replacement lesson in Markdown, not a patch or diff.
Correct every failed criterion while preserving good parts of the current lesson where possible.
Avoid unnecessary rewrites and remain consistent with the trusted grounding context.
After trusted grounding, treat current failed checks and required fixes as the primary corrective signal.
Do not mention the evaluator, retry process, rejection, rubric, feedback, or previous attempt."""

    regenerated_lesson = _request_lesson(regeneration_request)
    return {
        "lesson": regenerated_lesson,
        "retry_count": state["retry_count"] + 1,
    }
