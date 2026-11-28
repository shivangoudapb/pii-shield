"use strict";

/**
 * Shared pure logic and DOM adapters for the PII Shield Chrome Extension.
 * Exposed on `globalThis.PiiShieldShared` in browsers/service workers and via
 * CommonJS `module.exports` for the Node.js test suite (E12).
 */
(function initShared(root) {
  const DEFAULT_CLOUD_RUN_URL = "https://pii-shield-ql5licjz5a-uc.a.run.app";
  const DEFAULT_MODAL_FALLBACK_URL = "https://bhavihalshivu--pii-shield-web-app.us-east.modal.run";
  const DEFAULT_LOCAL_URL = "http://127.0.0.1:7860";
  const MAX_TEXT_CHARS = 20000;
  const PLACEHOLDER_REGEX = /\[([A-Za-z][A-Za-z_]*_[0-9]+)\]/gi;

  const SITE_CONFIGS = {
    chatgpt: {
      name: "ChatGPT",
      hosts: ["chatgpt.com", "chat.openai.com"],
      editorSelectors: [
        "#prompt-textarea[contenteditable='true']",
        "#prompt-textarea",
        "textarea#prompt-textarea",
        "form div[contenteditable='true']",
        "form textarea",
      ],
      assistantSelectors: [
        "[data-message-author-role='assistant']",
      ],
      userSelectors: [
        "[data-message-author-role='user']",
        "[data-testid^='conversation-turn-'][data-turn='user']",
      ],
    },
    gemini: {
      name: "Gemini",
      hosts: ["gemini.google.com"],
      editorSelectors: [
        "rich-textarea div.ql-editor[contenteditable='true']",
        "div.ql-editor[contenteditable='true']",
        "div[role='textbox'][contenteditable='true']",
      ],
      assistantSelectors: [
        "message-content",
        ".model-response-text",
      ],
      userSelectors: [
        "user-query",
        ".user-query-container",
      ],
    },
    claude: {
      name: "Claude",
      hosts: ["claude.ai"],
      editorSelectors: [
        "fieldset div.ProseMirror[contenteditable='true']",
        "[data-testid='chat-input'][contenteditable='true']",
        "fieldset div[contenteditable='true']",
        "div.ProseMirror[contenteditable='true']",
      ],
      assistantSelectors: [
        "[data-testid='assistant-message']",
        ".font-claude-response",
        ".font-claude-message",
        "[data-testid*='artifact']",
      ],
      userSelectors: [
        "[data-testid='user-message']",
        ".font-user-message",
      ],
    },
  };

  function normaliseEntity(value) {
    return String(value || "").toLowerCase().trim().split(/\s+/).join(" ");
  }

  function detectSiteConfig(hostname) {
    const cleanHost = String(hostname || "").toLowerCase();
    for (const [key, config] of Object.entries(SITE_CONFIGS)) {
      if (config.hosts.some((h) => cleanHost === h || cleanHost.endsWith(`.${h}`))) {
        return { id: key, ...config };
      }
    }
    return null;
  }

  function isHiddenElement(el) {
    if (!el || el.nodeType !== 1) return true;
    if (el.hidden) return true;
    if (typeof el.getAttribute === "function") {
      if (el.getAttribute("aria-hidden") === "true") return true;
      if (el.getAttribute("type") === "hidden") return true;
      const styleAttr = el.getAttribute("style") || "";
      if (/display\s*:\s*none/i.test(styleAttr)) return true;
    }
    if (el.style && el.style.display === "none") return true;
    return false;
  }

  function isInsideCanvasOrArtifact(el) {
    let cur = el;
    while (cur && cur.nodeType === 1) {
      if (cur.id === "prosemirror-editor-container") return true;
      const testId = typeof cur.getAttribute === "function" ? cur.getAttribute("data-testid") || "" : "";
      if (testId.includes("canvas") || testId.includes("artifact")) return true;
      cur = cur.parentElement;
    }
    return false;
  }

  function findComposerElement(doc, hostname) {
    const site = detectSiteConfig(hostname);
    const selectors = site
      ? site.editorSelectors
      : [
          "div.ProseMirror[contenteditable='true']",
          "div[role='textbox'][contenteditable='true']",
          "textarea",
        ];
    for (const selector of selectors) {
      const elements = Array.from(doc.querySelectorAll(selector));
      const visible = elements.find(
        (el) => !el.disabled && !el.readOnly && !isHiddenElement(el) && !isInsideCanvasOrArtifact(el)
      );
      if (visible) return visible;
    }
    return null;
  }

  function getEditorText(element) {
    if (!element) return "";
    const tag = (element.tagName || "").toUpperCase();
    if (tag === "TEXTAREA" || tag === "INPUT") {
      return element.value || "";
    }
    // ProseMirror and Quill represent paragraphs as <p> blocks; skip if nested <pre>/<code> exists.
    const hasCodeBlock = element.querySelector && element.querySelector("pre, code");
    const blocks = !hasCodeBlock && element.querySelectorAll ? element.querySelectorAll("p") : [];
    if (blocks && blocks.length > 0) {
      return Array.from(blocks)
        .map((p) => p.textContent || "")
        .join("\n");
    }
    return (element.innerText !== undefined ? element.innerText : element.textContent) || "";
  }

  function setEditorText(element, newText, docOverride) {
    if (!element) return false;
    const doc = docOverride || element.ownerDocument || (typeof document !== "undefined" ? document : null);
    const tag = (element.tagName || "").toUpperCase();

    if (tag === "TEXTAREA" || tag === "INPUT") {
      const proto =
        tag === "TEXTAREA" && typeof HTMLTextAreaElement !== "undefined"
          ? HTMLTextAreaElement.prototype
          : typeof HTMLInputElement !== "undefined"
            ? HTMLInputElement.prototype
            : null;
      const descriptor = proto ? Object.getOwnPropertyDescriptor(proto, "value") : null;
      if (descriptor && descriptor.set) {
        descriptor.set.call(element, newText);
      } else {
        element.value = newText;
      }
      if (typeof Event !== "undefined") {
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return true;
    }

    if (typeof element.focus === "function") {
      element.focus();
    }

    // Attempt native execCommand first so ProseMirror / Quill state stays synced.
    let usedExecCommand = false;
    if (doc && typeof doc.createRange === "function" && typeof doc.execCommand === "function") {
      try {
        const selection = doc.defaultView ? doc.defaultView.getSelection() : null;
        if (selection) {
          const range = doc.createRange();
          range.selectNodeContents(element);
          selection.removeAllRanges();
          selection.addRange(range);
          usedExecCommand = Boolean(doc.execCommand("insertText", false, newText));
        }
      } catch {
        usedExecCommand = false;
      }
    }

    if (!usedExecCommand || getEditorText(element).trim() !== String(newText).trim()) {
      if (doc && typeof doc.createElement === "function") {
        while (element.firstChild) {
          element.removeChild(element.firstChild);
        }
        const lines = String(newText).split("\n");
        for (const line of lines) {
          const p = doc.createElement("p");
          p.textContent = line;
          element.appendChild(p);
        }
      } else {
        element.textContent = newText;
      }
      if (typeof Event !== "undefined") {
        element.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }
    return true;
  }

  /**
   * Build redacted text and local mapping from spans, skipping disabled indices.
   * Mirrors `redactor.py` entity normalisation (`casefold` + whitespace collapse).
   */
  function buildRedactionFromSpans(text, spans, disabledIndices) {
    const disabled = disabledIndices instanceof Set ? disabledIndices : new Set(disabledIndices || []);
    const sorted = [...(spans || [])].sort((a, b) => a.start - b.start || a.end - b.end);
    const mapping = {};
    const placeholders = new Map();
    const counters = {};
    const parts = [];
    let cursor = 0;
    let activeCount = 0;

    sorted.forEach((span, idx) => {
      if (disabled.has(idx)) return;
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
    return { redacted: parts.join(""), mapping, activeCount, sortedSpans: sorted };
  }

  /**
   * Re-key a turn's placeholders against an existing session mapping so that:
   * 1. Previously seen entities keep their exact same `[LABEL_N]` across turns.
   * 2. Brand-new entities receive the next unused `[LABEL_K]` index instead of
   *    overwriting earlier turns' placeholders.
   */
  function mergeIntoSessionMapping(redactedText, turnMapping, existingSessionMapping) {
    const session = { ...(existingSessionMapping || {}) };
    const existingByLabelAndNorm = new Map();
    const maxIndexByLabel = {};

    for (const [placeholder, value] of Object.entries(session)) {
      const match = /^\[([A-Za-z][A-Za-z_]*)_([0-9]+)\]$/.exec(placeholder.trim());
      if (!match) continue;
      const label = match[1].toUpperCase();
      const index = Number.parseInt(match[2], 10);
      maxIndexByLabel[label] = Math.max(maxIndexByLabel[label] || 0, index);
      existingByLabelAndNorm.set(`${label}\u0000${normaliseEntity(value)}`, placeholder.toUpperCase());
    }

    const turnRewrite = new Map();
    for (const [rawPlaceholder, originalValue] of Object.entries(turnMapping || {})) {
      const upperPlaceholder = rawPlaceholder.toUpperCase();
      const match = /^\[([A-Za-z][A-Za-z_]*)_([0-9]+)\]$/.exec(upperPlaceholder);
      if (!match) continue;
      const label = match[1].toUpperCase();
      const lookupKey = `${label}\u0000${normaliseEntity(originalValue)}`;

      let targetPlaceholder = existingByLabelAndNorm.get(lookupKey);
      if (!targetPlaceholder) {
        if (!session[upperPlaceholder]) {
          targetPlaceholder = upperPlaceholder;
          const idx = Number.parseInt(match[2], 10);
          maxIndexByLabel[label] = Math.max(maxIndexByLabel[label] || 0, idx);
        } else {
          const nextIdx = (maxIndexByLabel[label] || 0) + 1;
          maxIndexByLabel[label] = nextIdx;
          targetPlaceholder = `[${label}_${nextIdx}]`;
        }
        session[targetPlaceholder] = originalValue;
        existingByLabelAndNorm.set(lookupKey, targetPlaceholder);
      }
      turnRewrite.set(upperPlaceholder, targetPlaceholder);
    }

    const rewrittenText = String(redactedText || "").replace(PLACEHOLDER_REGEX, (matched) => {
      return turnRewrite.get(matched.toUpperCase()) || matched;
    });

    return { redacted: rewrittenText, sessionMapping: session };
  }

  function buildKnownTokenRegex(mapping) {
    const bareTokens = [];
    for (const rawKey of Object.keys(mapping || {})) {
      const m = /^\[([A-Za-z][A-Za-z_]*_[0-9]+)\]$/.exec(rawKey.trim());
      if (!m) continue;
      const canonical = m[1].toUpperCase();
      // Match `[PERSON_1]`, `[person_1]`, `[PERSON 1]`, or bare `PERSON_1` if an LLM dropped brackets.
      const escapedSpaceVariant = canonical.replace(/_/g, "[_ ]");
      bareTokens.push(`\\[${escapedSpaceVariant}\\]`);
      bareTokens.push(`(?<![A-Za-z0-9_])${canonical}(?![A-Za-z0-9_])`);
    }
    if (!bareTokens.length) return null;
    return new RegExp(bareTokens.join("|"), "gi");
  }

  function resolveMatchedToken(matchedText, lookup) {
    const normalized = matchedText
      .trim()
      .replace(/^\[|\]$/g, "")
      .replace(/\s+/g, "_")
      .toUpperCase();
    const key = `[${normalized}]`;
    return lookup.has(key) ? lookup.get(key) : null;
  }

  /**
   * Restore known `[LABEL_N]` placeholders case-insensitively (plus LLM-mutated
   * `[LABEL N]` or bracket-stripped `LABEL_N` variants for known session keys),
   * leaving unknown placeholders untouched.
   */
  function restorePlaceholders(text, mapping) {
    const lookup = new Map();
    for (const [key, value] of Object.entries(mapping || {})) {
      lookup.set(key.trim().toUpperCase(), value);
    }
    const tokenRe = buildKnownTokenRegex(mapping);
    if (!tokenRe) return String(text || "");
    return String(text || "").replace(tokenRe, (matched) => {
      const resolved = resolveMatchedToken(matched, lookup);
      return resolved !== null ? resolved : matched;
    });
  }

  function findKnownPlaceholders(text, mapping) {
    const lookup = new Map();
    for (const [key, value] of Object.entries(mapping || {})) {
      lookup.set(key.trim().toUpperCase(), value);
    }
    const tokenRe = buildKnownTokenRegex(mapping);
    if (!tokenRe) return [];
    const found = [];
    for (const match of String(text || "").matchAll(tokenRe)) {
      const normalized = `[${match[0].trim().replace(/^\[|\]$/g, "").replace(/\s+/g, "_").toUpperCase()}]`;
      if (lookup.has(normalized) && !found.includes(normalized)) {
        found.push(normalized);
      }
    }
    return found;
  }

  function deduplicateOutermostElements(elements) {
    const unique = [];
    for (const el of elements || []) {
      if (el && !unique.includes(el)) unique.push(el);
    }
    return unique.filter(
      (el) => !unique.some((other) => other !== el && typeof other.contains === "function" && other.contains(el))
    );
  }

  function isExcludedSubtree(node, excludedRoots) {
    if (!node || !excludedRoots || !excludedRoots.length) return false;
    for (const ex of excludedRoots) {
      if (!ex) continue;
      if (ex === node || (typeof ex.contains === "function" && ex.contains(node))) {
        return true;
      }
    }
    return false;
  }

  function collectTextNodesDeep(rootNode, excludedRoots) {
    const textNodes = [];
    const skippedTags = new Set(["SCRIPT", "STYLE", "NOSCRIPT"]);

    function walk(node) {
      if (!node || isExcludedSubtree(node, excludedRoots)) return;
      if (node.nodeType === 3) {
        textNodes.push(node);
        return;
      }
      if (node.nodeType === 1) {
        const tag = (node.tagName || "").toUpperCase();
        if (skippedTags.has(tag)) return;
        if (
          typeof node.getAttribute === "function" &&
          (node.getAttribute("data-piishield-chip") === "true" ||
            node.getAttribute("data-piishield-ui") === "true")
        ) {
          return;
        }
        // Traverse open Shadow DOM if present (e.g. Gemini web components).
        if (node.shadowRoot) {
          walk(node.shadowRoot);
        }
        // Traverse accessible same-origin iframes (e.g. Canvas / Artifact preview frames).
        if (tag === "IFRAME") {
          try {
            if (node.contentDocument && node.contentDocument.body) {
              walk(node.contentDocument.body);
            }
          } catch {
            // Cross-origin iframe; ignore safely.
          }
        }
      }
      const children = node.childNodes || [];
      for (let i = 0; i < children.length; i += 1) {
        walk(children[i]);
      }
    }

    walk(rootNode);
    return textNodes;
  }

  function collectFormControlsDeep(rootNode, excludedRoots) {
    const controls = [];
    function walk(node) {
      if (!node || isExcludedSubtree(node, excludedRoots)) return;
      if (node.nodeType === 1) {
        const tag = (node.tagName || "").toUpperCase();
        if (
          !isHiddenElement(node) &&
          (tag === "TEXTAREA" || (tag === "INPUT" && (!node.type || node.type === "text")))
        ) {
          controls.push(node);
        }
        if (node.shadowRoot) walk(node.shadowRoot);
        if (tag === "IFRAME") {
          try {
            if (node.contentDocument && node.contentDocument.body) {
              walk(node.contentDocument.body);
            }
          } catch {
            // Cross-origin iframe; ignore safely.
          }
        }
      }
      const children = node.childNodes || [];
      for (let i = 0; i < children.length; i += 1) {
        walk(children[i]);
      }
    }
    walk(rootNode);
    return controls;
  }

  /**
   * Restore known `[LABEL_N]` placeholders inside `container`, including:
   * - Single text nodes (`<p>Hello [PERSON_1]</p>`)
   * - Split syntax-highlighted spans inside `<pre><code>` or CodeMirror boxes
   *   (`<span>[</span><span>PERSON_1</span><span>]</span>`)
   * - Secondary `<textarea>` / `<input>` draft boxes inside the container
   * - Open Shadow DOMs and accessible same-origin iframes
   */
  function restoreElementTextNodes(container, mapping, excludedRoots = []) {
    if (!container || !mapping || !Object.keys(mapping).length) return 0;

    const lookup = new Map();
    for (const [key, value] of Object.entries(mapping)) {
      lookup.set(key.toUpperCase(), value);
    }

    let replacements = 0;

    // 1. Restore any non-excluded <textarea>/<input> draft boxes inside container.
    for (const ctrl of collectFormControlsDeep(container, excludedRoots)) {
      const beforeVal = ctrl.value || "";
      if (!findKnownPlaceholders(beforeVal, mapping).length) continue;
      const afterVal = restorePlaceholders(beforeVal, mapping);
      if (afterVal !== beforeVal) {
        setEditorText(ctrl, afterVal);
        replacements += 1;
      }
    }

    // 2. Restore DOM text nodes, supporting tokens split across adjacent inline spans.
    const textNodes = collectTextNodesDeep(container, excludedRoots);
    if (!textNodes.length) return replacements;

    const blockTags = new Set([
      "P", "DIV", "PRE", "LI", "UL", "OL", "TABLE", "TR", "TD", "TH",
      "BLOCKQUOTE", "SECTION", "ARTICLE", "HEADER", "FOOTER", "H1", "H2", "H3", "H4", "H5", "H6",
    ]);
    function nearestBlock(node) {
      let cur = node.parentNode;
      while (cur && cur !== container) {
        if (cur.nodeType === 1 && blockTags.has((cur.tagName || "").toUpperCase())) {
          return cur;
        }
        cur = cur.parentNode;
      }
      return container;
    }

    const segments = [];
    let fullText = "";
    let prevBlock = null;
    for (const node of textNodes) {
      const block = nearestBlock(node);
      if (prevBlock !== null && block !== prevBlock) {
        fullText += "\n";
      }
      prevBlock = block;
      const val = node.nodeValue || "";
      const start = fullText.length;
      fullText += val;
      segments.push({ node, start, end: fullText.length });
    }

    const tokenRe = buildKnownTokenRegex(mapping);
    if (!tokenRe) return replacements;

    const matches = [];
    for (const match of fullText.matchAll(tokenRe)) {
      const resolved = resolveMatchedToken(match[0], lookup);
      if (resolved === null) continue;
      matches.push({
        start: match.index,
        end: match.index + match[0].length,
        replacement: resolved,
      });
    }

    if (!matches.length) return replacements;

    // Apply from right to left so earlier character offsets remain valid.
    for (let mIdx = matches.length - 1; mIdx >= 0; mIdx -= 1) {
      const { start, end, replacement } = matches[mIdx];
      let startSegIdx = -1;
      let endSegIdx = -1;

      for (let i = 0; i < segments.length; i += 1) {
        const seg = segments[i];
        if (startSegIdx === -1 && start >= seg.start && start < seg.end) {
          startSegIdx = i;
        }
        if (end > seg.start && end <= seg.end) {
          endSegIdx = i;
          break;
        }
      }
      if (startSegIdx === -1 || endSegIdx === -1) continue;

      if (startSegIdx === endSegIdx) {
        const seg = segments[startSegIdx];
        const current = seg.node.nodeValue || "";
        const localStart = start - seg.start;
        const localEnd = end - seg.start;
        seg.node.nodeValue =
          current.slice(0, localStart) + replacement + current.slice(localEnd);
      } else {
        const firstSeg = segments[startSegIdx];
        const lastSeg = segments[endSegIdx];
        const firstVal = firstSeg.node.nodeValue || "";
        const lastVal = lastSeg.node.nodeValue || "";
        firstSeg.node.nodeValue = firstVal.slice(0, start - firstSeg.start) + replacement;
        for (let mid = startSegIdx + 1; mid < endSegIdx; mid += 1) {
          segments[mid].node.nodeValue = "";
        }
        lastSeg.node.nodeValue = lastVal.slice(end - lastSeg.start);
      }
      replacements += 1;
    }

    return replacements;
  }

  function extractCombinedTextDeep(container, excludedRoots = []) {
    if (!container) return "";
    const parts = [];
    for (const node of collectTextNodesDeep(container, excludedRoots)) {
      if (node.nodeValue) parts.push(node.nodeValue);
    }
    for (const ctrl of collectFormControlsDeep(container, excludedRoots)) {
      if (ctrl.value) parts.push(ctrl.value);
    }
    return parts.join("");
  }

  const exported = {
    DEFAULT_CLOUD_RUN_URL,
    DEFAULT_MODAL_FALLBACK_URL,
    DEFAULT_LOCAL_URL,
    MAX_TEXT_CHARS,
    SITE_CONFIGS,
    normaliseEntity,
    detectSiteConfig,
    findComposerElement,
    getEditorText,
    setEditorText,
    buildRedactionFromSpans,
    mergeIntoSessionMapping,
    restorePlaceholders,
    findKnownPlaceholders,
    deduplicateOutermostElements,
    extractCombinedTextDeep,
    restoreElementTextNodes,
  };

  root.PiiShieldShared = exported;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = exported;
  }
})(typeof globalThis !== "undefined" ? globalThis : window);
