# PII Shield — Improvement & Change Ideas

Everything I could identify after reading the full codebase, eval results, error analysis, deployment config, and your notes. Not ordered by priority — just grouped so we can pick and sequence later.

---

## A. Stack Migration — Moving to Google

### A1. Deployment: Modal → Google Cloud Run
Your `modal_app.py` wraps a standard ASGI/FastAPI app. Cloud Run can serve the same Docker image you already have — push the existing `Dockerfile` to Artifact Registry and deploy. Free tier gives 2M requests/month, 360k vCPU-seconds, and 1 GiB outbound. Cold-start is comparable to Modal's scale-to-zero; you can set `min-instances: 1` to keep one warm if you want.

**What changes:** Delete `modal_app.py`, add a `clouddeploy.yaml` or a `gcloud run deploy` command in a script. The Dockerfile already works.

### A2. NER model: GLiNER → Gemma-based NER (or keep GLiNER, see notes)
Google's options for free NER:
- **gemma-ner** (community fine-tunes on HF like `Spacy-Galaxy/gemma-2b-NER`): These are 2B+ param LLMs doing NER via generation. They're **slow on CPU** (~seconds per item, not ms) and use **4–8 GB RAM** — a big regression from GLiNER's 212ms median and 2.7 GB RAM. Not practical for a lightweight tool without a GPU.
- **Google Cloud Natural Language API**: Has entity extraction, but it's **paid** after 5K units/month. Defeats the purpose.
- **Gemini API with free tier (1500 req/day on `gemini-2.0-flash`)**: You could call Gemini as an NER layer — send the text asking "extract person names and addresses" and parse the response. This is architecturally interesting but means **sending the text to Google's API**, which contradicts the entire privacy premise of PII Shield.

> [!IMPORTANT]
> **My honest take:** GLiNER is actually a good fit here — it's small, runs on CPU, is fast, and is specifically trained for PII. The weak spots (PERSON recall 0.74, LOCATION recall 0.44) are solvable by improving rules and post-processing, not necessarily by swapping the model. I'd keep GLiNER and focus improvements on the detection logic unless you specifically want a Google-branded model for portfolio/resume reasons.

### A3. Container Registry: Docker Hub / Modal → Google Artifact Registry
If you move to Cloud Run, your images naturally live in Artifact Registry. Free for the storage amounts you'd use.

### A4. CI/CD: → Google Cloud Build
Free 120 build-minutes/day. Trigger on GitHub push, run tests, build image, deploy to Cloud Run. Replaces any manual `modal deploy` workflow.

### A5. Hosting the UI: → Firebase Hosting (optional)
If you ever want to separate the static frontend from the API (e.g., for a CDN edge), Firebase Hosting is free-tier and Google-stack. But serving from FastAPI as you do now is simpler and fine.

---

## B. Detection Performance Improvements

### B1. Fix NER boundary errors (biggest win for PERSON)
The error analysis shows GLiNER repeatedly includes preceding context words: `"bhai F Gokhale"`, `"Candidate N Patel"`, `"hii nikhita reddy"`. Your NER post-processing already strips honorifics and "ji" — extend it with a stop-word prefix list: `bhai`, `candidate`, `hii`, `hey`, `dear`, `from`, `to`, common Hindi particles. This alone could fix ~8 of the boundary errors.

### B2. Fix "Surname, First" sign-off pattern
`"Regards,\nKaur, Jasmeet"` gets split into two spans instead of one. The rules layer's `_SIGNOFF` regex expects `FirstName LastName` after "Regards,". Add a "Last, First" variant. Same for the NER post-processing — if two adjacent PERSON spans from NER are separated only by `, `, merge them.

### B3. Fix short/nickname misses
Nicknames like `Faiy`, `Simry`, `Aswaty`, `Fioy` and standalone first names like `Amrit`, `Zain`, `Mukta`, `Senthil` after context phrases like `"follow up with"`, `"circular —"`, `"Ship to"` are missed. Add contextual rules:
- `follow up with <Name>`
- `Ship to <Name> at`
- `circular — <Name>`
- `From: <Name>\n`
- `update for <Name> —`
These are high-precision patterns that don't need NER.

