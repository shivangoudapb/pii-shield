"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const EXT_ROOT = path.resolve(__dirname, "..");
globalThis.__PIISHIELD_DISABLE_AUTO_INIT__ = true;

const shared = require("../shared.js");
const { initContentScript } = require("../content.js");

/**
 * Minimal, deterministic DOM implementation for testing content script injection,
 * ProseMirror/Quill editor manipulation, TreeWalker text-node restoration, and events.
 */
class MiniNode {
  constructor(nodeType, ownerDocument) {
    this.nodeType = nodeType;
    this.ownerDocument = ownerDocument;
    this.parentNode = null;
    this.childNodes = [];
  }

  get parentElement() {
    return this.parentNode && this.parentNode.nodeType === 1 ? this.parentNode : null;
  }

  get firstChild() {
    return this.childNodes[0] || null;
  }

  appendChild(child) {
    if (child.parentNode) {
      child.parentNode.removeChild(child);
    }
    child.parentNode = this;
    this.childNodes.push(child);
    return child;
  }

  append(...items) {
    for (const item of items) {
      if (typeof item === "string") {
        this.appendChild(this.ownerDocument.createTextNode(item));
      } else if (item) {
        this.appendChild(item);
      }
    }
  }

  removeChild(child) {
    const idx = this.childNodes.indexOf(child);
    if (idx !== -1) {
      this.childNodes.splice(idx, 1);
      child.parentNode = null;
    }
    return child;
  }

  replaceChildren(...items) {
    while (this.firstChild) {
      this.removeChild(this.firstChild);
    }
    this.append(...items);
  }

  remove() {
    if (this.parentNode) {
      this.parentNode.removeChild(this);
    }
  }

  contains(target) {
    let cur = target;
    while (cur) {
      if (cur === this) return true;
      cur = cur.parentNode;
    }
    return false;
  }
}

class MiniText extends MiniNode {
  constructor(value, ownerDocument) {
    super(3, ownerDocument);
    this.nodeValue = String(value);
  }

  get textContent() {
    return this.nodeValue;
  }

  set textContent(val) {
    this.nodeValue = String(val);
  }
}

class MiniClassList {
  constructor(el) {
    this._el = el;
  }

  _set() {
    return new Set((this._el.className || "").split(/\s+/).filter(Boolean));
  }

  _write(set) {
    this._el.className = Array.from(set).join(" ");
  }

  add(...tokens) {
    const s = this._set();
    for (const t of tokens) s.add(t);
    this._write(s);
  }

  remove(...tokens) {
    const s = this._set();
    for (const t of tokens) s.delete(t);
    this._write(s);
  }

  toggle(token, force) {
    const s = this._set();
    const shouldHave = force !== undefined ? Boolean(force) : !s.has(token);
    if (shouldHave) s.add(token);
    else s.delete(token);
    this._write(s);
    return shouldHave;
  }

  contains(token) {
    return this._set().has(token);
  }
}

