"use strict";

// This mapping exists only in this page's memory. It is sent back only to /restore.
let currentMapping = {};

const samples = {
  resume: "Resume contact: Dr. Ananya Rao | mobile +91 98450 12345 | mail ananya.rao@example.com\nAddress: 18 Cedar Cross, Sample Nagar, Bengaluru 560001",
  whatsapp: "hii team 👋 sagar can u share ur resume? call 98450-12345\nfwd: pls send the draft to kiran@example.com today",
  invoice: "Invoice to Kavya Menon; phone 09845012345; PAN ABCDE1234F\nAadhaar ref: 234567890123 (synthetic invalid checksum; should not be flagged)\nShip to 18 Maple Road, Demo Layout, Pune 411001",
};

const MAX_TEXT_CHARS = 20000;

const sourceText = document.querySelector("#source-text");
const sourceCount = document.querySelector("#source-count");
const redactButton = document.querySelector("#redact-button");
const redactStatus = document.querySelector("#redact-status");
const results = document.querySelector("#redacted-results");
const redactedText = document.querySelector("#redacted-text");
const highlightedText = document.querySelector("#highlighted-text");
const replyText = document.querySelector("#reply-text");
const replyCount = document.querySelector("#reply-count");
const restoreButton = document.querySelector("#restore-button");
const restoreStatus = document.querySelector("#restore-status");
const redactError = document.querySelector("#redact-error");
const restoreError = document.querySelector("#restore-error");

function showError(banner, message) {
  banner.querySelector(".error-message").textContent = message;
  banner.classList.remove("hidden");
}

function clearError(banner) {
  banner.classList.add("hidden");
  banner.querySelector(".error-message").textContent = "";
}

async function readErrorMessage(response, fallback) {
  const payload = await response.json().catch(() => ({}));
  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    return retryAfter
      ? `Rate limit reached. Please wait ${retryAfter}s and retry.`
      : payload.detail || "Rate limit reached. Please wait a moment and retry.";
  }
  return payload.detail || fallback;
}

function updateCharCount(textarea, countEl, button, statusEl) {
  const len = textarea.value.length;
  const over = len > MAX_TEXT_CHARS;
  countEl.textContent = `${len.toLocaleString()} / ${MAX_TEXT_CHARS.toLocaleString()}`;
  countEl.classList.toggle("char-count-over", over);
  textarea.setAttribute("aria-invalid", String(over));
  button.disabled = over;
  if (over) {
    statusEl.textContent = `Text exceeds the ${MAX_TEXT_CHARS.toLocaleString()} character limit.`;
  }
  return over;
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
  if (busy) button.dataset.originalLabel = button.textContent;
  button.textContent = busy ? label : button.dataset.originalLabel || label;
}

function renderHighlights(text, spans) {
  highlightedText.replaceChildren();
  const sorted = [...spans].sort((a, b) => a.start - b.start || a.end - b.end);
  let cursor = 0;
  for (const span of sorted) {
    if (span.start < cursor || span.end > text.length || text.slice(span.start, span.end) !== span.text) continue;
    highlightedText.append(document.createTextNode(text.slice(cursor, span.start)));
    const mark = document.createElement("mark");
    mark.className = `entity entity-${String(span.label).toLowerCase()}`;
    const hasScore = typeof span.score === "number" && Number.isFinite(span.score);
    const scorePct = hasScore ? Math.round(span.score * 100) : null;
    const sourceTextLabel = span.source ? `, ${span.source}` : "";
    const metaLabel = scorePct !== null ? `${span.label} (${scorePct}%${sourceTextLabel})` : span.label;
    mark.title = metaLabel;
    mark.setAttribute("aria-label", `${text.slice(span.start, span.end)} — ${metaLabel}`);
    mark.textContent = text.slice(span.start, span.end);
    if (scorePct !== null) {
      const badge = document.createElement("span");
      badge.className = "entity-score";
      badge.setAttribute("aria-hidden", "true");
      badge.textContent = `${scorePct}%`;
      mark.append(" ", badge);
    }
    highlightedText.append(mark);
    cursor = span.end;
  }
  highlightedText.append(document.createTextNode(text.slice(cursor)));
}

