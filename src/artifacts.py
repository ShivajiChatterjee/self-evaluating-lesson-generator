import html
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from markdown_it import MarkdownIt
from markdown_it.token import Token
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)

from src.gemini_utils import extract_response_text


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_DIRECTORY / "outputs"

CLEANUP_INSTRUCTION = """You are a whitespace-only Markdown formatting editor.
Return the exact same lesson and only insert or remove whitespace where necessary to fix
merged words caused by missing spaces. Preserve every non-whitespace character in its
original order. Preserve capitalization, punctuation, Markdown syntax, headings, code
fences, and URLs exactly. Do not rewrite or paraphrase sentences. Do not add or remove
information. Return only the complete lesson with no commentary or wrapper code fence."""

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")

_HORIZONTAL_BOX_CHARACTERS = "─━┄┅┈┉╌╍═╴╶╸╺╼╾"
_VERTICAL_BOX_CHARACTERS = "│┃┆┇┊┋╎╏║╵╷╹╻╽╿"
_CORNER_AND_INTERSECTION_CHARACTERS = "".join(
    chr(code_point)
    for first, last in ((0x250C, 0x254B), (0x2552, 0x2570))
    for code_point in range(first, last + 1)
)
_PDF_DIAGRAM_TRANSLATION = str.maketrans(
    {
        **{character: "-" for character in _HORIZONTAL_BOX_CHARACTERS},
        **{character: "|" for character in _VERTICAL_BOX_CHARACTERS},
        **{character: "+" for character in _CORNER_AND_INTERSECTION_CHARACTERS},
        "╱": "/",
        "╲": "\\",
        "╳": "x",
        "▼": "v",
        "↓": "v",
        "▲": "^",
        "↑": "^",
        "►": ">",
        "◄": "<",
    }
)


def validate_whitespace_cleanup(raw_lesson: str, cleaned_lesson: str) -> bool:
    raw_without_whitespace = "".join(raw_lesson.split())
    cleaned_without_whitespace = "".join(cleaned_lesson.split())
    return (
        raw_without_whitespace == cleaned_without_whitespace
        and URL_PATTERN.findall(raw_lesson) == URL_PATTERN.findall(cleaned_lesson)
        and raw_lesson.count("```") == cleaned_lesson.count("```")
    )


def _prepare_pdf_code_block(code: str) -> str:
    return code.translate(_PDF_DIAGRAM_TRANSLATION)


def _request_cleanup(raw_lesson: str) -> str:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to the .env file.")

    model = (
        os.getenv("CLEANUP_MODEL")
        or os.getenv("RESEARCH_MODEL")
        or os.getenv("GENERATOR_MODEL")
        or "gemini-2.5-flash-lite"
    )
    response = genai.Client(api_key=api_key).models.generate_content(
        model=model,
        contents=f"Lesson to clean:\n\n{raw_lesson}",
        config=types.GenerateContentConfig(system_instruction=CLEANUP_INSTRUCTION),
    )
    cleaned_lesson = extract_response_text(response)
    if not cleaned_lesson.strip():
        raise ValueError("Presentation cleanup returned no usable content.")
    return cleaned_lesson


def _safe_topic_slug(topic: str) -> str:
    ascii_topic = unicodedata.normalize("NFKD", topic).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_topic.lower()).strip("-")
    return (slug or "lesson")[:60].rstrip("-")


def _create_run_directory(output_root: Path, topic: str) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    base_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_topic_slug(topic)}"

    for suffix in range(1, 1000):
        directory_name = base_name if suffix == 1 else f"{base_name}_{suffix}"
        run_directory = output_root / directory_name
        try:
            run_directory.mkdir()
            return run_directory
        except FileExistsError:
            continue

    raise RuntimeError("Could not allocate a unique artifact directory.")


def _inline_markup(token: Token) -> str:
    if not token.children:
        return html.escape(token.content)

    fragments = []
    for child in token.children:
        if child.type == "text":
            fragments.append(html.escape(child.content))
        elif child.type == "softbreak":
            fragments.append(" ")
        elif child.type == "hardbreak":
            fragments.append("<br/>")
        elif child.type == "strong_open":
            fragments.append("<b>")
        elif child.type == "strong_close":
            fragments.append("</b>")
        elif child.type == "em_open":
            fragments.append("<i>")
        elif child.type == "em_close":
            fragments.append("</i>")
        elif child.type == "code_inline":
            fragments.append(f'<font name="Courier">{html.escape(child.content)}</font>')
        elif child.type == "link_open":
            href = html.escape(child.attrGet("href") or "", quote=True)
            fragments.append(f'<link href="{href}" color="#7a4324">')
        elif child.type == "link_close":
            fragments.append("</link>")
        elif child.type == "html_inline":
            fragments.append(html.escape(child.content))
    return "".join(fragments)


def _matching_token(tokens: list[Token], start: int, open_type: str, close_type: str) -> int:
    depth = 0
    for index in range(start, len(tokens)):
        if tokens[index].type == open_type:
            depth += 1
        elif tokens[index].type == close_type:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError(f"Unclosed Markdown token: {open_type}")


def _render_list(
    tokens: list[Token],
    start: int,
    styles: dict[str, ParagraphStyle],
) -> tuple[ListFlowable, int]:
    ordered = tokens[start].type == "ordered_list_open"
    close_type = "ordered_list_close" if ordered else "bullet_list_close"
    end = _matching_token(tokens, start, tokens[start].type, close_type)
    items = []
    index = start + 1

    while index < end:
        if tokens[index].type != "list_item_open":
            index += 1
            continue
        item_end = _matching_token(tokens, index, "list_item_open", "list_item_close")
        item_flowables = _render_blocks(tokens[index + 1 : item_end], styles)
        items.append(ListItem(item_flowables or [Paragraph("", styles["LessonBody"])]))
        index = item_end + 1

    start_number = int(tokens[start].attrGet("start") or 1) if ordered else None
    flowable = ListFlowable(
        items,
        bulletType="1" if ordered else "bullet",
        start=start_number,
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=9,
        spaceAfter=7,
    )
    return flowable, end + 1