function matchesSingleSelector(el, selector) {
  if (!el || el.nodeType !== 1) return false;
  let rest = selector.trim();

  const attrRegex = /\[([A-Za-z0-9_-]+)(?:=(?:'([^']*)'|"([^"]*)"|([^'"\]]+)))?\]/g;
  for (const m of rest.matchAll(attrRegex)) {
    const attrVal = el.getAttribute(m[1]);
    const expectedVal = m[2] ?? m[3] ?? m[4];
    if (expectedVal !== undefined) {
      if (attrVal !== expectedVal) return false;
    } else if (attrVal === null) {
      return false;
    }
  }
  rest = rest.replace(attrRegex, "");

  const idMatch = /#([A-Za-z0-9_-]+)/.exec(rest);
  if (idMatch && el.id !== idMatch[1]) return false;
  rest = rest.replace(/#[A-Za-z0-9_-]+/g, "");

  const classes = Array.from(rest.matchAll(/\.([A-Za-z0-9_-]+)/g)).map((m) => m[1]);
  for (const cls of classes) {
    if (!el.classList.contains(cls)) return false;
  }
  rest = rest.replace(/\.[A-Za-z0-9_-]+/g, "").trim();

  if (rest && el.tagName.toLowerCase() !== rest.toLowerCase()) return false;
  return true;
}

function matchesSelectorChain(el, fullSelector) {
  const parts = fullSelector.trim().split(/\s+/);
  let current = el;
  for (let i = parts.length - 1; i >= 0; i -= 1) {
    if (!current) return false;
    if (i === parts.length - 1) {
      if (!matchesSingleSelector(current, parts[i])) return false;
      current = current.parentElement;
    } else {
      while (current && !matchesSingleSelector(current, parts[i])) {
        current = current.parentElement;
      }
      if (!current) return false;
      current = current.parentElement;
    }
  }
  return true;
}

class MiniElement extends MiniNode {
  constructor(tagName, ownerDocument) {
    super(1, ownerDocument);
    this.tagName = String(tagName).toUpperCase();
    this.id = "";
    this.className = "";
    this.value = "";
    this.disabled = false;
    this.readOnly = false;
    this.tabIndex = -1;
    this.title = "";
    this._attrs = new Map();
    this._listeners = new Map();
    this.classList = new MiniClassList(this);
  }

  setAttribute(name, val) {
    const str = String(val);
    this._attrs.set(name, str);
    if (name === "id") this.id = str;
    if (name === "class") this.className = str;
    if (name === "readonly") this.readOnly = true;
  }

  getAttribute(name) {
    if (name === "id" && this.id) return this.id;
    if (name === "class" && this.className) return this.className;
    return this._attrs.has(name) ? this._attrs.get(name) : null;
  }

  addEventListener(type, fn) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(fn);
  }

  dispatchEvent(ev) {
    const handlers = this._listeners.get(ev.type) || [];
    for (const fn of handlers) fn(ev);
    return true;
  }

  click() {
    this.dispatchEvent({ type: "click", preventDefault() {} });
  }

  focus() {}

  get textContent() {
    return this.childNodes.map((c) => c.textContent).join("");
  }

  set textContent(val) {
    while (this.firstChild) this.removeChild(this.firstChild);
    if (val !== "" && val !== null && val !== undefined) {
      this.appendChild(this.ownerDocument.createTextNode(String(val)));
    }
  }

  set innerHTML(html) {
    while (this.firstChild) this.removeChild(this.firstChild);
    const parsed = parseSimpleHtml(String(html), this.ownerDocument);
    for (const node of parsed) this.appendChild(node);
  }

  querySelectorAll(selectorGroup) {
    const selectors = selectorGroup.split(",").map((s) => s.trim()).filter(Boolean);
    const results = [];
    const visit = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === 1) {
          if (selectors.some((sel) => matchesSelectorChain(child, sel))) {
            results.push(child);
          }
          visit(child);
        }
      }
    };
    visit(this);
    return results;
  }

  querySelector(selectorGroup) {
    return this.querySelectorAll(selectorGroup)[0] || null;
  }
}

function parseSimpleHtml(html, doc) {
  const tokens = html.match(/<\/?[a-zA-Z0-9-]+(?:\s+[^>]*)?>|[^<]+/g) || [];
  const rootHolder = new MiniElement("div", doc);
  const stack = [rootHolder];

  for (const token of tokens) {
    if (token.startsWith("</")) {
      if (stack.length > 1) stack.pop();
    } else if (token.startsWith("<")) {
      const tagMatch = /^<([a-zA-Z0-9-]+)([\s\S]*?)>$/.exec(token);
      if (!tagMatch) continue;
      const el = doc.createElement(tagMatch[1]);
      const attrPart = tagMatch[2] || "";
      const attrRe = /([a-zA-Z0-9_-]+)(?:="([^"]*)")?/g;
      for (const m of attrPart.matchAll(attrRe)) {
        el.setAttribute(m[1], m[2] ?? "");
      }
      stack[stack.length - 1].appendChild(el);
      if (!["input", "br", "hr", "img"].includes(tagMatch[1].toLowerCase())) {
        stack.push(el);
      }
    } else if (token.trim() || stack.length > 1) {
      stack[stack.length - 1].appendChild(doc.createTextNode(token));
    }
  }
  return [...rootHolder.childNodes];
}

class MiniDocument {
  constructor() {
    this.body = new MiniElement("body", this);
    this.defaultView = null;
  }

  createElement(tag) {
    return new MiniElement(tag, this);
  }

  createTextNode(text) {
    return new MiniText(text, this);
  }

  querySelectorAll(sel) {
    return this.body.querySelectorAll(sel);
  }

  querySelector(sel) {
    return this.body.querySelector(sel);
  }

