# SafeGen — Roadmap

What we've built, what's next, and the phases to make it world-class.

---

## Current State: What We Have

| Area                                  | Status   | Quality                            |
| ------------------------------------- | -------- | ---------------------------------- |
| Backend API (5 endpoints)             | Complete | Production-grade                   |
| Compliance Engine (PII, bias, safety) | Complete | Strong — smart exclusions, scoring |
| RAG Pipeline (FAISS + embeddings)     | Complete | Functional                         |
| React Dashboard (3 pages)             | Complete | Functional but incomplete          |
| Docker + CI/CD                        | Complete | Solid                              |
| Tests (203 total)                     | Complete | Excellent coverage                 |

**Overall: Strong engineering, weak storytelling.** The hardest parts are built. What's missing is the layer that makes someone say "that's cool" in 10 seconds.

---

## Phase 7: Playground — COMPLETE

**Status: COMPLETE** — Interactive `/playground` page where users type a prompt, submit it, and watch the compliance engine analyze the LLM response in real-time. Deployed at [safe-gen-dev.vercel.app/playground](https://safe-gen-dev.vercel.app/playground).

### What to Build

- **Prompt input** — textarea with character count and example prompts
- **Submit button** — calls `POST /api/validate` and streams the result
- **Response panel** — shows the LLM response with inline flag highlights
- **Compliance sidebar** — score gauge, pass/fail badge, flag list with severity
- **Example prompts** — pre-loaded buttons that demonstrate each validator:
  - "Clean" prompt (passes all checks)
  - PII prompt (triggers email/phone/SSN detection)
  - Bias prompt (triggers gendered language detection)
  - Mixed prompt (triggers multiple validators)
- **Category toggles** — let users enable/disable PII, bias, safety layers to see the difference

### Why This Matters

This is the page you demo in interviews. This is the page in the README GIF. This is the page that turns "I built a compliance pipeline" into "let me show you what it does."

### Files

| File                                             | Purpose                               |
| ------------------------------------------------ | ------------------------------------- |
| `src/pages/PlaygroundPage.tsx`                   | Main page with prompt input + results |
| `src/components/playground/PromptInput.tsx`      | Textarea with example buttons         |
| `src/components/playground/ComplianceResult.tsx` | Score, flags, pass/fail display       |
| `src/components/playground/ResponseViewer.tsx`   | LLM response with highlighted flags   |
| `src/components/playground/CategoryToggle.tsx`   | PII/bias/safety layer toggles         |

### Tests

- Renders prompt input and submit button
- Displays loading state during API call
- Renders compliance results with flags
- Example prompt buttons populate textarea
- Category toggles update request payload

---

## Phase 8: First Impressions — Seed Data & Empty States

**Priority: HIGH** — A dashboard full of zeros tells no story.

### What to Build

- **Seed data script** (`scripts/seed_demo.py`) — sends 15-20 curated validation requests that produce a mix of pass/fail/flagged results across different days
- **Demo mode flag** — `DEMO_MODE=true` env var that auto-seeds on first startup
- **Better empty states:**
  - Dashboard: "No validation data yet. Try the Playground to get started." with link
  - Audit Log: "No audit records. Send your first prompt from the Playground."
  - Rules: "No rules ingested yet. Upload a compliance document to get started."
- **Score gauge fix** — show "No data" instead of "0.0% Critical" when empty
- **Grammar fix** — "1 chunk" not "1 chunks"

### Why This Matters

A hiring manager will `docker-compose up`, open `localhost:5173`, and see either a compelling dashboard or a wall of zeros. You get one chance.

---

## Phase 9: Rules Page — Make It Useful

**Priority: MEDIUM** — Currently the weakest page. Three cards with "1 chunks" is not impressive.

### What to Build

- **Rule detail modal** — click a card to see the full extracted text, chunk count, and when it was ingested
- **Rule content preview** — show first 2-3 lines of each rule on the card itself
- **Delete rule** — button to remove an ingested rule (needs new `DELETE /api/rules/:id` endpoint)
- **Chunk visualization** — show how the document was split into chunks (demonstrates RAG understanding)
- **Search rules** — text search across ingested rule content (demonstrates semantic search)
- **Better cards** — add icon per document type (PDF, MD, DOCX, TXT), file size, ingestion timestamp

### Backend Additions

| Endpoint            | Method | Purpose                                 |
| ------------------- | ------ | --------------------------------------- |
| `/api/rules/:id`    | GET    | Get single rule with full text + chunks |
| `/api/rules/:id`    | DELETE | Remove rule and re-index FAISS          |
| `/api/rules/search` | POST   | Semantic search across rule chunks      |

---

## Phase 10: Visual Polish — Design That Impresses

**Priority: MEDIUM** — The UI is functional but generic. Small changes have outsized impact on perception.

### What to Fix

- **Flag Breakdown chart** — replace the purple with a proper color scale (red for critical, amber for warning, blue for info) that matches the severity system
- **Request Trend chart** — add passed (green area) vs failed (red area) stacked visualization instead of a single line
- **Score gauge** — add animation on load (count up from 0 to actual value)
- **Sidebar active state** — add a left border accent on the active nav item
- **Loading skeletons** — replace any flash of empty content with skeleton loaders (already have the shadcn component, just need to wire it up consistently)
- **Responsive mobile** — test and fix the hamburger menu, ensure tables scroll horizontally on small screens
- **Favicon** — add a proper SafeGen icon instead of the default Vite logo
- **Page transitions** — subtle fade between route changes

### Design Tokens to Refine

```
Critical flags: hsl(0, 84%, 60%)    — Red
Warning flags:  hsl(38, 92%, 50%)   — Amber
Info flags:     hsl(217, 91%, 60%)  — Blue
Passed:         hsl(142, 71%, 45%)  — Green
Failed:         hsl(0, 84%, 60%)    — Red
```

---

## Phase 11: README & Documentation — The Portfolio Wrapper

**Priority: HIGH** — The README is the landing page of your portfolio piece. Most people never look past it.

### What to Add

- **Hero GIF** — 15-second recording of the Playground page: type a prompt with PII, submit, watch flags appear. This single asset will get more attention than anything else.
- **Architecture diagram** — Mermaid or Excalidraw diagram showing the full data flow: Client -> Azure Functions -> OpenAI -> Compliance Engine -> Audit Store -> Dashboard
- **Quick start that actually works** — `docker-compose up` with seed data, link to `localhost:5173/playground`
- **Screenshots** — Dashboard (dark mode), Playground with flags, Audit detail modal
- **Feature comparison table** — what SafeGen validates vs what raw LLM output gives you
- **Tech decision rationale** — brief "Why FAISS over Pinecone?" "Why Azure Functions over FastAPI?" sections that show architectural thinking

### Files

| File                           | Purpose                                    |
| ------------------------------ | ------------------------------------------ |
| `README.md`                    | Rewrite with GIF, screenshots, quick start |
| `docs/screenshots/`            | Dashboard, Playground, Audit screenshots   |
| `docs/architecture.excalidraw` | Visual architecture diagram                |

---

## Phase 12: Production Hardening

**Priority: LOW** (for portfolio) / **HIGH** (for real deployment)

### What to Add

- **Rate limiting** — prevent abuse of the validate endpoint
- **Request validation** — max prompt length, content-type checks
- **Error boundaries** — React error boundary component so one component crash doesn't take down the whole app
- **API retry logic** — exponential backoff in the frontend API client
- **Health check endpoint** — `GET /api/health` returning status + dependency health
- **Structured logging** — JSON logs with correlation IDs for request tracing
- **OpenAPI spec** — auto-generated Swagger docs from the Azure Functions endpoints
- **Environment config** — proper config management for dev/staging/prod

---

## Phase 13: Advanced Features (Stretch)

**Priority: NICE-TO-HAVE** — These push SafeGen from "good portfolio project" to "this person thinks about AI safety deeply."

### Ideas

- **Custom rule authoring** — let users write their own compliance rules in the UI (not just upload documents)
- **Rule effectiveness dashboard** — which rules trigger most often? Which are never triggered?
- **Prompt rewriting** — when a flag is detected, suggest a rewritten version that passes compliance
- **Batch validation** — upload a CSV of prompts and get a compliance report
- **Webhook notifications** — alert on critical compliance failures
- **Multi-model comparison** — validate the same prompt against GPT-4o, GPT-3.5, and compare compliance scores
- **Export audit report** — PDF/CSV export of audit logs for compliance documentation

---

## Priority Matrix

| Phase                             | Impact          | Effort            | Do It    |
| --------------------------------- | --------------- | ----------------- | -------- |
| Phase 7: Playground               | Transformative  | 1 session         | DONE     |
| Phase 8: Seed Data + Empty States | High            | 2 hours           | Second   |
| Phase 11: README + GIF            | High            | 1 hour            | Third    |
| Phase 10: Visual Polish           | Medium          | 3 hours           | Fourth   |
| Phase 9: Rules Page               | Medium          | 1 session         | Fifth    |
| Phase 12: Production Hardening    | Low (portfolio) | 1 session         | Optional |
| Phase 13: Advanced Features       | Low (portfolio) | Multiple sessions | Stretch  |

---

## The 80/20

If you only do three things:

1. **Build the Playground page** — this is the demo
2. **Record a README GIF** — this is the hook
3. **Add seed data** — this is the first impression

Everything else is polish. These three turn SafeGen from "strong backend project with a monitoring UI" into "full-stack AI safety platform you can demo live."
