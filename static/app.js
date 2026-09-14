const form = document.querySelector("#lesson-form");
const topicInput = document.querySelector("#topic");
const topicError = document.querySelector("#topic-error");
const generateButton = document.querySelector("#generate-button");
const loadingState = document.querySelector("#loading-state");
const errorBanner = document.querySelector("#error-banner");
const failureView = document.querySelector("#failure-view");
const resultView = document.querySelector("#result-view");

let workflowRunning = false;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (workflowRunning) return;

  const topic = topicInput.value.trim();
  clearErrors();
  if (!topic) {
    showTopicError("Enter a topic before generating a lesson.");
    return;
  }

  setLoading(true);
  resultView.hidden = true;
  failureView.hidden = true;

  try {
    const response = await fetch("/api/lessons/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    const responseBody = await readJson(response);

    if (!response.ok) {
      handleApiError(response.status);
      return;
    }

    renderResult(responseBody);
  } catch (error) {
    showError("Something went wrong while running the lesson workflow.");
  } finally {
    setLoading(false);
  }
});

topicInput.addEventListener("input", clearErrors);

async function readJson(response) {
  try {
    return await response.json();
  } catch (error) {
    return {};
  }
}

function setLoading(isLoading) {
  workflowRunning = isLoading;
  generateButton.disabled = isLoading;
  generateButton.textContent = isLoading ? "Generating..." : "Generate lesson";
  loadingState.hidden = !isLoading;
  form.setAttribute("aria-busy", String(isLoading));
}

function clearErrors() {
  topicInput.removeAttribute("aria-invalid");
  topicError.hidden = true;
  topicError.textContent = "";
  errorBanner.hidden = true;
  errorBanner.textContent = "";
}

function showTopicError(message) {
  topicInput.setAttribute("aria-invalid", "true");
  topicError.textContent = message;
  topicError.hidden = false;
  topicInput.focus();
}

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.hidden = false;
}

function handleApiError(status) {
  if (status === 422) {
    showTopicError("Enter a valid, non-empty topic.");
  } else if (status === 429) {
    showError("Model rate limit reached. Please try again later.");
  } else if (status === 503) {
    showError("AI model service is temporarily unavailable. Please try again.");
  } else {
    showError("Something went wrong while running the lesson workflow.");
  }
}

function renderResult(result) {
  if (!result.evaluation.overall_pass) {
    document.querySelector("#artifact-links").hidden = true;
    resultView.hidden = true;
    failureView.hidden = false;
    failureView.focus();
    return;
  }

  const presentationLesson = result.presentation_lesson || result.lesson || "";
  renderLessonMarkdown(presentationLesson);
  renderArtifacts(result.artifacts);
  failureView.hidden = true;
  resultView.hidden = false;
  resultView.focus();
}

function renderLessonMarkdown(markdown) {
  const lessonContent = document.querySelector("#lesson-content");
  lessonContent.replaceChildren();

  if (window.marked && window.DOMPurify) {
    const rendered = window.marked.parse(markdown, { gfm: true });
    lessonContent.innerHTML = window.DOMPurify.sanitize(rendered);
    lessonContent.querySelectorAll("a[href]").forEach((link) => {
      const url = new URL(link.href, window.location.href);
      if (url.protocol === "http:" || url.protocol === "https:") {
        link.target = "_blank";
        link.rel = "noopener noreferrer";
      }
    });
    return;
  }

  lessonContent.append(createElement("pre", "markdown-fallback", markdown));
}

function renderArtifacts(artifacts) {
  const artifactLinks = document.querySelector("#artifact-links");
  artifactLinks.hidden = true;
  if (!artifacts || !artifacts.pdf_url || !artifacts.markdown_url) return;

  const pdfLink = document.querySelector("#download-pdf");
  const markdownLink = document.querySelector("#download-markdown");
  pdfLink.href = artifacts.pdf_url;
  pdfLink.download = "lesson.pdf";
  markdownLink.href = artifacts.markdown_url;
  markdownLink.download = "final_lesson.md";
  artifactLinks.hidden = false;
}

function createElement(tagName, className = "", text = "") {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}