  createTreeWalker(rootNode) {
    const textNodes = [];
    const collect = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === 3) textNodes.push(child);
        else if (child.nodeType === 1) collect(child);
      }
    };
    collect(rootNode);
    let idx = -1;
    return {
      nextNode() {
        idx += 1;
        return textNodes[idx] || null;
      },
    };
  }
}

function createBackgroundHarness(fetchImpl) {
  const localStore = {};
  const sessionStore = {};
  let messageListener = null;

  const chromeMock = {
    storage: {
      local: {
        async get(key) {
          return { [key]: localStore[key] };
        },
        async set(obj) {
          Object.assign(localStore, obj);
        },
      },
      session: {
        async get(key) {
          return { [key]: sessionStore[key] };
        },
        async set(obj) {
          Object.assign(sessionStore, obj);
        },
      },
    },
    runtime: {
      lastError: null,
      onMessage: {
        addListener(fn) {
          messageListener = fn;
        },
      },
      sendMessage(msg, cb) {
        messageListener(msg, {}, cb);
      },
    },
  };

  const sandbox = {
    chrome: chromeMock,
    fetch: fetchImpl,
    URL,
    Error,
    Object,
    Promise,
    Number,
    String,
    Boolean,
    Math,
    Map,
    Set,
    RegExp,
    Array,
    importScripts(relPath) {
      const code = fs.readFileSync(path.join(EXT_ROOT, relPath), "utf8");
      vm.runInContext(code, sandbox);
    },
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(EXT_ROOT, "background.js"), "utf8"), sandbox);

  const send = (msg) =>
    new Promise((resolve) => {
      chromeMock.runtime.sendMessage(msg, resolve);
    });

  return { chromeMock, send, localStore, sessionStore };
}

// ---------------------------------------------------------------------------
// 1. Manifest & Asset Integrity
// ---------------------------------------------------------------------------
test("manifest.json is valid Manifest V3 and all referenced files exist", () => {
  const manifestPath = path.join(EXT_ROOT, "manifest.json");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

  assert.equal(manifest.manifest_version, 3);
  assert.ok(manifest.permissions.includes("storage"));
  assert.ok(manifest.host_permissions.includes("https://*.a.run.app/*"));
  assert.ok(manifest.host_permissions.includes("https://*.modal.run/*"));

  const filesToCheck = [
    manifest.background.service_worker,
    manifest.action.default_popup,
    ...Object.values(manifest.icons),
    ...manifest.content_scripts.flatMap((cs) => [...cs.js, ...cs.css]),
  ];
  for (const rel of filesToCheck) {
    assert.ok(fs.existsSync(path.join(EXT_ROOT, rel)), `Missing extension file: ${rel}`);
  }
});

// ---------------------------------------------------------------------------
// 2. Selective Redaction & Multi-Turn Collision-Free Session Mapping
// ---------------------------------------------------------------------------
test("buildRedactionFromSpans and restorePlaceholders handle selective toggles and underscore labels", () => {
  const text = "Name: Ananya Rao, Voter ID DLQ4019283, follow up with ananya rao";
  const spans = [
    { start: 6, end: 16, label: "PERSON", text: "Ananya Rao", source: "rules", score: 1.0 },
    { start: 27, end: 37, label: "VOTER_ID", text: "DLQ4019283", source: "regex", score: 1.0 },
    { start: 54, end: 64, label: "PERSON", text: "ananya rao", source: "ner", score: 0.92 },
  ];

  const allActive = shared.buildRedactionFromSpans(text, spans, new Set());
  assert.equal(
    allActive.redacted,
    "Name: [PERSON_1], Voter ID [VOTER_ID_1], follow up with [PERSON_1]"
  );
  assert.equal(shared.restorePlaceholders(allActive.redacted, allActive.mapping), "Name: Ananya Rao, Voter ID DLQ4019283, follow up with Ananya Rao");

  // Disable Voter ID (index 1) -> kept unredacted while PERSON remains redacted
  const toggled = shared.buildRedactionFromSpans(text, spans, new Set([1]));
  assert.equal(
    toggled.redacted,
    "Name: [PERSON_1], Voter ID DLQ4019283, follow up with [PERSON_1]"
  );
  assert.equal(toggled.activeCount, 2);
});

