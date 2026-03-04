# SafeGen — Build Plan

Step-by-step build order. Each phase is independently deployable and testable.

---

## Phase 1: Core Backend ✅

**Goal:** Working Azure Function that calls Azure OpenAI and returns a response.

- [x] Azure Functions Python v2 project with blueprint pattern
- [x] `core/openai_client.py` — Azure OpenAI wrapper with GenerationResult
- [x] `core/models.py` — Pydantic v2 request/response models
- [x] `functions/validate.py` — POST /api/validate (LLM proxy)
- [x] 26 tests passing (models, openai_client, validate)

**Deliverable:** `POST /api/validate` accepts a prompt and returns an Azure OpenAI response.

---

## Phase 2: RAG Pipeline ✅

**Goal:** Upload compliance documents, chunk, index in FAISS, retrieve relevant rules.

- [x] `core/rag_pipeline.py` — text extraction (PDF/DOCX/MD), chunking (500 tokens, 50 overlap), HF embeddings, FAISS index
- [x] `core/blob_storage.py` — Azure Blob Storage CRUD
- [x] `functions/ingest_rules.py` — POST /api/rules/ingest (file upload)
- [x] `functions/list_rules.py` — GET /api/rules (list with previews)
- [x] Sample rule documents in `rules/` (GDPR, bias, PII)
- [x] 51 tests passing (cumulative)

**Deliverable:** Upload a PDF, chunks indexed in FAISS, query returns relevant rule passages.

---

## Phase 3: Compliance Engine ✅

**Goal:** Multi-layer validation of LLM responses against compliance rules.

- [x] `core/validators.py` — PIIDetector (email, phone, SSN, credit card, IPv4), BiasChecker (gendered terms, ableist language, stereotypes), SafetyFilter (hate, violence, self-harm)
- [x] `core/compliance_engine.py` — orchestrates validators, computes score (1.0 base, -0.3 critical, -0.1 warning)
- [x] Smart exclusions: example.com emails, date-like SSNs, version-like IPs, educational context
- [x] Category filtering via RulesCategory enum
- [x] Updated `functions/validate.py` with compliance pipeline + audit logging
- [x] 120 tests passing (cumulative, including 40 validator tests + 27 engine tests)

**Deliverable:** `POST /api/validate` returns `{ response, compliance: { passed, score, flags, layers_run } }`.

---

## Phase 4: Metrics & Audit API ✅

**Goal:** Audit log retrieval and aggregated metrics for the dashboard.

- [x] `core/audit_logger.py` — dual-backend store (FileAuditStore for local, BlobAuditStore for Azure)
- [x] `functions/audit.py` — GET /api/audit (paginated, date/status filters)
- [x] `functions/metrics.py` — GET /api/metrics (totals, rates, flag breakdown, time series)
- [x] Single-pass O(n) aggregation for metrics
- [x] 150 tests passing (cumulative)

**Deliverable:** `GET /api/metrics` returns dashboard-ready JSON. `GET /api/audit` returns paginated logs.

---

## Phase 5: React Dashboard ✅

**Goal:** Monitoring dashboard showing compliance health at a glance.

- [x] Vite + React 19 + TypeScript (strict mode) + Tailwind CSS v4
- [x] shadcn/ui components (button, card, badge, table, dialog, input, select, separator, skeleton, tooltip)
- [x] Typed API client with error handling (`ApiError` class)
- [x] `useApi<T>` generic data-fetching hook, `useTheme` dark mode toggle
- [x] **DashboardPage** — 4 KPI cards, TrendChart (Recharts AreaChart), FlagBreakdownChart (BarChart), ScoreGauge, 60s auto-refresh
- [x] **AuditPage** — date/status filters, paginated table, detail modal with flag list
- [x] **RulesPage** — drag-and-drop upload zone, rule card grid
- [x] Responsive layout: fixed sidebar (256px), mobile hamburger, light/dark mode
- [x] Vite dev proxy `/api` → `localhost:7071`
- [x] 41 frontend tests passing (vitest + testing-library)

**Deliverable:** Full working dashboard at `localhost:5173` consuming all 5 backend API endpoints.

---

## Phase 6: Docker + CI/CD ✅

**Goal:** Containerize and automate testing/builds.

- [x] `backend/Dockerfile` — Azure Functions Python v4 container with health check
- [x] `frontend/Dockerfile` — multi-stage (Node build + nginx serve) with SPA routing
- [x] `frontend/nginx.conf` — SPA fallback + `/api/` proxy to backend + asset caching
- [x] `docker-compose.yml` — full stack: backend + frontend + Azurite (Blob emulator), health checks, env passthrough
- [x] `.dockerignore` files for root, backend, frontend
- [x] GitHub Actions CI — 7 parallel jobs: backend lint/test/build, frontend lint/test/build, Docker build

**Deliverable:** `docker-compose up --build` runs the full stack. CI validates every push/PR.

```bash
docker-compose up --build
# Backend:  http://localhost:7071
# Frontend: http://localhost:5173
# Azurite:  http://localhost:10000
```

---

## Test Summary

| Module                      | Tests   | What's Covered                                 |
| --------------------------- | ------- | ---------------------------------------------- |
| `test_models.py`            | 17      | Pydantic validation, all model types           |
| `test_openai_client.py`     | 7       | Azure OpenAI wrapper, error handling           |
| `test_validate.py`          | 13      | /api/validate endpoint, compliance integration |
| `test_rag_pipeline.py`      | 16      | Extract, chunk, embed, FAISS, semantic search  |
| `test_ingest_rules.py`      | 8       | /api/rules/ingest, file parsing                |
| `test_compliance_engine.py` | 27      | Scoring, flag aggregation, category filtering  |
| `test_validators.py`        | 40      | PII/bias/safety detectors, edge cases          |
| `test_audit.py`             | 10      | /api/audit, pagination, filters                |
| `test_audit_logger.py`      | 6       | File + Blob store backends                     |
| `test_metrics.py`           | 6       | /api/metrics, aggregation                      |
| Frontend (8 files)          | 41      | Formatters, API client, components, pages      |
| **Total**                   | **191** | **Backend: 150 + Frontend: 41**                |
