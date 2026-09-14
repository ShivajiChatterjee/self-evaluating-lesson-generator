# Self-Evaluating Lesson Content Generator

This project is an agentic content-generation system that dynamically researches an educational topic, generates a beginner-friendly lesson, evaluates it against strict quality gates, automatically corrects failed lessons, persists feedback across runs, and exports a final Markdown/PDF lesson.

The required submission topic is **Introduction to RAG**, but the workflow itself is topic-agnostic. The same architecture has been exercised with topics including Introduction to Transformers, Neural Networks, SQL Joins, and Hamiltonian Mechanics; these are examples, not a hard-coded supported-topic list.

## Assessment context

**GenAI Engineer - Content Systems | Take-Home Assessment**

The task is more than writing one prompt that produces educational content. The system owns the content-quality lifecycle:

```text
Topic
  -> Research
  -> Generate
  -> Evaluate
  -> Regenerate if needed
  -> Persist feedback
  -> Ship only when quality checks pass
```

The intended learner is approximately a 12th-grade graduate in India who may come from a non-English-medium background, have limited technical vocabulary, and have no previous knowledge of the requested topic. This leads the generator to use simple language, teach prerequisites first, define jargon when introduced, and use practical examples and analogies where they improve understanding.

## Key capabilities

- Topic-agnostic lesson generation
- Dynamic Gemini + Google Search grounding
- Dedicated research/grounding LLM role
- Separate generator and evaluator roles
- One shared grounding package for generation and evaluation
- Six hard binary PASS/FAIL quality gates
- Bounded corrective regeneration
- Rejection history with failed-check evidence
- Persistent SQLite memory across independent runs
- Topic-specific learned generation guidance
- Deterministic LangGraph orchestration
- FastAPI backend and lightweight browser frontend
- Markdown and PDF artifact export
- Validated whitespace-only presentation cleanup
- Separate preservation of the raw approved lesson
- PDF-safe ASCII normalization for text diagrams

The LLM-powered workflow nodes are specialized by responsibility. They are not an autonomous swarm: LangGraph controls their order and routing deterministically.

## Architecture

```text
                    +----------------------+
                    |      User Topic      |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Research / Grounding |
                    | Gemini + Google      |
                    | Search               |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Persistent Memory    |
                    | SQLite Guidance      |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Lesson Generator     |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Evaluator            |
                    | 6 Binary Gates       |
                    +------+---------+-----+
                           |         |
                        PASS         FAIL
                           |          |
                           |          v
                           |   Rejection Record
                           |          |
                           |          v
                           |    Regeneration
                           |          |
                           |          +-----> Evaluator
                           |
                           v
                    Persist Run Memory
                           |
                           v
                      Final Lesson
                           |
                           v
                Presentation Cleanup
                           |
                           v
                 Markdown + PDF Export
```

Research runs exactly once per workflow execution. Every retry reuses the original topic-specific grounding context and verified source list. The generator does not browse independently, and the evaluator does not conduct a separate search. Both judge and produce content from the same evidence package, while LangGraph controls all transitions.

## Why LangGraph

LangGraph is the deterministic orchestration layer. It maintains shared workflow state and moves that state through:

1. research
2. memory loading
3. generation
4. evaluation
5. rejection recording when required
6. regeneration when retries remain
7. run-memory persistence

No manager or supervisor LLM is used. The routing questions are objective and available directly in state:

- Did every quality gate pass?
- Has the retry limit been reached?

A supervisor model would add cost, latency, and nondeterminism without resolving a genuinely ambiguous routing decision.

The shared `LessonState` carries the topic, grounding context, sources, memory guidance, current lesson, evaluation, retry count, and rejection history.

## Research and grounding

The first node receives the requested topic and uses Gemini with Google Search grounding to create:

- topic-specific research context
- foundational and prerequisite ideas
- essential terminology
- relevant examples and use cases
- misconceptions or important distinctions
- limitations and trade-offs where relevant
- source metadata

The research instruction prioritizes official documentation, primary research, established educational institutions, and recognized technical organizations.

Source URLs are extracted from Gemini's Google Search grounding metadata. Model-written URLs are not treated as the source of truth. The extracted research context and source list form the common grounding package used downstream, preventing the generator and evaluator from independently working from different versions of the facts.