test("mergeIntoSessionMapping preserves existing placeholders and re-indexes new people across turns", () => {
  const turn1 = shared.mergeIntoSessionMapping(
    "Hi, I am [PERSON_1].",
    { "[PERSON_1]": "Ananya Rao" },
    {}
  );
  assert.equal(turn1.redacted, "Hi, I am [PERSON_1].");
  assert.deepEqual(turn1.sessionMapping, { "[PERSON_1]": "Ananya Rao" });

  // Turn 2 introduces Rohan Verma as [PERSON_1] from stateless API + repeats Ananya Rao as [PERSON_2]
  const turn2 = shared.mergeIntoSessionMapping(
    "Connect [PERSON_1] with [PERSON_2].",
    { "[PERSON_1]": "Rohan Verma", "[PERSON_2]": "ananya   rao" },
    turn1.sessionMapping
  );
  assert.equal(turn2.redacted, "Connect [PERSON_2] with [PERSON_1].");
  assert.deepEqual(turn2.sessionMapping, {
    "[PERSON_1]": "Ananya Rao",
    "[PERSON_2]": "Rohan Verma",
  });
});

// ---------------------------------------------------------------------------
// 3. Service Worker Persistence & Automatic Cloud Run -> Modal Failover
// ---------------------------------------------------------------------------
test("background worker persists session mapping and fails over from Cloud Run to Modal on 503", async () => {
  const calledUrls = [];
  const harness = createBackgroundHarness(async (url) => {
    calledUrls.push(url);
    if (url.startsWith(shared.DEFAULT_CLOUD_RUN_URL)) {
      return { ok: false, status: 503, headers: { get: () => null }, json: async () => ({}) };
    }
    return {
      ok: true,
      status: 200,
      headers: { get: () => null },
      json: async () => ({
        redacted: "Call [PHONE_1]",
        spans: [{ start: 5, end: 15, label: "PHONE", text: "9845012345", source: "regex", score: 1.0 }],
        mapping: { "[PHONE_1]": "9845012345" },
      }),
    };
  });

  const detectRes = await harness.send({ type: "PII_SHIELD_DETECT", text: "Call 9845012345" });
  assert.equal(detectRes.ok, true);
  assert.equal(detectRes.endpointUsed, shared.DEFAULT_MODAL_FALLBACK_URL);
  assert.equal(calledUrls.length, 2);

  const commitRes = await harness.send({
    type: "PII_SHIELD_COMMIT_REDACTION",
    redacted: detectRes.payload.redacted,
    mapping: detectRes.payload.mapping,
  });
  assert.equal(commitRes.ok, true);
  assert.deepEqual({ ...commitRes.sessionMapping }, { "[PHONE_1]": "9845012345" });

  const restored = await harness.send({
    type: "PII_SHIELD_RESTORE_TEXT",
    text: "Sure, dialing [phone_1] now!",
  });
  assert.equal(restored.restored, "Sure, dialing 9845012345 now!");
});

test("background worker does not fail over on HTTP 413 or 429 client errors", async () => {
  const calledUrls = [];
  const harness = createBackgroundHarness(async (url) => {
    calledUrls.push(url);
    return {
      ok: false,
      status: 429,
      headers: { get: (h) => (h === "Retry-After" ? "12" : null) },
      json: async () => ({ detail: "Rate limit exceeded." }),
    };
  });

  const res = await harness.send({ type: "PII_SHIELD_DETECT", text: "Name: Ananya Rao" });
  assert.equal(res.ok, false);
  assert.match(res.error, /12s/);
  assert.equal(calledUrls.length, 1);
});