### B4. Fix "surname on roster" / initial-name misses
`"H. F. Nayak"` is detected but `"(surname on roster: Nayak)"` isn't. Add a rule: `surname on roster: <Name>` and similar parenthetical patterns.

### B5. Improve full-address detection
Addresses like `"41 Lotus Lane, Test Garden, Hyderabad"` are completely missed, and `"96 Maple Road, Sample Nagar, Hyderabad"` gets truncated. The NER sees these as partial spans. Options:
- **Address-assembly post-processing**: When NER returns a partial address span, expand it forward/backward to the nearest comma-separated city name or pincode. Use a list of major Indian city names.
- **Regex address pattern**: Match `\d+ [A-Z][a-z]+ (Street|Road|Lane|Cross|Avenue), .*, (city name)` patterns.
- **Merge adjacent LOCATION spans**: If two LOCATION spans are separated only by `, `, merge them.

### B6. Expand address-context keywords for pincode detection
`_ADDRESS_CONTEXT` only has 6 city/landmark terms. Add more Indian cities (Mumbai, Delhi, Chennai, Kolkata, Pune, Jaipur, etc.) and address vocabulary (street, lane, layout, colony, extension, enclave, block, flat, apartment, floor, building, etc.).

### B7. Expand UPI provider list
`constants.py` only has 5 providers. India has 50+ UPI handles: `ybl`, `ibl`, `axl`, `upi`, `apl`, `barodampay`, `cnrb`, `csbpay`, `dlb`, `fbl`, `federal`, `hsbc`, `idbi`, `ikwik`, `indus`, `kbl`, `kotak`, `mahb`, `pnb`, `rbl`, `sbi`, `sib`, `ubi`, `united`, `vijb`, `yesbank`, etc.

### B8. False alarm: `"Customer"` and `"address"` as PERSON/LOCATION
Item t060 flags `"Customer"` as PERSON, items t052/t070 flag the word `"address"` as LOCATION. Add these to a NER blocklist — common English words that GLiNER misidentifies.

### B9. Lowercase name handling
`"hii nikhita reddy"` — the NER detects it but includes `"hii"`. Even after fixing B1, lowercase names without title cues are inherently hard. Consider: if GLiNER detects a name and the first token is all-lowercase and not a known name, trim it.

### B10. Bigger and more diverse evaluation dataset
60 dev + 100 test items from templates is small. Generate 500+ items with more varied templates, mixed PII types per item, longer text, and edge cases. Consider including: multi-paragraph text, emails with headers, chat-style multi-turn conversations.

### B11. Native-script (Devanagari, etc.) support
Currently English-only. GLiNER does support multilingual text to some degree. This is a bigger effort — needs a new evaluation set, potentially a different or additional model, and UI changes for RTL/complex scripts.

---

## C. User Experience — Beyond Copy-Paste

### C1. Chrome Extension (most practical next step)
A Chrome extension can **intercept the AI chat textbox** and auto-redact before sending, then auto-restore in the response. Architecture options:

| Approach | How it works | Pros | Cons |
|---|---|---|---|
| **Content script injection** | Inject JS into ChatGPT/Gemini/Claude pages. Intercept the send button, call your API to redact, replace the textarea content, let the message send. When the response streams in, restore placeholders. | Seamless UX, works per-site | Needs to track DOM changes per chatbot (fragile), one content script per supported site |
| **Side panel** | Extension opens a side panel. User types there, clicks redact, copies to chat. Paste AI reply back, restore. | Simpler, works with any AI chat | Still manual copy-paste, just in a panel |
| **Proxy/request interception** | Use `chrome.webRequest` or `chrome.declarativeNetRequest` to intercept the API call to the AI service, modify the body in-flight, and modify the response on the way back. | Fully transparent to the user | Extremely fragile (API formats change), may break streaming/SSE, violates many sites' ToS, MV3 restrictions make this hard |

**My recommendation:** Start with **content script + floating button** for the top 3 sites (ChatGPT, Gemini, Claude). When the user clicks "Shield" before sending, the extension:
1. Grabs the textarea content
2. Calls your PII Shield API (or runs detection locally — see C2)
3. Shows a diff/preview of what will be redacted
4. Replaces the textarea with redacted text
5. Stores the mapping in `chrome.storage.session`
6. When the AI responds, offers a "Restore" button that swaps placeholders back in the displayed response

