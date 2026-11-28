"use strict";

importScripts("shared.js");

const {
  DEFAULT_CLOUD_RUN_URL,
  DEFAULT_MODAL_FALLBACK_URL,
  DEFAULT_LOCAL_URL,
  mergeIntoSessionMapping,
  restorePlaceholders,
} = globalThis.PiiShieldShared;

const SETTINGS_KEY = "pii_shield_settings_v1";
const SESSION_MAPPING_KEY = "pii_shield_session_mapping_v1";

const DEFAULT_SETTINGS = {
  mode: "cloud_run", // "cloud_run" | "modal" | "local" | "custom"
  customUrl: "",
  autoFallbackToModal: true,
  reviewBeforeReplace: true,
};

async function getSettings() {
  const stored = await chrome.storage.local.get(SETTINGS_KEY);
  return { ...DEFAULT_SETTINGS, ...(stored[SETTINGS_KEY] || {}) };
}

async function saveSettings(partial) {
  const next = { ...(await getSettings()), ...(partial || {}) };
  await chrome.storage.local.set({ [SETTINGS_KEY]: next });
  return next;
}

async function getSessionMapping() {
  const stored = await chrome.storage.session.get(SESSION_MAPPING_KEY);
  return stored[SESSION_MAPPING_KEY] || {};
}

async function setSessionMapping(mapping) {
  await chrome.storage.session.set({ [SESSION_MAPPING_KEY]: mapping || {} });
  return mapping || {};
}

function resolveCandidateEndpoints(settings) {
  const clean = (url) => String(url || "").trim().replace(/\/+$/, "");
  if (settings.mode === "local") {
    return [clean(settings.customUrl) || DEFAULT_LOCAL_URL];
  }
  if (settings.mode === "modal") {
    return [DEFAULT_MODAL_FALLBACK_URL];
  }
  if (settings.mode === "custom" && clean(settings.customUrl)) {
    const list = [clean(settings.customUrl)];
    if (settings.autoFallbackToModal) list.push(DEFAULT_MODAL_FALLBACK_URL);
    return list;
  }
  const endpoints = [DEFAULT_CLOUD_RUN_URL];
  if (settings.autoFallbackToModal) {
    endpoints.push(DEFAULT_MODAL_FALLBACK_URL);
  }
  return endpoints;
}

async function callBackendWithFailover(path, options = {}) {
  const settings = await getSettings();
  const endpoints = resolveCandidateEndpoints(settings);
  let lastError = null;

  for (const baseUrl of endpoints) {
    try {
      const response = await fetch(`${baseUrl}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
      });
      // Do not fail over on client input errors (413 oversized, 422 invalid, 429 rate-limit).
      if (response.status >= 400 && response.status < 500) {
        const errBody = await response.json().catch(() => ({}));
        if (response.status === 429) {
          const retry = response.headers.get("Retry-After");
          throw new Error(
            retry
              ? `Rate limit reached. Please wait ${retry}s and try again.`
              : errBody.detail || "Rate limit reached."
          );
        }
        throw new Error(errBody.detail || `Request rejected (HTTP ${response.status}).`);
      }
      if (!response.ok) {
        throw new Error(`Server unavailable at ${baseUrl} (HTTP ${response.status}).`);
      }
      const data = await response.json();
      return { data, endpointUsed: baseUrl };
    } catch (err) {
      lastError = err;
      // If it was a 4xx validation/size/rate error, stop immediately without hitting fallback.
      if (
        err instanceof Error &&
        (err.message.includes("character limit") ||
          err.message.includes("Rate limit") ||
          err.message.includes("Request rejected"))
      ) {
        throw err;
      }
    }
  }
  throw lastError || new Error("Could not reach PII Shield server.");
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const safeReply = (payload) => {
    try {
      sendResponse(payload);
    } catch {
      // Sender tab/popup closed before async response completed; ignore safely.
    }
  };

  (async () => {
    switch (message?.type) {
      case "PII_SHIELD_DETECT": {
        const { data, endpointUsed } = await callBackendWithFailover("/redact", {
          method: "POST",
          body: JSON.stringify({ text: message.text || "" }),
        });
        safeReply({ ok: true, payload: data, endpointUsed });
        break;
      }
      case "PII_SHIELD_COMMIT_REDACTION": {
        const existing = await getSessionMapping();
        const merged = mergeIntoSessionMapping(
          message.redacted || "",
          message.mapping || {},
          existing
        );
        await setSessionMapping(merged.sessionMapping);
        safeReply({
          ok: true,
          redacted: merged.redacted,
          sessionMapping: merged.sessionMapping,
        });
        break;
      }
      case "PII_SHIELD_GET_SESSION": {
        const sessionMapping = await getSessionMapping();
        const settings = await getSettings();
        safeReply({ ok: true, sessionMapping, settings });
        break;
      }
      case "PII_SHIELD_RESTORE_TEXT": {
        const sessionMapping = await getSessionMapping();
        const restored = restorePlaceholders(message.text || "", sessionMapping);
        safeReply({ ok: true, restored, sessionMapping });
        break;
      }
      case "PII_SHIELD_CLEAR_SESSION": {
        await setSessionMapping({});
        safeReply({ ok: true, sessionMapping: {} });
        break;
      }
      case "PII_SHIELD_SAVE_SETTINGS": {
        const settings = await saveSettings(message.settings || {});
        safeReply({ ok: true, settings });
        break;
      }
      case "PII_SHIELD_HEALTH": {
        const { data, endpointUsed } = await callBackendWithFailover("/health", {
          method: "GET",
        });
        safeReply({ ok: true, health: data, endpointUsed });
        break;
      }
      default:
        safeReply({ ok: false, error: "Unknown message type." });
    }
  })().catch((err) => {
    safeReply({ ok: false, error: err?.message || "Unexpected extension error." });
  });
  return true; // Keep message channel open for async response.
});