// ---------------------------------------------------------------------------
// 4. Per-Site Content Script Injection & DOM Manipulation (ChatGPT, Gemini, Claude)
// ---------------------------------------------------------------------------
test("ChatGPT content script shields ProseMirror prompt with selective toggle and restores reply nodes", async () => {
  const doc = new MiniDocument();
  const form = doc.createElement("form");
  const editor = doc.createElement("div");
  editor.id = "prompt-textarea";
  editor.setAttribute("contenteditable", "true");
  const p = doc.createElement("p");
  p.textContent = "Name: Ananya Rao, PAN ABCDE1234F";
  editor.appendChild(p);
  form.appendChild(editor);
  doc.body.appendChild(form);

  const harness = createBackgroundHarness(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({
      redacted: "Name: [PERSON_1], PAN [PAN_1]",
      spans: [
        { start: 6, end: 16, label: "PERSON", text: "Ananya Rao", source: "rules", score: 1.0 },
        { start: 22, end: 32, label: "PAN", text: "ABCDE1234F", source: "regex", score: 1.0 },
      ],
      mapping: { "[PERSON_1]": "Ananya Rao", "[PAN_1]": "ABCDE1234F" },
    }),
  }));

  const controller = initContentScript({
    window: {},
    document: doc,
    shared,
    runtime: harness.chromeMock.runtime,
    hostname: "chatgpt.com",
  });
  await controller.readyPromise;

  // Click "Shield Prompt" -> opens review popover
  await controller.handleShieldClick();
  const popover = doc.querySelector(".piishield-ext-popover");
  assert.equal(popover.classList.contains("piishield-ext-hidden"), false);

  // Toggle first span (Ananya Rao) OFF -> keeps name unredacted, redacts PAN only
  const marks = popover.querySelectorAll("mark");
  assert.equal(marks.length, 2);
  marks[0].click();

  const applyBtn = doc.querySelector("#piishield-ext-apply");
  applyBtn.click();
  await new Promise((r) => setTimeout(r, 20));

  assert.equal(shared.getEditorText(editor), "Name: Ananya Rao, PAN [PAN_1]");

  // Simulate ChatGPT streaming an assistant reply inside `<article data-testid="conversation-turn-2" data-turn="assistant">`
  const article = doc.createElement("article");
  article.setAttribute("data-testid", "conversation-turn-2");
  article.setAttribute("data-turn", "assistant");
  const agentTurn = doc.createElement("div");
  agentTurn.className = "agent-turn";
  const assistantMsg = doc.createElement("div");
  assistantMsg.setAttribute("data-message-author-role", "assistant");
  const bold = doc.createElement("strong");
  bold.textContent = "[PAN_1]";
  assistantMsg.append("Verified PAN ", bold, " successfully.");
  // Action toolbar sibling outside `assistantMsg` (e.g. feedback textarea) must NOT block `assistantMsg` chip!
  const toolbarFeedback = doc.createElement("textarea");
  toolbarFeedback.setAttribute("style", "display: none");
  agentTurn.append(assistantMsg, toolbarFeedback);
  article.appendChild(agentTurn);
  doc.body.appendChild(article);

  controller.scanAssistantMessages();
  const inlineChip = article.querySelector("[data-piishield-chip='true']");
  assert.ok(inlineChip, "Expected inline Restore chip on ChatGPT assistant message");
  assert.equal(inlineChip.parentElement.parentElement, assistantMsg);
  inlineChip.click();

  assert.equal(assistantMsg.textContent, "Verified PAN ABCDE1234F successfully.");
  assert.equal(bold.textContent, "ABCDE1234F");
});

test("Gemini content script shields Quill editor and restores model-response message-content", async () => {
  const doc = new MiniDocument();
  const richTextarea = doc.createElement("rich-textarea");
  const quill = doc.createElement("div");
  quill.className = "ql-editor";
  quill.setAttribute("contenteditable", "true");
  const p = doc.createElement("p");
  p.textContent = "Send ₹500 to rohan@ybl";
  quill.appendChild(p);
  richTextarea.appendChild(quill);
  doc.body.appendChild(richTextarea);

  const harness = createBackgroundHarness(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({
      redacted: "Send ₹500 to [UPI_1]",
      spans: [{ start: 13, end: 22, label: "UPI", text: "rohan@ybl", source: "regex", score: 1.0 }],
      mapping: { "[UPI_1]": "rohan@ybl" },
    }),
  }));

  const controller = initContentScript({
    window: {},
    document: doc,
    shared,
    runtime: harness.chromeMock.runtime,
    hostname: "gemini.google.com",
  });
  await controller.readyPromise;

  await controller.handleShieldClick();
  doc.querySelector("#piishield-ext-apply").click();
  await new Promise((r) => setTimeout(r, 20));

  assert.equal(shared.getEditorText(quill), "Send ₹500 to [UPI_1]");

  const wrapper = doc.createElement("div");
  const modelResponse = doc.createElement("model-response");
  const msgContent = doc.createElement("message-content");
  msgContent.className = "model-response-text";
  const innerMarkdown = doc.createElement("div");
  innerMarkdown.className = "markdown";
  innerMarkdown.textContent = "Payment queued for [UPI_1].";
  msgContent.appendChild(innerMarkdown);
  modelResponse.appendChild(msgContent);
  wrapper.appendChild(modelResponse);
  doc.body.appendChild(wrapper);

  // Nested Gemini containers (`model-response` > `message-content.model-response-text` > `.markdown`)
  // must produce strictly ONE inline Restore button inside `message-content` (not on outer `model-response`).
  controller.scanAssistantMessages();
  const chips = wrapper.querySelectorAll("[data-piishield-chip='true']");
  assert.equal(chips.length, 1);
  assert.equal(chips[0].parentElement.className, "piishield-ext-chip-row");
  assert.equal(chips[0].parentElement.parentElement, msgContent);

  const replaced = await controller.restoreAllAssistantMessages();
  assert.equal(replaced, 1);
  assert.equal(innerMarkdown.textContent, "Payment queued for rohan@ybl.");
});