This is the **highest-impact UX improvement** — it eliminates the copy-paste workflow entirely.

### C2. In-browser inference (ambitious but possible)
Run the NER model **in the browser** using ONNX Runtime Web or Transformers.js. GLiNER has an ONNX export. This means:
- **Zero server round-trips** — text never leaves the device
- **True privacy** — no network at all
- **Works offline**
- **Downside**: First load downloads ~100–200 MB of model weights (cached after). Inference is slower on CPU in WASM (~500ms–2s). WebGPU could help but browser support is still partial.

You could make this the **premium mode** in the extension: "Local mode (private, slower)" vs "API mode (faster, text goes to your server)".

### C3. Desktop app / system-wide proxy
A local proxy (e.g., mitmproxy-based) that sits between the browser and the internet, intercepts requests to known AI APIs, redacts the body, and restores the response. This is the "gateway" idea you mentioned.
- **Pros**: Works with any AI tool, not just browser chat
- **Cons**: Requires installing a local CA cert (trust issues), complex setup, doesn't work well with pinned certs, hard to handle streaming responses
- **Verdict**: Cool concept, but the Chrome extension is 10x easier and covers 95% of use cases. I'd skip this unless you specifically want to support desktop AI apps.

### C4. Keyboard shortcut / system tray app
A lightweight system tray app: user selects text anywhere, presses a hotkey, text gets redacted in the clipboard. Paste into any AI. For restore: copy AI reply, press another hotkey, restored text in clipboard.
- Simple, universal, doesn't depend on specific sites
- Needs a background process
- Could be built with Tauri (Rust + WebView) or Electron

---

## D. API & Distribution

### D1. Public API — worth it or not?
You asked if making the API available externally makes sense. My take:

**Potential consumers:**
- Other developers building AI wrappers / chatbot UIs who want PII scrubbing as a feature
- Enterprise tools that pipe text through an API before sending to LLMs
- Other Chrome extensions or browser tools

**But:**
- Your tool's value is the **India-specific detection** — a niche. Generic PII detection services already exist (Presidio, Private AI, etc.)
- Hosting costs scale with usage. Free API = abuse magnet
- The privacy promise gets complicated when third parties send you their users' data

**Verdict:** Don't prioritize a public API now. If you build the Chrome extension, it'll call your API anyway. If someone else wants to use it, they can self-host the Docker image. Consider a public API later if there's demand, with rate limiting and an API key.

### D2. OpenAPI / Swagger docs
Your FastAPI app already auto-generates these at `/docs`. Make sure it's clean and useful — add descriptions, examples, and response schemas to the Pydantic models. This helps if you ever open the API, and it's good practice regardless.

### D3. npm / pip package
Package the Python engine as a pip-installable library (`pip install pii-shield`) so developers can use it programmatically without running the server. Low effort, nice for portfolio.

---

## E. General Engineering Improvements

### E1. [Done] Async NER inference
`GlinerNer.detect()` is synchronous and runs on the main thread. In FastAPI (async), this blocks the event loop. Wrap it in `asyncio.run_in_executor()` or use a thread pool so the API can handle concurrent requests without blocking.

### E2. [Done] Rate limiting
No rate limiting currently. Add a simple in-memory rate limiter (e.g., `slowapi` or a custom token bucket) to prevent abuse on the hosted version.

### E3. [Done] Request size limit enforcement on the frontend
The API has a 20K char limit, but the frontend doesn't warn before sending. Add a character counter and disable the button when over the limit.

### E4. [Done] Dark mode
The UI is light-only. Add a `prefers-color-scheme: dark` media query and CSS custom properties for dark mode. Small effort, nice polish.

### E5. [Done] Confidence display in the UI
Show the NER confidence scores in the highlighted spans (maybe as a tooltip or opacity). Helps users understand why some things are flagged and others aren't.

### E6. Selective redaction
Let the user click on a highlighted span to toggle it on/off before copying the redacted text. "I don't want to redact this name, it's a public figure."

