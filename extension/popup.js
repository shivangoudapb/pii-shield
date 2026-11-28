"use strict";

const healthDot = document.querySelector("#health-dot");
const healthText = document.querySelector("#health-text");
const sessionCount = document.querySelector("#session-count");
const clearBtn = document.querySelector("#clear-session");
const quickInput = document.querySelector("#quick-input");
const quickRedactBtn = document.querySelector("#quick-redact");
const quickRestoreBtn = document.querySelector("#quick-restore");
const quickStatus = document.querySelector("#quick-status");
const modeSelect = document.querySelector("#mode-select");
const customUrlInput = document.querySelector("#custom-url");
const fallbackToggle = document.querySelector("#fallback-toggle");
const reviewToggle = document.querySelector("#review-toggle");

function sendBg(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(message, (res) => {
        try {
          const lastErr = chrome.runtime.lastError;
          resolve(res || { ok: false, error: lastErr?.message || "No response" });
        } catch {
          resolve({ ok: false, error: "Extension context invalidated." });
        }
      });
    } catch (err) {
      resolve({ ok: false, error: err?.message || "Extension runtime unavailable." });
    }
  });
}

function updateSessionLabel(mapping) {
  const count = Object.keys(mapping || {}).length;
  sessionCount.textContent = `${count} placeholder${count === 1 ? "" : "s"} mapped in this browser session.`;
}

async function refreshHealth() {
  healthDot.className = "dot dot-pending";
  healthText.textContent = "Checking service…";
  const res = await sendBg({ type: "PII_SHIELD_HEALTH" });
  if (res.ok) {
    healthDot.className = "dot dot-ok";
    let host = res.endpointUsed || "server";
    try {
      host = new URL(res.endpointUsed).hostname;
    } catch {
      // Keep raw string fallback.
    }
    healthText.textContent = `Connected (${host})`;
  } else {
    healthDot.className = "dot dot-err";
    healthText.textContent = res.error || "Service unreachable";
  }
}

async function initPopup() {
  const res = await sendBg({ type: "PII_SHIELD_GET_SESSION" });
  if (res.ok) {
    updateSessionLabel(res.sessionMapping);
    const s = res.settings;
    modeSelect.value = s.mode || "cloud_run";
    customUrlInput.value = s.customUrl || "";
    customUrlInput.classList.toggle("hidden", modeSelect.value !== "custom");
    fallbackToggle.checked = Boolean(s.autoFallbackToModal);
    reviewToggle.checked = Boolean(s.reviewBeforeReplace);
  }
  await refreshHealth();
}

async function saveCurrentSettings() {
  customUrlInput.classList.toggle("hidden", modeSelect.value !== "custom");
  await sendBg({
    type: "PII_SHIELD_SAVE_SETTINGS",
    settings: {
      mode: modeSelect.value,
      customUrl: customUrlInput.value.trim(),
      autoFallbackToModal: fallbackToggle.checked,
      reviewBeforeReplace: reviewToggle.checked,
    },
  });
  await refreshHealth();
}

modeSelect.addEventListener("change", saveCurrentSettings);
customUrlInput.addEventListener("change", saveCurrentSettings);
fallbackToggle.addEventListener("change", saveCurrentSettings);
reviewToggle.addEventListener("change", saveCurrentSettings);

clearBtn.addEventListener("click", async () => {
  const res = await sendBg({ type: "PII_SHIELD_CLEAR_SESSION" });
  if (res.ok) {
    updateSessionLabel({});
    quickStatus.textContent = "Cleared session mapping.";
  }
});

quickRedactBtn.addEventListener("click", async () => {
  const text = quickInput.value;
  if (!text.trim()) {
    quickStatus.textContent = "Paste some text first.";
    return;
  }
  quickRedactBtn.disabled = true;
  quickStatus.textContent = "Redacting in memory…";
  const detected = await sendBg({ type: "PII_SHIELD_DETECT", text });
  quickRedactBtn.disabled = false;
  if (!detected.ok) {
    quickStatus.textContent = detected.error || "Redaction failed.";
    return;
  }
  const committed = await sendBg({
    type: "PII_SHIELD_COMMIT_REDACTION",
    redacted: detected.payload.redacted,
    mapping: detected.payload.mapping,
  });
  if (!committed.ok) {
    quickStatus.textContent = committed.error || "Could not save session mapping.";
    return;
  }
  quickInput.value = committed.redacted;
  updateSessionLabel(committed.sessionMapping);
  await navigator.clipboard.writeText(committed.redacted).catch(() => {});
  quickStatus.textContent = `Redacted (${detected.payload.spans.length} found) & copied!`;
});

quickRestoreBtn.addEventListener("click", async () => {
  const text = quickInput.value;
  if (!text.trim()) {
    quickStatus.textContent = "Paste an AI reply with placeholders first.";
    return;
  }
  const res = await sendBg({ type: "PII_SHIELD_RESTORE_TEXT", text });
  if (res.ok) {
    quickInput.value = res.restored;
    await navigator.clipboard.writeText(res.restored).catch(() => {});
    quickStatus.textContent = "Restored & copied!";
  }
});

initPopup().catch(() => {});