test("Claude content script supports 1-click instant replacement and restores .font-claude-message", async () => {
  const doc = new MiniDocument();
  const claudeEditor = doc.createElement("div");
  claudeEditor.className = "ProseMirror";
  claudeEditor.setAttribute("contenteditable", "true");
  const p = doc.createElement("p");
  p.textContent = "Passport J8364921";
  claudeEditor.appendChild(p);
  doc.body.appendChild(claudeEditor);

  const harness = createBackgroundHarness(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({
      redacted: "Passport [PASSPORT_1]",
      spans: [{ start: 9, end: 17, label: "PASSPORT", text: "J8364921", source: "regex", score: 1.0 }],
      mapping: { "[PASSPORT_1]": "J8364921" },
    }),
  }));
  await harness.send({
    type: "PII_SHIELD_SAVE_SETTINGS",
    settings: { reviewBeforeReplace: false },
  });

  const controller = initContentScript({
    window: {},
    document: doc,
    shared,
    runtime: harness.chromeMock.runtime,
    hostname: "claude.ai",
  });
  await controller.readyPromise;

  await controller.handleShieldClick();
  assert.equal(shared.getEditorText(claudeEditor), "Passport [PASSPORT_1]");

  const replyHolder = doc.createElement("div");
  const claudeMsg = doc.createElement("div");
  claudeMsg.className = "font-claude-message";
  claudeMsg.textContent = "Checked passport [PASSPORT_1].";
  replyHolder.appendChild(claudeMsg);
  doc.body.appendChild(replyHolder);

  await controller.restoreAllAssistantMessages();
  assert.equal(claudeMsg.textContent, "Checked passport J8364921.");
});

test("ChatGPT restores split syntax-highlighted code boxes, Canvas/textarea boxes, and unknown containers", async () => {
  const doc = new MiniDocument();
  const form = doc.createElement("form");
  const composer = doc.createElement("div");
  composer.id = "prompt-textarea";
  composer.setAttribute("contenteditable", "true");
  composer.textContent = "Keep [PERSON_1] untouched inside prompt input";
  form.appendChild(composer);
  doc.body.appendChild(form);

  // User bubble should ALSO stay untouched when restoring AI replies
  const userTurn = doc.createElement("div");
  userTurn.setAttribute("data-message-author-role", "user");
  userTurn.textContent = "My name is [PERSON_1]";
  doc.body.appendChild(userTurn);

  // 1. ChatGPT syntax-highlighted code/copy box splitting `[PERSON_1]` across 3 <span>s
  const preBox = doc.createElement("pre");
  const codeEl = doc.createElement("code");
  const sOpen = doc.createElement("span");
  sOpen.textContent = "[";
  const sBody = doc.createElement("span");
  sBody.textContent = "PERSON";
  const sClose = doc.createElement("span");
  sClose.textContent = "_1]";
  codeEl.append("Hello, I am ", sOpen, sBody, sClose, " and PAN is PAN_1.");
  preBox.appendChild(codeEl);
  doc.body.appendChild(preBox);

  // 2. Unmatched custom draft box / textarea outside standard assistant selector
  const customCard = doc.createElement("section");
  const draftArea = doc.createElement("textarea");
  draftArea.value = "Draft bio for [PERSON 1] (PAN [PAN_1]).";
  customCard.appendChild(draftArea);
  doc.body.appendChild(customCard);

  const harness = createBackgroundHarness(async () => ({ ok: true, status: 200, headers: { get: () => null }, json: async () => ({}) }));
  await harness.send({
    type: "PII_SHIELD_COMMIT_REDACTION",
    redacted: "[PERSON_1] [PAN_1]",
    mapping: { "[PERSON_1]": "Ananya Rao", "[PAN_1]": "ABCDE1234F" },
  });

  const controller = initContentScript({
    window: {},
    document: doc,
    shared,
    runtime: harness.chromeMock.runtime,
    hostname: "chatgpt.com",
  });
  await controller.readyPromise;

  const count = await controller.restoreAllAssistantMessages();
  assert.equal(count, 3);
  assert.equal(codeEl.textContent, "Hello, I am Ananya Rao and PAN is ABCDE1234F.");
  assert.equal(draftArea.value, "Draft bio for Ananya Rao (PAN ABCDE1234F).");

  // Composer and user message bubble were safely excluded!
  assert.equal(composer.textContent, "Keep [PERSON_1] untouched inside prompt input");
  assert.equal(userTurn.textContent, "My name is [PERSON_1]");
});