## Lesson generation

The generator receives:

- the requested topic
- dynamic grounding context
- verified research sources
- historical guidance for that topic

It assumes zero topic knowledge, uses simple English, defines important terms when introduced, and presents prerequisites before dependent ideas. The section structure is chosen dynamically from the topic and available evidence rather than using a fixed RAG template.

A lesson is expected to explain what the topic is, why it matters, and how it works; cover important supported concepts; include practical examples; use an analogy and workflow or diagram when useful; end with a clear summary; and provide Further Learning links drawn only from verified sources.

## Quality gates

The evaluator applies exactly six criteria:

1. `ACCURATE_AND_GROUNDED`
2. `BEGINNER_FRIENDLY`
3. `TEACHES_BY_EXAMPLE`
4. `JARGON_CONTROL`
5. `KEY_POINTS_COVERED`
6. `COHERENT_TEACHING_FLOW`

Every criterion is binary: PASS or FAIL, with no partial credit. Each result contains a reason, lesson evidence, and a required fix when it fails. The evaluator compares the lesson with the same dynamic grounding context used during generation.

`KEY_POINTS_COVERED` is topic-independent. It checks whether the lesson sufficiently teaches what the requested topic is, why it matters, how it works, and the important topic-specific concepts supported by the grounding context.

The evaluator returns structured JSON validated by Pydantic. Python then verifies that all six expected criteria appear exactly once and recalculates `overall_pass` from the six individual results rather than trusting the model's claimed overall decision.

## Corrective retry loop

`MAX_RETRIES = 2`, which means at most three lesson attempts:

| Attempt | Meaning |
|---|---|
| 1 | Initial generation |
| 2 | First regeneration |
| 3 | Second and final regeneration |

Every rejected attempt records:

- attempt number
- failed criteria
- reason
- evidence
- required fix
- complete rejected lesson

Regeneration receives the same topic, research context, source list, previous rejected lesson, evaluator feedback, and historical memory guidance. Research is not rerun during correction.

## Memory and self-evolution

SQLite provides local persistence through three conceptual tables:

| Table | Purpose |
|---|---|
| `runs` | Records the topic, final status, retry count, and timestamp for each run |
| `failures` | Stores criterion-level failures for rejected attempts |
| `learned_rules` | Maintains topic-and-criterion-specific guidance and failure frequency |

Historical evaluator failures become guidance for future generation. For example:

```text
Topic: Introduction to RAG
Repeated failure: TEACHES_BY_EXAMPLE
Learned guidance: Add a concrete, practical example that walks through a real user question.
```

On a later independent run for the same topic, the most relevant learned rules are loaded before initial generation.

The evaluator rubric does not evolve. Only generator guidance evolves. Allowing previous model judgments to modify the quality gate would risk evaluation drift; keeping the rubric fixed preserves a consistent shipping standard while generation improves from past failures.

## Output and artifact safety

A successful run creates a unique filesystem-safe directory:

```text
outputs/<timestamp>_<topic-slug>/
├── raw_lesson.md
├── final_lesson.md
├── lesson.pdf
└── rejection_log.json
```

| Artifact | Purpose |
|---|---|
| `raw_lesson.md` | Exact final lesson returned by LangGraph, preserved for traceability |
| `final_lesson.md` | Presentation-cleaned lesson used for learner-facing output |
| `lesson.pdf` | Print-friendly learner document generated from `final_lesson.md` |
| `rejection_log.json` | Topic, retry count, final status, rejection history, and loaded memory guidance |

Runtime artifacts are ignored by Git. If the final evaluation fails after all permitted attempts, the API still returns the completed workflow result, but no approved Markdown/PDF artifact set is created.

## Safe presentation cleanup

Gemini can occasionally return adjacent English words without a required space. Cleanup runs only after a lesson passes the quality gate and may only add or remove whitespace.

Before accepting cleaned text, the exporter requires:

```text
remove_all_whitespace(raw_lesson)
==
remove_all_whitespace(cleaned_lesson)
```

It also requires identical URL lists and an identical number of Markdown code fences. If cleanup changes any non-whitespace character or URL, returns empty content, fails validation, or encounters a provider error, `final_lesson.md` safely falls back to the raw lesson.

