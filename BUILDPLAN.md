# SafeGen — Build Plan

Step-by-step build order. Each phase is independently deployable and testable.
Estimated total: **5-7 days**.

---

## Phase 1: Core Backend (Day 1-2) ✅ COMPLETE

**Goal:** Working Azure Function that calls Azure OpenAI and returns a response.

### Tasks

- [x] Initialize Azure Functions Python v2 project
- [x] Create `host.json`, `local.settings.example.json`, `requirements.txt`
- [x] Build `core/openai_client.py` — wrapper for Azure OpenAI calls
- [x] Build `core/models.py` — Pydantic request/response models
- [x] Build `functions/validate.py` — basic POST endpoint (no compliance yet, just proxy to OpenAI)
- [x] Write tests for OpenAI client (mocked) — 7 tests
- [x] Write tests for models — 12 tests
- [x] Write tests for validate endpoint — 7 tests

### Deliverable

`POST /api/validate` accepts a prompt and returns an Azure OpenAI response. **26 tests passing.**

---

## Phase 2: RAG Pipeline + Rule Ingestion (Day 2-3) ✅ COMPLETE

**Goal:** Upload compliance documents, chunk them, index in FAISS, retrieve relevant rules.

### Tasks

- [x] Build `core/rag_pipeline.py`:
  - Text extraction (PDF via `PyMuPDF`, DOCX via `python-docx`, MD as-is)
  - Chunking (500 tokens, 50 token overlap)
  - Embedding with `sentence-transformers` (`all-MiniLM-L6-v2`)
  - FAISS index management (add, search, persist to disk, load)
- [x] Build `core/blob_storage.py` — upload/download/list/delete from Azure Blob Storage
- [x] Build `functions/ingest_rules.py` — POST endpoint for rule upload (file + JSON)
- [x] Build `functions/list_rules.py` — GET endpoint to list rules with previews
- [x] Create sample rule documents in `rules/` directory (GDPR, bias, PII)
- [x] Write tests for RAG pipeline — 16 tests (extract, chunk, embed, FAISS, real semantic search)
- [x] Write tests for ingest endpoint — 4 tests

### Deliverable

Upload a PDF → chunks indexed in FAISS → query returns relevant rule passages. **51 tests passing (cumulative).**

---

## Phase 3: Compliance Engine (Day 3-4)

**Goal:** Validate LLM responses against rules using 4 validation layers.

### Tasks

- [ ] Build `core/validators.py`:
  - `PIIDetector` — regex patterns for email, phone, SSN, credit card
  - `BiasChecker` — keyword list + sentiment heuristic
  - `SafetyFilter` — call Azure OpenAI content safety API
- [ ] Build `core/compliance_engine.py`:
  - Orchestrates all 4 validation layers
  - RAG retrieval of relevant rules for the response
  - LLM-as-judge: ask GPT-4o to score response against retrieved rules
  - Aggregate results into final `ComplianceResult`
- [ ] Update `functions/validate.py` to run compliance engine after LLM call
- [ ] Build `functions/audit.py` — log validation results to Blob Storage
- [ ] Write tests for each validator and the engine

### Deliverable

`POST /api/validate` now returns `{ response, compliance: { passed, score, flags } }`.

---

## Phase 4: Metrics & Audit API (Day 4-5)

**Goal:** Audit log retrieval and aggregated metrics for the dashboard.

### Tasks

- [ ] Build `functions/audit.py` — GET with date/status filters
- [ ] Build `functions/metrics.py` — aggregated stats:
  - Total requests, compliance rate, top flagged rules
  - Time-series data for trend charts (last 7/30 days)
- [ ] Store audit logs as JSON blobs: `audit/{date}/{request_id}.json`
- [ ] Write tests for metrics aggregation

### Deliverable

`GET /api/metrics` returns dashboard-ready JSON. `GET /api/audit` returns paginated logs.

---

## Phase 5: React Dashboard (Day 5-7)

**Goal:** Monitoring dashboard showing compliance health at a glance.

### Tasks

- [ ] Initialize Vite + React + TypeScript + Tailwind project
- [ ] Build `services/api.ts` — typed API client
- [ ] Build `types/index.ts` — shared types matching backend models
- [ ] Build pages:
  - **DashboardPage** — ComplianceRateCard, TrendChart (Recharts), RuleHitChart
  - **RulesPage** — RuleUploader (drag-and-drop), RuleList with status
  - **AuditPage** — AuditLogTable (sortable, filterable), AuditDetail modal
- [ ] Build layout: Sidebar + Header
- [ ] Add dark mode support (Tailwind `dark:` classes)
- [ ] Docker setup: `Dockerfile.frontend`, `Dockerfile.backend`, `docker-compose.yml`

### Deliverable

Full working dashboard connected to the API. Docker Compose runs everything locally.

---

## Phase 6: Polish & Deploy (Day 7)

- [ ] Write comprehensive README with screenshots
- [ ] Add `.env.example` with all required variables
- [ ] Add GitHub Actions CI (lint + test)
- [ ] Deploy backend to Azure Functions (consumption plan)
- [ ] Deploy frontend to Azure Static Web Apps or Vercel
- [ ] Record a 2-minute demo video / GIF for README

---

## Dependencies

```
# Backend (requirements.txt)
azure-functions
openai
azure-storage-blob
faiss-cpu
sentence-transformers
PyMuPDF
python-docx
pydantic
pytest
pytest-asyncio
```

```
# Frontend (package.json)
react, react-dom, react-router-dom
typescript, @types/react
vite, @vitejs/plugin-react
tailwindcss, postcss, autoprefixer
recharts
lucide-react
```