test("ChatGPT Canvas ProseMirror never gets inline Restore button injected (prevents infinite typing loop) and restores cleanly via dock", async () => {
  const doc = new MiniDocument();
  const form = doc.createElement("form");
  const composer = doc.createElement("div");
  composer.id = "prompt-textarea";
  composer.setAttribute("contenteditable", "true");
  composer.textContent = "Write a cover letter for [PERSON_1]";
  // Hidden fallback textarea inside composer <form> must also stay untouched
  const hiddenTextarea = doc.createElement("textarea");
  hiddenTextarea.setAttribute("style", "display: none");
  hiddenTextarea.value = "Write a cover letter for [PERSON_1]";
  form.append(composer, hiddenTextarea);
  doc.body.appendChild(form);

  // Simulate ChatGPT Canvas (`div.ProseMirror[contenteditable="true"]`) inside an assistant turn
  const assistantTurn = doc.createElement("div");
  assistantTurn.setAttribute("data-message-author-role", "assistant");
  const canvasHost = doc.createElement("div");
  canvasHost.id = "prosemirror-editor-container";
  const canvasProseMirror = doc.createElement("div");
  canvasProseMirror.className = "ProseMirror";
  canvasProseMirror.setAttribute("contenteditable", "true");
  const p = doc.createElement("p");
  p.textContent = "Dear Team, I am [PERSON_1] and my PAN is [PAN_1].";
  canvasProseMirror.appendChild(p);
  canvasHost.appendChild(canvasProseMirror);
  assistantTurn.appendChild(canvasHost);
  doc.body.appendChild(assistantTurn);

  const harness = createBackgroundHarness(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({}),
  }));
  await harness.send({
    type: "PII_SHIELD_COMMIT_REDACTION",
    redacted: "[PERSON_1] [PAN_1]",
    mapping: { "[PERSON_1]": "Ananya Rao", "[PAN_1]": "ABCDE1234F" },
  });

  const controller = initContentScript({
    window: {},
    document: doc,
    shared,
    runtime: harness.chromeMock.runtime,
    hostname: "chatgpt.com",
  });
  await controller.readyPromise;

  // Scan multiple times: ZERO inline chips may ever be injected into or around ProseMirror Canvas!
  for (let i = 0; i < 5; i += 1) {
    controller.scanAssistantMessages();
  }
  assert.equal(assistantTurn.querySelectorAll("[data-piishield-chip='true']").length, 0);
  assert.equal(
    canvasProseMirror.textContent.includes("Restore 2 placeholders"),
    false,
    "Canvas ProseMirror must never have button text injected"
  );

  // Clicking bottom-right dock Restore button restores Canvas text cleanly without touching composer
  const restoreDockBtn = doc.querySelector("#piishield-ext-restore-btn");
  assert.equal(restoreDockBtn.classList.contains("piishield-ext-hidden"), false);
  const replaced = await controller.restoreAllAssistantMessages();
  assert.equal(replaced, 2);
  assert.equal(canvasProseMirror.textContent, "Dear Team, I am Ananya Rao and my PAN is ABCDE1234F.");
  assert.equal(composer.textContent, "Write a cover letter for [PERSON_1]");
  assert.equal(hiddenTextarea.value, "Write a cover letter for [PERSON_1]");
});