def _render_blocks(
    tokens: list[Token], styles: dict[str, ParagraphStyle]
) -> list[Any]:
    flowables = []
    index = 0
    while index < len(tokens):
        token = tokens[index]

        if token.type == "heading_open" and index + 1 < len(tokens):
            level = min(int(token.tag[1]), 3)
            flowables.append(Paragraph(_inline_markup(tokens[index + 1]), styles[f"H{level}"]))
            index += 3
        elif token.type == "paragraph_open" and index + 1 < len(tokens):
            flowables.append(Paragraph(_inline_markup(tokens[index + 1]), styles["LessonBody"]))
            index += 3
        elif token.type in {"bullet_list_open", "ordered_list_open"}:
            rendered_list, index = _render_list(tokens, index, styles)
            flowables.append(rendered_list)
        elif token.type in {"fence", "code_block"}:
            flowables.append(
                Preformatted(
                    _prepare_pdf_code_block(token.content),
                    styles["LessonCode"],
                    maxLineLength=92,
                )
            )
            index += 1
        elif token.type == "hr":
            flowables.append(Spacer(1, 8))
            index += 1
        else:
            index += 1
    return flowables


def _pdf_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "LessonTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#26231F"),
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "H1": ParagraphStyle(
            "LessonH1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=25,
            textColor=colors.HexColor("#26231F"),
            spaceBefore=8,
            spaceAfter=12,
        ),
        "H2": ParagraphStyle(
            "LessonH2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=colors.HexColor("#7A4324"),
            spaceBefore=15,
            spaceAfter=8,
        ),
        "H3": ParagraphStyle(
            "LessonH3",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#3C3933"),
            spaceBefore=11,
            spaceAfter=6,
        ),
        "LessonBody": ParagraphStyle(
            "LessonBody",
            parent=sample["BodyText"],
            fontName="Times-Roman",
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#26231F"),
            spaceAfter=9,
        ),
        "LessonCode": ParagraphStyle(
            "LessonCode",
            parent=sample["Code"],
            fontName="Courier",
            fontSize=8.5,
            leading=12,
            leftIndent=10,
            rightIndent=10,
            borderColor=colors.HexColor("#C8BBA8"),
            borderWidth=0.5,
            borderPadding=8,
            backColor=colors.HexColor("#F2EEE6"),
            spaceBefore=5,
            spaceAfter=11,
        ),
    }


def _draw_footer(canvas: Any, document: Any, topic: str) -> None:
    canvas.saveState()
    canvas.setTitle(topic)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6A645B"))
    canvas.drawString(20 * mm, 13 * mm, "Self-Evaluating Lesson Generator")
    canvas.drawRightString(A4[0] - 20 * mm, 13 * mm, f"Page {document.page}")
    canvas.restoreState()


def _write_pdf(markdown: str, topic: str, destination: Path) -> None:
    tokens = MarkdownIt("commonmark").parse(markdown)
    styles = _pdf_styles()
    story = _render_blocks(tokens, styles)
    if not tokens or tokens[0].type != "heading_open" or tokens[0].tag != "h1":
        story.insert(0, Paragraph(html.escape(topic), styles["Title"]))

    document = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=topic,
        author="Self-Evaluating Lesson Generator",
    )
    def draw_footer(canvas: Any, document: Any) -> None:
        _draw_footer(canvas, document, topic)

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


def create_lesson_artifacts(
    result: dict[str, Any], output_root: Path = OUTPUT_DIRECTORY
) -> dict[str, Any] | None:
    if not result["evaluation"]["overall_pass"]:
        return None

    raw_lesson = result["lesson"]
    cleaned_lesson = raw_lesson
    cleanup_applied = False
    try:
        cleanup_candidate = _request_cleanup(raw_lesson)
        if validate_whitespace_cleanup(raw_lesson, cleanup_candidate):
            cleaned_lesson = cleanup_candidate
            cleanup_applied = True
    except Exception:
        # Presentation cleanup must never invalidate an already approved lesson.
        pass

    run_directory = _create_run_directory(output_root, result["topic"])
    raw_markdown_path = run_directory / "raw_lesson.md"
    markdown_path = run_directory / "final_lesson.md"
    pdf_path = run_directory / "lesson.pdf"
    rejection_log_path = run_directory / "rejection_log.json"

    raw_markdown_path.write_bytes(raw_lesson.encode("utf-8"))
    markdown_path.write_bytes(cleaned_lesson.encode("utf-8"))
    rejection_log = {
        "topic": result["topic"],
        "retry_count": result["retry_count"],
        "overall_pass": result["evaluation"]["overall_pass"],
        "rejection_history": result["rejection_history"],
        "memory_guidance": result["memory_guidance"],
    }
    rejection_log_path.write_bytes(
        json.dumps(rejection_log, indent=2, ensure_ascii=False).encode("utf-8")
    )
    _write_pdf(cleaned_lesson, result["topic"], pdf_path)

    return {
        "run_directory": run_directory,
        "raw_markdown_path": raw_markdown_path,
        "markdown_path": markdown_path,
        "pdf_path": pdf_path,
        "rejection_log_path": rejection_log_path,
        "presentation_lesson": cleaned_lesson,
        "cleanup_applied": cleanup_applied,
    }