### E7. Session history
Store past redaction sessions in `localStorage` or `IndexedDB` (redacted text + mapping only, never raw text). Let the user restore a previous mapping if they close the tab accidentally.

### E8. Telemetry / analytics (privacy-safe)
Track anonymous usage metrics: how many redactions, how many spans detected, latency, error rates. Use something privacy-friendly and self-hosted like Plausible or just log counts server-side. No request bodies, ever.

### E9. Add more PII types
- **Date of birth**: Common in resumes and forms
- **Passport number**: Indian passport format `[A-Z][0-9]{7}`
- **Voter ID**: Indian EPIC format `[A-Z]{3}[0-9]{7}`
- **Driving license**: State-specific formats
- **Bank account numbers**: Less structured but detectable with context
- **IP addresses**: Sometimes PII

### E10. [Done] Better error handling in the UI
Currently errors show as a text string in the status area. Add proper toast notifications or error banners with retry buttons.

### E11. [Done] Accessibility audit
The UI uses semantic HTML and ARIA, which is good. Run an axe audit, check keyboard navigation, screen reader flow, and color contrast for the entity highlight colors.

### E12. Tests for the Chrome extension
If you build C1, the extension needs its own test suite: content script injection tests, mapping persistence tests, DOM manipulation tests for each supported AI chat site.

---

## F. Summary Matrix

| # | What | Effort | Impact | Dependencies |
|---|---|---|---|---|
| A1 | Modal → Cloud Run | Low | Medium (cost, Google stack) | Dockerfile already works |
| A2 | GLiNER → Google NER | High | Uncertain (may regress) | Needs GPU or accepts slowdown |
| A3 | Artifact Registry | Low | Low (follows from A1) | A1 |
| A4 | Cloud Build CI/CD | Medium | Medium | A1, A3 |
| B1 | NER boundary stop-words | Low | High (fixes ~8 errors) | None |
| B2 | Surname-comma sign-off | Low | Medium | None |
| B3 | Contextual name rules | Low-Med | High (fixes ~10 misses) | None |
| B4 | Parenthetical surname rule | Low | Low-Med | None |
| B5 | Address assembly | Medium | High (biggest LOCATION gap) | None |
| B6 | Expand address keywords | Low | Low-Med | None |
| B7 | Expand UPI providers | Low | Low | None |
| B8 | NER word blocklist | Low | Low-Med (fixes 3 FPs) | None |
| B9 | Lowercase name trimming | Low | Low | B1 |
| B10 | Bigger eval dataset | Medium | High (confidence in scores) | None |
| B11 | Native-script support | High | Medium | New eval set, possibly new model |
| C1 | Chrome extension | High | Very High (core UX) | API must be deployed |
| C2 | In-browser inference | High | High (true privacy) | ONNX export of GLiNER |
| C3 | System proxy | Very High | Medium | Not recommended first |
| C4 | Keyboard shortcut app | Medium | Medium | None |
| D1 | Public API | Low-Med | Low for now | A1 |
| D2 | OpenAPI docs polish | Low | Low | None |
| D3 | pip package | Low | Low-Med | None |
| E1 | Async NER `[Done]` | Low | Medium (concurrency) | None |
| E2 | Rate limiting `[Done]` | Low | Medium (abuse prevention) | None |
| E3 | Frontend char limit `[Done]` | Low | Low | None |
| E4 | Dark mode `[Done]` | Low | Low (polish) | None |
| E5 | Confidence display `[Done]` | Low | Low (UX) | None |
| E6 | Selective redaction | Medium | High (UX) | None |
| E7 | Session history | Low-Med | Medium (UX) | None |
| E9 | More PII types | Medium | Medium | New validators, eval data |
| E10 | Better error UI `[Done]` | Low | Low | None |
| E11 | Accessibility audit `[Done]` | Low | Low | None |

> [!TIP]
> The highest-impact, lowest-effort wins are **B1 + B2 + B3** (detection rule fixes — could boost PERSON recall from 0.74 to ~0.85+), followed by **A1** (Modal → Cloud Run, since the Dockerfile already works), and then **C1** (Chrome extension for the real UX leap).