test("circuit breaker stops re-injecting inline chip if host framework strips it and skips streaming turns", async () => {
  const doc = new MiniDocument();
  const assistantMsg = doc.createElement("div");
  assistantMsg.setAttribute("data-message-author-role", "assistant");
  const markdown = doc.createElement("div");
  markdown.className = "markdown result-streaming";
  markdown.textContent = "Hello [PERSON_1]!";
  assistantMsg.appendChild(markdown);
  doc.body.appendChild(assistantMsg);

  const harness = createBackgroundHarness(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({}),
  }));
  await harness.send({
    type: "PII_SHIELD_COMMIT_REDACTION",
    redacted: "[PERSON_1]",
    mapping: { "[PERSON_1]": "Ananya Rao" },
  });

  const controller = initContentScript({
    window: {},
    document: doc,
    shared,
    runtime: harness.chromeMock.runtime,
    hostname: "chatgpt.com",
  });
  await controller.readyPromise;

  // 1. While `.result-streaming` is present, no inline chip is injected mid-stream.
  controller.scanAssistantMessages();
  assert.equal(assistantMsg.querySelectorAll("[data-piishield-chip='true']").length, 0);

  // 2. Once streaming completes, exactly 1 chip row is attached.
  markdown.classList.remove("result-streaming");
  controller.scanAssistantMessages();
  const rows = assistantMsg.querySelectorAll(".piishield-ext-chip-row");
  assert.equal(rows.length, 1);

  // 3. Simulate React / host framework stripping our injected node from the DOM:
  //    subsequent scans must circuit-break and NEVER re-append in a loop.
  rows[0].remove();
  controller.scanAssistantMessages();
  controller.scanAssistantMessages();
  assert.equal(assistantMsg.querySelectorAll(".piishield-ext-chip-row").length, 0);
});

test("content script gracefully handles 'Extension context invalidated' without uncaught rejections and still restores from in-memory session", async () => {
  const doc = new MiniDocument();
  const reply = doc.createElement("div");
  reply.className = "font-claude-message";
  reply.textContent = "Hello [PERSON_1], your phone is [PHONE_1].";
  doc.body.appendChild(reply);

  let invalidated = false;
  const storageListeners = [];
  const mockStorage = {
    onChanged: {
      addListener(fn) {
        storageListeners.push(fn);
      },
      removeListener(fn) {
        const idx = storageListeners.indexOf(fn);
        if (idx !== -1) storageListeners.splice(idx, 1);
      },
    },
  };

  const mockRuntime = {
    get id() {
      return invalidated ? undefined : "phlaehiijjaaangcelciegbkmghjbeai";
    },
    lastError: null,
    sendMessage(msg, cb) {
      if (invalidated) {
        throw new Error("Extension context invalidated.");
      }
      if (msg.type === "PII_SHIELD_GET_SESSION") {
        cb({
          ok: true,
          sessionMapping: { "[PERSON_1]": "Ananya Rao" },
          settings: { reviewBeforeReplace: true },
        });
        return;
      }
      cb({ ok: true });
    },
  };

  let observerDisconnected = false;
  class MockMutationObserver {
    observe() {}
    disconnect() {
      observerDisconnected = true;
    }
  }

  const controller = initContentScript({
    window: { MutationObserver: MockMutationObserver },
    document: doc,
    shared,
    runtime: mockRuntime,
    storage: mockStorage,
    hostname: "claude.ai",
  });
  await controller.readyPromise;
  assert.equal(storageListeners.length, 1);

  // Simulate popup updating session storage -> content script receives live update via storage.onChanged!
  storageListeners[0](
    {
      pii_shield_session_mapping_v1: {
        newValue: { "[PERSON_1]": "Ananya Rao", "[PHONE_1]": "9845012345" },
      },
    },
    "session"
  );
  assert.equal(doc.querySelector("#piishield-ext-restore-btn").textContent, "Restore (2)");

  // Now simulate extension reload in chrome://extensions -> context becomes invalidated!
  invalidated = true;

  // Clicking Shield Prompt or Restore must NEVER throw `Uncaught (in promise) Error: Extension context invalidated.`
  await assert.doesNotReject(() => controller.handleShieldClick());
  const replaced = await controller.restoreAllAssistantMessages();
  assert.equal(replaced, 2);
  assert.equal(reply.textContent, "Hello Ananya Rao, your phone is 9845012345.");
  assert.equal(observerDisconnected, true);
  assert.equal(storageListeners.length, 0);
});
