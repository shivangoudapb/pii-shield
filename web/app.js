"use strict";

// This mapping exists only in this page's memory. It is sent back only to /restore.
let currentMapping = {};

const samples = {
  resume: "Resume contact: Dr. Ananya Rao | mobile +91 98450 12345 | mail ananya.rao@example.com\nAddress: 18 Cedar Cross, Sample Nagar, Bengaluru 560001",
  whatsapp: "hii team 👋 sagar can u share ur resume? call 98450-12345\nfwd: pls send the draft to kiran@example.com today",
  invoice: "Invoice to Kavya Menon; phone 09845012345; PAN ABCDE1234F\nAadhaar ref: 234567890123 (synthetic invalid checksum; should not be flagged)\nShip to 18 Maple Road, Demo Layout, Pune 411001",
};

const sourceText = document.querySelector("#source-text");
const redactButton = document.querySelector("#redact-button");
const redactStatus = document.querySelector("#redact-status");
const results = document.querySelector("#redacted-results");
const redactedText = document.querySelector("#redacted-text");
const highlightedText = document.querySelector("#highlighted-text");
const replyText = document.querySelector("#reply-text");
const restoreButton = document.querySelector("#restore-button");
const restoreStatus = document.querySelector("#restore-status");

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
    mark.title = span.label;
    mark.textContent = text.slice(span.start, span.end);
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

redactButton.addEventListener("click", async () => {
  const text = sourceText.value;
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
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Could not redact this text.");
    currentMapping = payload.mapping;
    redactedText.value = payload.redacted;
    renderHighlights(text, payload.spans);
    document.querySelector("#span-count").textContent = `${payload.spans.length} found`;
    results.classList.remove("hidden");
    redactStatus.textContent = payload.spans.length ? "Review the highlighted details before copying." : "No supported PII patterns were detected.";
    restoreStatus.textContent = "Mapping ready in this tab. It is sent only when you restore a reply.";
  } catch (error) {
    redactStatus.textContent = error.message || "Connection failed. Please try again.";
  } finally {
    setBusy(redactButton, false, "Redact →");
  }
});

restoreButton.addEventListener("click", async () => {
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
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Could not restore this reply.");
    document.querySelector("#restored-text").value = payload.restored;
    document.querySelector("#restored-results").classList.remove("hidden");
    restoreStatus.textContent = "Reply restored.";
  } catch (error) {
    restoreStatus.textContent = error.message || "Connection failed. Please try again.";
  } finally {
    setBusy(restoreButton, false, "Restore →");
  }
});

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => {
    sourceText.value = samples[button.dataset.sample];
    sourceText.focus();
    redactStatus.textContent = "Synthetic sample loaded. Select Redact to preview.";
  });
});

document.querySelector("#copy-redacted").addEventListener("click", () => copyFrom(redactedText, redactStatus));
document.querySelector("#copy-restored").addEventListener("click", () => copyFrom(document.querySelector("#restored-text"), restoreStatus));