async function copyFrom(element, statusElement) {
  try {
    await navigator.clipboard.writeText(element.value);
    statusElement.textContent = "Copied to clipboard.";
  } catch {
    element.focus();
    element.select();
    statusElement.textContent = "Select and copy the text.";
  }
}

async function runRedact() {
  clearError(redactError);
  const text = sourceText.value;
  if (updateCharCount(sourceText, sourceCount, redactButton, redactStatus)) return;
  if (!text.trim()) {
    redactStatus.textContent = "Paste some text first.";
    return;
  }
  setBusy(redactButton, true, "Loading model…");
  redactStatus.textContent = "Processing in memory…";
  try {
    const response = await fetch("/redact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, "Could not redact this text."));
    }
    const payload = await response.json();
    currentMapping = payload.mapping;
    redactedText.value = payload.redacted;
    renderHighlights(text, payload.spans);
    document.querySelector("#span-count").textContent = `${payload.spans.length} found`;
    results.classList.remove("hidden");
    redactStatus.textContent = payload.spans.length ? "Review the highlighted details before copying." : "No supported PII patterns were detected.";
    restoreStatus.textContent = "Mapping ready in this tab. It is sent only when you restore a reply.";
  } catch (error) {
    const message = error.message || "Connection failed. Please try again.";
    redactStatus.textContent = "Redaction failed.";
    showError(redactError, message);
  } finally {
    setBusy(redactButton, false, "Redact →");
  }
}

async function runRestore() {
  clearError(restoreError);
  if (updateCharCount(replyText, replyCount, restoreButton, restoreStatus)) return;
  if (!replyText.value.trim()) {
    restoreStatus.textContent = "Paste the AI reply first.";
    return;
  }
  setBusy(restoreButton, true, "Restoring…");
  restoreStatus.textContent = "Restoring with the in-memory mapping…";
  try {
    const response = await fetch("/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: replyText.value, mapping: currentMapping }),
    });
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, "Could not restore this reply."));
    }
    const payload = await response.json();
    document.querySelector("#restored-text").value = payload.restored;
    document.querySelector("#restored-results").classList.remove("hidden");
    restoreStatus.textContent = "Reply restored.";
  } catch (error) {
    const message = error.message || "Connection failed. Please try again.";
    restoreStatus.textContent = "Restore failed.";
    showError(restoreError, message);
  } finally {
    setBusy(restoreButton, false, "Restore →");
  }
}

redactButton.addEventListener("click", runRedact);
restoreButton.addEventListener("click", runRestore);
redactError.querySelector(".error-retry").addEventListener("click", runRedact);
redactError.querySelector(".error-dismiss").addEventListener("click", () => clearError(redactError));
restoreError.querySelector(".error-retry").addEventListener("click", runRestore);
restoreError.querySelector(".error-dismiss").addEventListener("click", () => clearError(restoreError));

sourceText.addEventListener("input", () => {
  const wasOver = sourceCount.classList.contains("char-count-over");
  const over = updateCharCount(sourceText, sourceCount, redactButton, redactStatus);
  if (wasOver && !over) redactStatus.textContent = "Ready when you are.";
});

replyText.addEventListener("input", () => {
  const wasOver = replyCount.classList.contains("char-count-over");
  const over = updateCharCount(replyText, replyCount, restoreButton, restoreStatus);
  if (wasOver && !over) restoreStatus.textContent = "Uses the latest mapping from this tab.";
});

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => {
    sourceText.value = samples[button.dataset.sample];
    updateCharCount(sourceText, sourceCount, redactButton, redactStatus);
    sourceText.focus();
    redactStatus.textContent = "Synthetic sample loaded. Select Redact to preview.";
  });
});

document.querySelector("#copy-redacted").addEventListener("click", () => copyFrom(redactedText, redactStatus));
document.querySelector("#copy-restored").addEventListener("click", () => copyFrom(document.querySelector("#restored-text"), restoreStatus));