The evaluator always evaluates the raw lesson. Presentation cleanup cannot affect the quality-gate result or modify LangGraph state.

## PDF export

ReportLab produces an A4 learner-facing PDF using standard built-in fonts, readable margins, document hierarchy, page numbers, and a restrained footer. `markdown-it-py` parses the controlled Markdown subset used by generated lessons:

- H1, H2, and H3 headings
- paragraphs
- bold and italic text
- bullet and numbered lists
- fenced text/code blocks
- links

ReportLab's standard fonts do not reliably support every Unicode box-drawing glyph. Immediately before a fenced block is rendered in Courier, PDF-only normalization maps box lines, corners, intersections, and arrows to aligned ASCII equivalents—for example, `┌ ─ │ ▼` becomes `+ - | v`.

This normalization affects only `lesson.pdf`. It does not modify `raw_lesson.md`, `final_lesson.md`, or the browser-rendered lesson.

## Interfaces

### Command line

Run the required topic:

```bash
python main.py --topic "Introduction to RAG"
```

Run another topic:

```bash
python main.py --topic "Introduction to SQL Joins"
```

The CLI prints the lesson, source and evaluation summary, retry and memory information, and generated artifact paths.

### FastAPI

Primary routes:

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Serves the browser frontend |
| `GET` | `/health` | Returns `{"status": "ok"}` |
| `POST` | `/api/lessons/generate` | Runs the synchronous workflow and, on PASS, artifact export |
| `GET` | `/outputs/<run-folder>/<file>` | Serves generated artifacts |

Example request:

```json
{
  "topic": "Introduction to RAG"
}
```

The response retains `topic`, `lesson`, `evaluation` (including its checks and `overall_pass`), `retry_count`, `rejection_history`, `sources`, `memory_guidance`, and `artifacts`. There is no separate `presentation_lesson` response field.

When the final quality gate passes, `lesson` contains the presentation lesson used for `final_lesson.md` and `lesson.pdf`. Its `artifacts` object separately contains `pdf_url`, `markdown_url`, `rejection_log_url`, and `cleanup_applied`; the exact raw lesson remains in `raw_lesson.md`.

A completed workflow whose final evaluator result is FAIL returns HTTP 200 because the workflow itself completed normally. In that case, `lesson` remains the final raw workflow lesson, `evaluation.overall_pass` is `false`, `artifacts` is `null`, and artifact export is not run. Provider failures are separate operational errors: rate limits are translated to HTTP 429, temporary model unavailability to HTTP 503, and other provider or research failures to an appropriate error response.

### Browser frontend

The frontend uses plain HTML, CSS, and vanilla JavaScript served directly by FastAPI. No Node/npm runtime is required. It intentionally keeps the learner-facing view focused on the rendered final lesson and its Download PDF and Download Markdown actions.

Evaluation, retry, rejection, source, memory, and artifact metadata remain available in backend/API structures for debugging and programmatic use without cluttering the normal lesson view. Markdown is sanitized before being inserted into the page, and external lesson links open in a separate tab with safe link attributes.

## Project structure

```text
.
├── src/
│   ├── __init__.py
│   ├── api.py
│   ├── artifacts.py
│   ├── evaluator.py
│   ├── gemini_utils.py
│   ├── generator.py
│   ├── graph.py
│   ├── grounding.py
│   ├── memory.py
│   ├── retry.py
│   ├── state.py
│   └── workflow.py
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
│   └── test_artifacts.py
├── data/
│   └── lesson_memory.db       # runtime, Git-ignored
├── outputs/                   # generated artifacts, Git-ignored
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation and setup

### Prerequisites

- Python 3.10.11 — tested development/runtime version
- Git
- A Gemini API key

### Clone the repository

```bash
git clone <repository-url>
cd nxtwave
```

### Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Configure environment variables

Copy the template:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. The checked-in model configuration is:

```dotenv
GEMINI_API_KEY=
RESEARCH_MODEL=gemini-3.6-flash
GENERATOR_MODEL=gemini-3.6-flash
EVALUATOR_MODEL=gemini-3.5-flash
CLEANUP_MODEL=gemini-2.5-flash-lite
```

| Variable | Role |
|---|---|
| `GEMINI_API_KEY` | Authenticates Gemini requests |
| `RESEARCH_MODEL` | Builds the grounded research brief using Google Search |
| `GENERATOR_MODEL` | Generates and corrects the lesson; configured for minimal thinking and temperature `0.4` |
| `EVALUATOR_MODEL` | Returns structured quality checks; configured for medium thinking |
| `CLEANUP_MODEL` | Optional whitespace-only presentation cleanup model |

If `CLEANUP_MODEL` is empty, cleanup falls back in order to `RESEARCH_MODEL`, then `GENERATOR_MODEL`, then its code default. Cleanup does not use Google Search.

Do not commit `.env`; it is ignored by Git.

## Running the application

### Browser and API

Start FastAPI from the repository root:

```bash
python -m uvicorn src.api:app --reload
```

Open `http://127.0.0.1:8000` for the frontend. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

