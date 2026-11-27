"use strict";

// This mapping exists in this page's memory (and optionally browser localStorage history). It is sent back only to /restore.
let currentMapping = {};
let lastSourceText = "";
let lastSpans = [];
let disabledSpanIndices = new Set();
let activeSessionId = null;

const HISTORY_STORAGE_KEY = "pii_shield_sessions_v1";
const MAX_HISTORY_ITEMS = 10;

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
const sessionHistoryPanel = document.querySelector("#session-history");
const historyList = document.querySelector("#history-list");
const clearHistoryButton = document.querySelector("#clear-history");

function loadSessionsFromStorage() {
  try {
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item) =>
        item &&
        typeof item.id === "string" &&
        typeof item.redacted === "string" &&
        item.mapping &&
        typeof item.mapping === "object"
    );
  } catch {
    return [];
  }
}

function saveSessionsToStorage(sessions) {
  try {
    if (!sessions.length) {
      window.localStorage.removeItem(HISTORY_STORAGE_KEY);
    } else {
      window.localStorage.setItem(
        HISTORY_STORAGE_KEY,
        JSON.stringify(sessions.slice(0, MAX_HISTORY_ITEMS))
      );
    }
  } catch {
    // Ignore storage quota or private-mode restrictions.
  }
}

function formatSessionTime(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "Saved session";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) +
    " · " +
    date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function renderSessionHistory() {
  const sessions = loadSessionsFromStorage();
  historyList.replaceChildren();
  if (!sessions.length) {
    sessionHistoryPanel.classList.add("hidden");
    return;
  }
  sessionHistoryPanel.classList.remove("hidden");
  for (const session of sessions) {
    const li = document.createElement("li");
    const isActive = session.id === activeSessionId;
    li.className = `history-item${isActive ? " history-item-active" : ""}`;

    const meta = document.createElement("div");
    meta.className = "history-meta";

    const snippet = document.createElement("span");
    snippet.className = "history-snippet";
    const compactPreview = session.redacted.replace(/\s+/g, " ").trim();
    snippet.textContent = compactPreview.slice(0, 72) || "(empty redacted text)";

    const count = Object.keys(session.mapping).length;
    const sub = document.createElement("span");
    sub.className = "history-sub";
    sub.textContent = `${formatSessionTime(session.createdAt)} · ${count} placeholder${count === 1 ? "" : "s"}${isActive ? " · active" : ""}`;

    meta.append(snippet, sub);

    const actions = document.createElement("div");
    actions.className = "history-actions";

    const useBtn = document.createElement("button");
    useBtn.type = "button";
    useBtn.className = "button button-quiet";
    useBtn.textContent = isActive ? "Active" : "Use";
    useBtn.disabled = isActive;
    useBtn.addEventListener("click", () => {
      currentMapping = { ...session.mapping };
      activeSessionId = session.id;
      redactedText.value = session.redacted;
      restoreStatus.textContent = `Loaded saved mapping (${count} placeholder${count === 1 ? "" : "s"}). Paste the AI reply to restore.`;
      renderSessionHistory();
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "button button-quiet";
    removeBtn.setAttribute("aria-label", "Remove saved session");
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      const remaining = loadSessionsFromStorage().filter((item) => item.id !== session.id);
      if (activeSessionId === session.id) {
        activeSessionId = null;
      }
      saveSessionsToStorage(remaining);
      renderSessionHistory();
    });

    actions.append(useBtn, removeBtn);
    li.append(meta, actions);
    historyList.append(li);
  }
}

function recordSessionHistory(redacted, mapping) {
  const keys = Object.keys(mapping || {});
  if (!keys.length) {
    activeSessionId = null;
    renderSessionHistory();
    return;
  }
  const session = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    redacted,
    mapping: { ...mapping },
  };
  activeSessionId = session.id;
  const existing = loadSessionsFromStorage();
  saveSessionsToStorage([session, ...existing].slice(0, MAX_HISTORY_ITEMS));
  renderSessionHistory();
}

function syncActiveSessionHistory() {
  if (!activeSessionId) {
    if (Object.keys(currentMapping).length) {
      recordSessionHistory(redactedText.value, currentMapping);
    }
    return;
  }
  const sessions = loadSessionsFromStorage();
  const idx = sessions.findIndex((item) => item.id === activeSessionId);
  if (idx === -1) return;
  if (!Object.keys(currentMapping).length) {
    sessions.splice(idx, 1);
    activeSessionId = null;
  } else {
    sessions[idx] = {
      ...sessions[idx],
      redacted: redactedText.value,
      mapping: { ...currentMapping },
    };
  }
  saveSessionsToStorage(sessions);
  renderSessionHistory();
}

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

function normaliseEntity(value) {
  return value.toLowerCase().trim().split(/\s+/).join(" ");
}

