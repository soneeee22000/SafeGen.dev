# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (from `backend/`):

```bash
# Tests (150 passing)
cd backend && python -m pytest tests/ -v --tb=short

# Single test file
cd backend && python -m pytest tests/test_models.py -v

# Single test
cd backend && python -m pytest tests/test_models.py::TestValidateRequest::test_valid_request -v

# Lint
cd backend && python -m ruff check .

# Format
cd backend && python -m ruff format .

# Format check (CI uses this)
cd backend && python -m ruff format --check .

# Verify Azure Functions app loads
cd backend && python -c "from function_app import app; print(f'Registered {len(app._function_builders)} functions')"
```

### Frontend (from `frontend/`):

```bash
# Dev server (proxies /api to localhost:7071)
cd frontend && npm run dev

# Tests (53 passing)
cd frontend && npm run test:run

# Production build
cd frontend && npm run build

# Lint
cd frontend && npm run lint
```

### Docker:

```bash
# Full stack (backend + frontend + Azurite)
docker-compose up --build

# Individual images
docker build -t safegen-backend ./backend
docker build -t safegen-frontend ./frontend
```

## Architecture

**Serverless compliance-validation pipeline for LLM responses.** Azure Functions v2 (Python 3.10) + Azure OpenAI + FAISS vector search.

### Core Pattern: Clean Architecture with Blueprint Registration

```
backend/
  function_app.py          # Entry point — registers all Blueprint functions
  core/                    # Business logic (zero Azure Functions imports)
    models.py              # Pydantic v2 models (request/response schemas)
    openai_client.py       # Azure OpenAI wrapper (GenerationResult dataclass)
    rag_pipeline.py        # Text extraction → chunking → embedding → FAISS
    blob_storage.py        # Azure Blob Storage CRUD
    audit_logger.py        # Dual-backend audit store (FileAuditStore/BlobAuditStore)
  functions/               # HTTP triggers (thin Blueprint wrappers over core/)
    validate.py            # POST /api/validate (with audit logging)
    ingest_rules.py        # POST /api/rules/ingest
    list_rules.py          # GET /api/rules
    audit.py               # GET /api/audit (paginated audit log)
    metrics.py             # GET /api/metrics (aggregated stats)
  tests/
    conftest.py            # Shared fixtures: mock_env, mock_openai_client, sample_generation_result
```

**Key architectural rule:** `core/` must never import from `azure.functions`. All Azure Functions specifics stay in `functions/`. This keeps business logic testable without the Functions runtime.

### Data Flow

1. **Validate:** Client → `functions/validate.py` → `core/openai_client.py` → Azure OpenAI → compliance engine → audit logger → Response
2. **Ingest Rules:** Upload document → extract text → chunk → embed with sentence-transformers → add to FAISS index → persist to disk
3. **List Rules:** Read FAISS index metadata → group chunks by source file → return summaries
4. **Audit:** GET /api/audit → `core/audit_logger.py` → FileAuditStore (local) or BlobAuditStore (Azure) → paginated records
5. **Metrics:** GET /api/metrics → audit store → single-pass O(n) aggregation → totals, rates, time series

### Blueprint Pattern

Each endpoint is an `azure.functions.Blueprint`. New endpoints: create a Blueprint in `functions/`, register it in `function_app.py`.

### Lazy Initialization

Both the OpenAI client (`validate.py`) and embedding model (`rag_pipeline.py`) are lazy-loaded module-level singletons to optimize cold starts.

## Build Progress

- **Phase 1** (Core Backend): COMPLETE
- **Phase 2** (RAG Pipeline): COMPLETE
- **Phase 3** (Compliance Engine): COMPLETE — PII detection, bias checking, safety filtering
- **Phase 4** (Metrics & Audit API): COMPLETE — Dual-backend audit logging, paginated audit retrieval, aggregated metrics
- **Phase 5** (React Dashboard): COMPLETE — Vite + React 19 + TypeScript, shadcn/ui, Recharts, 3 pages
- **Phase 6** (Docker + CI/CD): COMPLETE — Dockerfiles, docker-compose, GitHub Actions CI (backend + frontend + Docker)
- **Phase 7** (Playground): COMPLETE — Interactive compliance validation page with example prompts, category toggles, 53 frontend tests

## Dependency Pins

`sentence-transformers>=2.5.0,<3.0.0` and `transformers>=4.38.0,<5.0.0` are pinned because the global Python environment has conflicting packages. Do not widen these ranges.

## Ruff Configuration

Line length 120, Python 3.10 target. TCH001-003 rules are ignored because moving imports into `TYPE_CHECKING` blocks breaks runtime. See `pyproject.toml` for full rule set.

## Test Patterns

- All external services are mocked (Azure OpenAI, Blob Storage)
- Use `mock_env` fixture from `conftest.py` for environment variables
- Use `monkeypatch.setattr` to inject mock clients into endpoint modules
- Test API keys use variable patterns (not string literals) to pass the `scan-secrets.js` commit hook

## Rules Documents

Sample compliance rules live in `rules/` (GDPR, bias detection, PII handling). These are ingested via `/api/rules/ingest` and indexed in FAISS for semantic retrieval.