An API request can be sent with:

```bash
curl -X POST "http://127.0.0.1:8000/api/lessons/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Introduction to RAG"}'
```

The endpoint is synchronous: it returns after research, generation, evaluation, any required correction, and memory persistence. When the final quality gate passes, it also waits for artifact creation; a terminal FAIL skips artifact export.

### CLI

```bash
python main.py --topic "Introduction to RAG"
```

Both interfaces use the same LangGraph workflow and artifact exporter.

## Tests and validation

Run the offline unit tests:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The current test verifies that Unicode box-drawing diagrams are converted to aligned ASCII only for PDF rendering, ordinary code remains unchanged, and the generated file is a non-empty PDF.

Additional local checks:

```bash
python -m compileall -q main.py src
python -m pip check
```

These checks and unit tests do not require a live Gemini request.

## Design decisions and trade-offs

| Decision | Rationale and trade-off |
|---|---|
| Dynamic research instead of static topic files | Keeps the workflow topic-agnostic, with grounding quality dependent on retrieved evidence. |
| Shared grounding context | Gives the generator and evaluator the same evidence and avoids inconsistent independent research. |
| Deterministic LangGraph routing instead of a supervisor LLM | PASS/FAIL and retry-count decisions are deterministic, avoiding unnecessary model cost, latency, and nondeterminism. |
| Binary evaluator | Provides the hard shipping gates required by the assessment rather than partial scores. |
| Bounded retries | Allows at most two regenerations and three total lesson attempts, preventing uncontrolled loops and model cost. |
| SQLite memory | Provides simple durable persistence appropriate for a local take-home system without distributed-storage complexity. |
| Lightweight frontend | Keeps attention on the content system instead of frontend framework complexity. |
| Post-evaluation presentation cleanup | Repairs formatting only after evaluation, so cleanup cannot influence quality-gate results. |
| Separate raw and final artifacts | Preserves traceability while still providing polished learner-facing output. |

## Known limitations and future improvements

- Grounding quality depends on the sources returned by Google Search, and grounding metadata may contain Google redirect URLs.
- Source-authority ranking could be strengthened beyond the current prompt-level preference for primary and recognized sources.
- The API is synchronous, so clients wait for the complete workflow and any successful export.
- SQLite is appropriate for local or single-instance use, not distributed scale.
- Provider quota and availability can produce HTTP 429 or 503 responses.
- Streaming progress events and richer workflow observability are future improvements.

## Security

- `.env` is Git-ignored, and the Gemini API key is not committed.
- API keys and environment variables are never returned to the frontend.
- `outputs/` and `data/lesson_memory.db` are Git-ignored runtime data.
- API and provider errors returned to clients are sanitized rather than exposing internal exceptions or stack traces.

## Troubleshooting

| Problem | Resolution |
|---|---|
| `GEMINI_API_KEY is not set` | Copy `.env.example` to `.env` and set `GEMINI_API_KEY` to a valid key. |
| Gemini/API returns HTTP 429 | The provider rate limit or quota was reached. Wait for quota availability, then retry. |
| Gemini/API returns HTTP 503 | The selected model is temporarily unavailable or under high demand. Retry later. |
| PowerShell blocks virtual-environment activation | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, then run `.\.venv\Scripts\Activate.ps1` again. |
| Port 8000 is already in use | Start on another port with `python -m uvicorn src.api:app --reload --port 8001`. |

## Submission

Required demonstration topic: **Introduction to RAG**.

The system itself accepts arbitrary researchable educational topics.
