"use strict";

(function registerContentScript(root) {
  function initContentScript(customEnv) {
    const win = customEnv?.window || root;
    const doc = customEnv?.document || win.document;
    const shared = customEnv?.shared || root.PiiShieldShared;
    const runtime = customEnv?.runtime || (typeof chrome !== "undefined" ? chrome.runtime : null);
    const storage = customEnv?.storage || (typeof chrome !== "undefined" ? chrome.storage : null);
    const hostname = customEnv?.hostname || win.location?.hostname || "";

    if (!doc || !doc.body || !shared) {
      return null;
    }

    // Prevent duplicate mounting on SPA route transitions.
    const existingRoot = doc.querySelector("#piishield-ext-root");
    if (existingRoot) {
      existingRoot.remove();
    }

    let sessionMapping = {};
    let settings = { reviewBeforeReplace: true };
    let pendingState = null; // { sourceText, spans, disabledSet, editorEl }
    let contextInvalidated = false;
    let debounceTimer = null;
    let observer = null;
    let storageListener = null;

    function isRuntimeValid() {
      if (contextInvalidated || !runtime || typeof runtime.sendMessage !== "function") {
        return false;
      }
      try {
        if ("id" in runtime && !runtime.id) {
          contextInvalidated = true;
          return false;
        }
        return true;
      } catch {
        contextInvalidated = true;
        return false;
      }
    }

    function cleanupInvalidatedContext() {
      contextInvalidated = true;
      if (debounceTimer) {
        clearTimeout(debounceTimer);
        debounceTimer = null;
      }
      if (observer) {
        observer.disconnect();
        observer = null;
      }
      if (storageListener && storage?.onChanged?.removeListener) {
        try {
          storage.onChanged.removeListener(storageListener);
        } catch {
          // Context already torn down; ignore safely.
        }
        storageListener = null;
      }
    }

    function sendMessage(msg) {
      return new Promise((resolve) => {
        if (!isRuntimeValid()) {
          cleanupInvalidatedContext();
          resolve({
            ok: false,
            invalidated: true,
            error: "Extension was reloaded — please refresh this tab (F5) once.",
          });
          return;
        }
        try {
          runtime.sendMessage(msg, (response) => {
            try {
              const lastErr = runtime.lastError;
              if (lastErr && /context invalidated/i.test(lastErr.message || "")) {
                cleanupInvalidatedContext();
                resolve({
                  ok: false,
                  invalidated: true,
                  error: "Extension was reloaded — please refresh this tab (F5) once.",
                });
                return;
              }
              resolve(
                response || {
                  ok: false,
                  error: lastErr?.message || "No response from background worker.",
                }
              );
            } catch {
              cleanupInvalidatedContext();
              resolve({
                ok: false,
                invalidated: true,
                error: "Extension was reloaded — please refresh this tab (F5) once.",
              });
            }
          });
        } catch (err) {
          cleanupInvalidatedContext();
          const isInvalidated = err && /context invalidated/i.test(err.message || "");
          resolve({
            ok: false,
            invalidated: Boolean(isInvalidated),
            error: isInvalidated
              ? "Extension was reloaded — please refresh this tab (F5) once."
              : err?.message || "Extension runtime unavailable.",
          });
        }
      });
    }

    const container = doc.createElement("div");
    container.id = "piishield-ext-root";

    const toastEl = doc.createElement("div");
    toastEl.className = "piishield-ext-toast piishield-ext-hidden";
    toastEl.setAttribute("role", "status");
    toastEl.setAttribute("aria-live", "polite");

    const popoverEl = doc.createElement("div");
    popoverEl.className = "piishield-ext-popover piishield-ext-hidden";
    popoverEl.setAttribute("role", "dialog");
    popoverEl.setAttribute("aria-label", "Review detected PII before replacing prompt");
    popoverEl.innerHTML = `
      <div class="piishield-ext-pop-head">
        <h2 class="piishield-ext-pop-title">Review detected PII</h2>
        <span class="piishield-ext-pill" id="piishield-ext-span-pill">0 found</span>
      </div>
      <p class="piishield-ext-hint">Click any highlighted detail to keep it unredacted.</p>
      <div class="piishield-ext-highlights" id="piishield-ext-highlights" tabindex="0"></div>
      <textarea class="piishield-ext-preview" id="piishield-ext-preview" readonly aria-label="Redacted prompt preview"></textarea>
      <div class="piishield-ext-actions">
        <button type="button" class="piishield-ext-btn piishield-ext-btn-quiet" id="piishield-ext-cancel">Cancel</button>
        <button type="button" class="piishield-ext-btn piishield-ext-btn-primary" id="piishield-ext-apply">Replace in Chat</button>
      </div>
    `;

    const dockEl = doc.createElement("div");
    dockEl.className = "piishield-ext-dock";
    dockEl.innerHTML = `
      <span class="piishield-ext-mark" aria-hidden="true">P</span>
      <button type="button" class="piishield-ext-btn piishield-ext-btn-primary" id="piishield-ext-shield-btn">Shield Prompt</button>
      <button type="button" class="piishield-ext-btn piishield-ext-btn-teal piishield-ext-hidden" id="piishield-ext-restore-btn">Restore</button>
    `;

    container.append(toastEl, popoverEl, dockEl);
    doc.body.appendChild(container);

    const shieldBtn = container.querySelector("#piishield-ext-shield-btn");
    const restoreBtn = container.querySelector("#piishield-ext-restore-btn");
    const spanPill = container.querySelector("#piishield-ext-span-pill");
    const highlightsBox = container.querySelector("#piishield-ext-highlights");
    const previewBox = container.querySelector("#piishield-ext-preview");
    const cancelBtn = container.querySelector("#piishield-ext-cancel");
    const applyBtn = container.querySelector("#piishield-ext-apply");

    let toastTimer = null;
    function showToast(message, isError = false, durationMs = 3500) {
      toastEl.textContent = message;
      toastEl.classList.toggle("piishield-ext-toast-error", Boolean(isError));
      toastEl.classList.remove("piishield-ext-hidden");
      if (toastTimer) clearTimeout(toastTimer);
      if (durationMs > 0) {
        toastTimer = setTimeout(() => {
          toastEl.classList.add("piishield-ext-hidden");
        }, durationMs);
      }
    }

    function updateRestoreDockButton() {
      const count = Object.keys(sessionMapping || {}).length;
      if (count > 0) {
        restoreBtn.textContent = `Restore (${count})`;
        restoreBtn.classList.remove("piishield-ext-hidden");
      } else {
        restoreBtn.classList.add("piishield-ext-hidden");
      }
    }

    function refreshPopoverPreview() {
      if (!pendingState) return;
      const built = shared.buildRedactionFromSpans(
        pendingState.sourceText,
        pendingState.spans,
        pendingState.disabledSet
      );
      pendingState.currentBuilt = built;
      previewBox.value = built.redacted;
      const total = pendingState.spans.length;
      spanPill.textContent =
        built.activeCount === total
          ? `${total} found`
          : `${built.activeCount} of ${total} redacted`;
    }

    function renderPopoverHighlights(text, spans) {
      highlightsBox.replaceChildren();
      const sorted = [...spans].sort((a, b) => a.start - b.start || a.end - b.end);
      const valid = [];
      let cursor = 0;

      for (const span of sorted) {
        if (span.start < cursor || span.end > text.length || text.slice(span.start, span.end) !== span.text) {
          continue;
        }
        const idx = valid.length;
        valid.push(span);
        highlightsBox.append(doc.createTextNode(text.slice(cursor, span.start)));

        const mark = doc.createElement("mark");
        mark.className = "piishield-ext-entity";
        mark.setAttribute("role", "button");
        mark.tabIndex = 0;
        mark.setAttribute("aria-pressed", "true");
        const pct = typeof span.score === "number" ? Math.round(span.score * 100) : null;
        mark.title = pct !== null ? `${span.label} (${pct}%) — click to toggle` : span.label;
        mark.textContent = span.text;

        if (pct !== null) {
          const scoreEl = doc.createElement("span");
          scoreEl.className = "piishield-ext-score";
          scoreEl.setAttribute("aria-hidden", "true");
          scoreEl.textContent = `${pct}%`;
          mark.appendChild(scoreEl);
        }

        const toggle = () => {
          if (!pendingState) return;
          if (pendingState.disabledSet.has(idx)) {
            pendingState.disabledSet.delete(idx);
          } else {
            pendingState.disabledSet.add(idx);
          }
          const active = !pendingState.disabledSet.has(idx);
          mark.classList.toggle("piishield-ext-entity-disabled", !active);
          mark.setAttribute("aria-pressed", String(active));
          refreshPopoverPreview();
        };

        mark.addEventListener("click", toggle);
        mark.addEventListener("keydown", (ev) => {
          if (ev.key === " " || ev.key === "Enter") {
            ev.preventDefault();
            toggle();
          }
        });

        highlightsBox.appendChild(mark);
        cursor = span.end;
      }
      highlightsBox.append(doc.createTextNode(text.slice(cursor)));
      return valid;
    }

    async function commitAndInsert(editorEl, redacted, mapping) {
      const committed = await sendMessage({
        type: "PII_SHIELD_COMMIT_REDACTION",
        redacted,
        mapping,
      });
      if (!committed.ok) {
        showToast(committed.error || "Could not save session mapping.", true);
        return false;
      }
      sessionMapping = committed.sessionMapping || {};
      updateRestoreDockButton();
      shared.setEditorText(editorEl, committed.redacted, doc);
      popoverEl.classList.add("piishield-ext-hidden");
      pendingState = null;
      const count = Object.keys(mapping || {}).length;
      showToast(
        count
          ? `Replaced ${count} personal detail${count === 1 ? "" : "s"} with placeholders.`
          : "Prompt left unchanged."
      );
      scanAssistantMessages();
      return true;
    }

    async function handleShieldClick() {
      const editorEl = shared.findComposerElement(doc, hostname);
      if (!editorEl) {
        showToast("Could not locate the AI chat input box on this page.", true);
        return;
      }
      const text = shared.getEditorText(editorEl);
      if (!text.trim()) {
        showToast("Type or paste a prompt in the chat box first.");
        return;
      }
      if (text.length > shared.MAX_TEXT_CHARS) {
        showToast(`Prompt exceeds the ${shared.MAX_TEXT_CHARS.toLocaleString()}-character limit.`, true);
        return;
      }

      shieldBtn.disabled = true;
      const prevLabel = shieldBtn.textContent;
      shieldBtn.textContent = "Scanning…";

      try {
        const res = await sendMessage({ type: "PII_SHIELD_DETECT", text });
        if (!res.ok) {
          showToast(res.error || "Could not reach PII Shield backend.", true, 5000);
          return;
        }
        const spans = res.payload?.spans || [];
        if (!spans.length) {
          showToast("No Indian PII detected in your prompt.");
          return;
        }

        if (!settings.reviewBeforeReplace) {
          await commitAndInsert(editorEl, res.payload.redacted, res.payload.mapping);
          return;
        }

        const validSpans = renderPopoverHighlights(text, spans);
        pendingState = {
          sourceText: text,
          spans: validSpans,
          disabledSet: new Set(),
          editorEl,
          currentBuilt: null,
        };
        refreshPopoverPreview();
        popoverEl.classList.remove("piishield-ext-hidden");
      } finally {
        shieldBtn.disabled = false;
        shieldBtn.textContent = prevLabel;
      }
    }

    function getExcludedPromptRoots() {
      const excluded = [container];
      const composer = shared.findComposerElement(doc, hostname);
      if (composer) {
        excluded.push(composer);
        let p = composer.parentElement;
        while (p && p !== doc.body) {
          const tag = (p.tagName || "").toUpperCase();
          if (tag === "FORM" || tag === "FIELDSET" || tag === "RICH-TEXTAREA") {
            const wrapsReplies =
              typeof p.querySelector === "function" &&
              p.querySelector("[data-message-author-role='assistant'], message-content, .font-claude-message");
            if (!wrapsReplies) {
              excluded.push(p);
            }
            break;
          }
          p = p.parentElement;
        }
      }
      return excluded;
    }

    function getUserMessageElements() {
      const site = shared.detectSiteConfig(hostname);
      const selectors = site?.userSelectors || [
        "[data-message-author-role='user']",
        "[data-testid='user-message']",
        "user-query",
      ];
      const nodes = [];
      for (const sel of selectors) {
        for (const el of doc.querySelectorAll(sel)) {
          if (!nodes.includes(el)) nodes.push(el);
        }
      }
      return nodes;
    }

    function hasEditableAncestorOrSelf(el) {
      let cur = el;
      while (cur && cur.nodeType === 1) {
        if (cur.isContentEditable) return true;
        const ce = typeof cur.getAttribute === "function" ? cur.getAttribute("contenteditable") : null;
        if (ce === "" || ce === "true" || ce === "plaintext-only") return true;
        const cls = cur.classList;
        if (
          cls &&
          (cls.contains("ProseMirror") || cls.contains("cm-editor") || cls.contains("cm-content") || cls.contains("ql-editor"))
        ) {
          return true;
        }
        const tag = (cur.tagName || "").toUpperCase();
        if (tag === "PRE" || tag === "CODE" || tag === "TEXTAREA" || tag === "INPUT") {
          return true;
        }
        cur = cur.parentElement;
      }
      return false;
    }

    function isActivelyStreaming(el) {
      let cur = el;
      while (cur && cur.nodeType === 1) {
        if (typeof cur.getAttribute === "function" && cur.getAttribute("data-is-streaming") === "true") {
          return true;
        }
        if (cur.classList && cur.classList.contains("result-streaming")) {
          return true;
        }
        cur = cur.parentElement;
      }
      if (
        el &&
        typeof el.querySelector === "function" &&
        el.querySelector(".result-streaming, [data-is-streaming='true']")
      ) {
        return true;
      }
      return false;
    }

    /**
     * Strict safety check before attaching an inline Restore button to a message container.
     * NEVER inject DOM nodes inside or around live editors (ChatGPT Canvas ProseMirror,
     * CodeMirror, Quill, contenteditable, <pre>/<code>, or streaming nodes).
     */
    function canSafelyAttachInlineChip(el) {
      if (!el || el.nodeType !== 1) return false;
      if (hasEditableAncestorOrSelf(el)) return false;
      if (isActivelyStreaming(el)) return false;
      if (
        typeof el.querySelector === "function" &&
        el.querySelector("[contenteditable='true'], [contenteditable=''], .ProseMirror, .cm-editor, textarea")
      ) {
        return false;
      }
      return true;
    }

    function getAssistantElements() {
      const site = shared.detectSiteConfig(hostname);
      const selectors = site
        ? site.assistantSelectors
        : [
            "[data-message-author-role='assistant']",
            "message-content",
            ".font-claude-message",
          ];

      const excludedPromptRoots = getExcludedPromptRoots();
      const userTurns = getUserMessageElements();
      const candidates = [];

      for (const sel of selectors) {
        for (const el of doc.querySelectorAll(sel)) {
          if (container === el || container.contains(el)) continue;
          if (
            excludedPromptRoots.some(
              (ex) => ex && ex !== container && (ex === el || ex.contains(el) || el.contains(ex))
            )
          ) {
            continue;
          }
          if (userTurns.some((u) => u === el || u.contains(el) || el.contains(u))) continue;
          candidates.push(el);
        }
      }

      // Deduplicate nested matches (e.g. Gemini `message-content` vs `.model-response-text`)
      // so each AI turn gets at most ONE inline restore chip.
      return shared.deduplicateOutermostElements(candidates);
    }

    const chipByElement = new WeakMap();
    const failedChipContainers = new WeakSet();
    let isInternalDomChange = false;

    function withInternalDomChange(fn) {
      isInternalDomChange = true;
      try {
        return fn();
      } finally {
        isInternalDomChange = false;
      }
    }

    function removeChipFor(msgEl) {
      const existing = chipByElement.get(msgEl);
      if (existing) {
        withInternalDomChange(() => existing.remove());
        chipByElement.delete(msgEl);
      }
    }

    async function restoreAllAssistantMessages() {
      // Refresh mapping from background session storage first in case the tab
      // navigated (e.g. ChatGPT `/` -> `/c/...`) or the popup updated mappings.
      const latest = await sendMessage({ type: "PII_SHIELD_GET_SESSION" });
      if (latest && latest.ok && latest.sessionMapping) {
        sessionMapping = latest.sessionMapping;
        updateRestoreDockButton();
      }

      const excluded = [...getExcludedPromptRoots(), ...getUserMessageElements()];
      let totalReplacements = 0;

      withInternalDomChange(() => {
        for (const msgEl of getAssistantElements()) {
          totalReplacements += shared.restoreElementTextNodes(msgEl, sessionMapping, excluded);
          removeChipFor(msgEl);
        }

        // Always sweep the rest of the document (excluding the prompt composer and
        // user-sent bubbles) so ChatGPT Canvas editors, copy-cards, <pre><code> boxes,
        // iframes, and Shadow DOM blocks are restored cleanly without injecting DOM chips into them.
        totalReplacements += shared.restoreElementTextNodes(doc.body, sessionMapping, excluded);
      });

      if (totalReplacements > 0) {
        showToast("Restored personal details in AI replies.");
      } else {
        showToast("No mapped placeholders found in visible replies.");
      }
      return totalReplacements;
    }

    function scanAssistantMessages() {
      if (!Object.keys(sessionMapping || {}).length) return;
      const excluded = getExcludedPromptRoots();

      for (const msgEl of getAssistantElements()) {
        if (!canSafelyAttachInlineChip(msgEl) || failedChipContainers.has(msgEl)) {
          continue;
        }

        const combinedText = shared.extractCombinedTextDeep(msgEl, excluded);
        const found = shared.findKnownPlaceholders(combinedText, sessionMapping);
        const existingRow = chipByElement.get(msgEl);

        if (!found.length) {
          if (existingRow) removeChipFor(msgEl);
          continue;
        }

        const label = `Restore ${found.length} placeholder${found.length === 1 ? "" : "s"}`;
        if (existingRow) {
          if (!doc.body.contains(existingRow)) {
            // Host framework stripped our injected node; circuit-break so we NEVER loop!
            chipByElement.delete(msgEl);
            failedChipContainers.add(msgEl);
            continue;
          }
          const btn = existingRow.querySelector("[data-piishield-chip='true']");
          if (btn && btn.textContent !== label) {
            withInternalDomChange(() => {
              btn.textContent = label;
            });
          }
          continue;
        }

        withInternalDomChange(() => {
          const row = doc.createElement("div");
          row.className = "piishield-ext-chip-row";
          row.setAttribute("data-piishield-ui", "true");

          const chip = doc.createElement("button");
          chip.type = "button";
          chip.className = "piishield-ext-inline-restore";
          chip.setAttribute("data-piishield-chip", "true");
          chip.setAttribute("data-piishield-ui", "true");
          chip.textContent = label;
          chip.addEventListener("click", () => {
            withInternalDomChange(() => {
              shared.restoreElementTextNodes(msgEl, sessionMapping, excluded);
            });
            removeChipFor(msgEl);
            showToast("Restored reply details.");
          });

          row.appendChild(chip);
          msgEl.appendChild(row);
          chipByElement.set(msgEl, row);
        });
      }
    }

    shieldBtn.addEventListener("click", handleShieldClick);
    restoreBtn.addEventListener("click", restoreAllAssistantMessages);
    cancelBtn.addEventListener("click", () => {
      popoverEl.classList.add("piishield-ext-hidden");
      pendingState = null;
    });
    applyBtn.addEventListener("click", async () => {
      if (!pendingState || !pendingState.currentBuilt) return;
      await commitAndInsert(
        pendingState.editorEl,
        pendingState.currentBuilt.redacted,
        pendingState.currentBuilt.mapping
      );
    });

    // Hydrate current session mapping & preferences from background service worker.
    const readyPromise = sendMessage({ type: "PII_SHIELD_GET_SESSION" })
      .then((res) => {
        if (res && res.ok) {
          sessionMapping = res.sessionMapping || {};
          settings = { ...settings, ...(res.settings || {}) };
          updateRestoreDockButton();
          scanAssistantMessages();
        }
      })
      .catch(() => {});

    // Keep sessionMapping & settings synced if the user redacts or clears via the toolbar popup.
    if (storage?.onChanged?.addListener) {
      try {
        storageListener = (changes, areaName) => {
          if (areaName === "session" && changes.pii_shield_session_mapping_v1) {
            sessionMapping = changes.pii_shield_session_mapping_v1.newValue || {};
            updateRestoreDockButton();
            scanAssistantMessages();
          }
          if (areaName === "local" && changes.pii_shield_settings_v1?.newValue) {
            settings = { ...settings, ...changes.pii_shield_settings_v1.newValue };
          }
        };
        storage.onChanged.addListener(storageListener);
      } catch {
        storageListener = null;
      }
    }

    function isOnlyExtensionMutation(mutations) {
      if (!mutations || !mutations.length) return true;
      return mutations.every((m) => {
        const target = m.target;
        if (target && (target === container || container.contains(target))) return true;
        if (
          target &&
          target.nodeType === 1 &&
          typeof target.getAttribute === "function" &&
          target.getAttribute("data-piishield-ui") === "true"
        ) {
          return true;
        }
        const changedNodes = [...(m.addedNodes || []), ...(m.removedNodes || [])];
        if (
          changedNodes.length > 0 &&
          changedNodes.every(
            (n) =>
              n === container ||
              container.contains(n) ||
              (n.nodeType === 1 &&
                typeof n.getAttribute === "function" &&
                n.getAttribute("data-piishield-ui") === "true")
          )
        ) {
          return true;
        }
        return false;
      });
    }

    if (typeof win.MutationObserver === "function") {
      observer = new win.MutationObserver((mutations) => {
        if (contextInvalidated || isInternalDomChange || isOnlyExtensionMutation(mutations)) return;
        if (!isRuntimeValid()) {
          cleanupInvalidatedContext();
          return;
        }
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(scanAssistantMessages, 550);
      });
      observer.observe(doc.body, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ["class", "data-is-streaming"],
      });
    }

    return {
      container,
      readyPromise,
      handleShieldClick,
      restoreAllAssistantMessages,
      scanAssistantMessages,
      getSessionMapping: () => ({ ...sessionMapping }),
      disconnect: cleanupInvalidatedContext,
    };
  }

  root.PiiShieldContent = { initContentScript };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { initContentScript };
  }

  if (
    typeof document !== "undefined" &&
    document.body &&
    !root.__PIISHIELD_DISABLE_AUTO_INIT__
  ) {
    initContentScript();
  }
})(typeof globalThis !== "undefined" ? globalThis : window);