function buildRedactionFromSpans(text, spans, disabledSet) {
  const mapping = {};
  const placeholders = new Map();
  const counters = {};
  const parts = [];
  let cursor = 0;
  let activeCount = 0;

  spans.forEach((span, idx) => {
    if (disabledSet.has(idx)) return;
    if (span.start < cursor || span.end > text.length) return;
    const original = text.slice(span.start, span.end);
    if (original !== span.text) return;

    parts.push(text.slice(cursor, span.start));
    const key = `${span.label}\u0000${normaliseEntity(original)}`;
    let placeholder = placeholders.get(key);
    if (!placeholder) {
      counters[span.label] = (counters[span.label] || 0) + 1;
      placeholder = `[${span.label}_${counters[span.label]}]`;
      placeholders.set(key, placeholder);
      mapping[placeholder] = original;
    }
    parts.push(placeholder);
    cursor = span.end;
    activeCount += 1;
  });

  parts.push(text.slice(cursor));
  return { redacted: parts.join(""), mapping, activeCount };
}

function updateSpanCountPill(total, active) {
  const pill = document.querySelector("#span-count");
  pill.textContent = active === total ? `${total} found` : `${active} of ${total} redacted`;
}

function applySelectiveRedaction() {
  const { redacted, mapping, activeCount } = buildRedactionFromSpans(
    lastSourceText,
    lastSpans,
    disabledSpanIndices
  );
  currentMapping = mapping;
  redactedText.value = redacted;
  updateSpanCountPill(lastSpans.length, activeCount);
}

function toggleSpanAt(index, markEl, spanText, metaLabel) {
  if (disabledSpanIndices.has(index)) {
    disabledSpanIndices.delete(index);
  } else {
    disabledSpanIndices.add(index);
  }
  const isRedacted = !disabledSpanIndices.has(index);
  markEl.classList.toggle("entity-disabled", !isRedacted);
  markEl.setAttribute("aria-pressed", String(isRedacted));
  const stateLabel = isRedacted ? "redacted" : "kept unredacted";
  markEl.setAttribute("aria-label", `${spanText} — ${metaLabel}, ${stateLabel}`);
  applySelectiveRedaction();
  if (typeof syncActiveSessionHistory === "function") {
    syncActiveSessionHistory();
  }
}

function renderHighlights(text, spans) {
  highlightedText.replaceChildren();
  const validSpans = [];
  const sorted = [...spans].sort((a, b) => a.start - b.start || a.end - b.end);
  let cursor = 0;
  for (const span of sorted) {
    if (span.start < cursor || span.end > text.length || text.slice(span.start, span.end) !== span.text) continue;
    const spanIndex = validSpans.length;
    validSpans.push(span);
    highlightedText.append(document.createTextNode(text.slice(cursor, span.start)));
    const spanSlice = text.slice(span.start, span.end);
    const mark = document.createElement("mark");
    mark.className = `entity entity-${String(span.label).toLowerCase()}`;
    mark.setAttribute("role", "button");
    mark.tabIndex = 0;
    mark.setAttribute("aria-pressed", "true");
    const hasScore = typeof span.score === "number" && Number.isFinite(span.score);
    const scorePct = hasScore ? Math.round(span.score * 100) : null;
    const sourceTextLabel = span.source ? `, ${span.source}` : "";
    const metaLabel = scorePct !== null ? `${span.label} (${scorePct}%${sourceTextLabel})` : span.label;
    mark.title = `${metaLabel} — click to toggle redaction`;
    mark.setAttribute("aria-label", `${spanSlice} — ${metaLabel}, redacted`);
    mark.textContent = spanSlice;
    if (scorePct !== null) {
      const badge = document.createElement("span");
      badge.className = "entity-score";
      badge.setAttribute("aria-hidden", "true");
      badge.textContent = `${scorePct}%`;
      mark.append(" ", badge);
    }
    mark.addEventListener("click", () => toggleSpanAt(spanIndex, mark, spanSlice, metaLabel));
    mark.addEventListener("keydown", (event) => {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        toggleSpanAt(spanIndex, mark, spanSlice, metaLabel);
      }
    });
    highlightedText.append(mark);
    cursor = span.end;
  }
  highlightedText.append(document.createTextNode(text.slice(cursor)));
  return validSpans;
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
    lastSourceText = text;
    disabledSpanIndices = new Set();
    lastSpans = renderHighlights(text, payload.spans);
    currentMapping = payload.mapping;
    redactedText.value = payload.redacted;
    updateSpanCountPill(lastSpans.length, lastSpans.length);
    recordSessionHistory(payload.redacted, payload.mapping);
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
clearHistoryButton.addEventListener("click", () => {
  activeSessionId = null;
  saveSessionsToStorage([]);
  restoreStatus.textContent = "Cleared saved mappings from this browser.";
  renderSessionHistory();
});

renderSessionHistory();
