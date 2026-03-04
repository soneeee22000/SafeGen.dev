# SafeGen — Responsible AI Compliance API

A serverless compliance-validation pipeline built on **Azure Functions** that intercepts LLM responses and evaluates them against configurable safety, bias, and regulatory rules before serving to end users. Includes a **React/TypeScript** monitoring dashboard.

## Why This Exists

Organizations deploying LLMs need guardrails. SafeGen sits between your application and Azure OpenAI, validating every response against your compliance rules using RAG-based policy retrieval — no redeployment needed when rules change.

## Tech Stack

| Layer        | Technology                                                       |
| ------------ | ---------------------------------------------------------------- |
| **Backend**  | Azure Functions (Python 3.11), FastAPI-style HTTP triggers       |
| **AI/LLM**   | Azure OpenAI GPT-4o, Prompt Engineering                          |
| **RAG**      | FAISS vector store, Hugging Face embeddings (`all-MiniLM-L6-v2`) |
| **Storage**  | Azure Blob Storage (audit logs, rule documents)                  |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Recharts               |
| **Database** | Azure Table Storage (metrics), local SQLite for dev              |
| **DevOps**   | Docker, Azure DevOps, Git                                        |
| **Tools**    | VS Code, Azure Functions Core Tools                              |

## Features

- **Compliance Validation Pipeline** — Every LLM response passes through configurable rule checks (safety, bias, regulatory, PII detection) before delivery
- **RAG-Based Rule Engine** — Upload compliance documents (PDF/DOCX), automatically chunked and indexed in FAISS for semantic rule retrieval
- **Real-Time Dashboard** — React/TypeScript SPA showing compliance rates, flagged outputs, rule hit frequency, and trend charts
- **Audit Trail** — Every validation result logged to Azure Blob Storage with full request/response payloads for regulatory review
- **Dynamic Policy Updates** — Add or modify compliance rules without redeploying the API; rules are retrieved via RAG at inference time

## Architecture Overview

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Client App  │────▶│  Azure Function   │────▶│  Azure OpenAI   │
│  (any app)   │     │  /api/validate    │     │  GPT-4o         │
└─────────────┘     └────────┬─────────┘     └─────────────────┘
                             │
                    ┌────────▼─────────┐
                    │ Compliance Engine │
                    │  ┌─────────────┐ │
                    │  │ FAISS Index │ │◀── Rule Documents (Blob Storage)
                    │  │ (policies)  │ │
                    │  └─────────────┘ │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐     ┌─────────────────┐
                    │  Audit Logger     │────▶│  Azure Blob     │
                    │                   │     │  Storage        │
                    └───────────────────┘     └─────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  React Dashboard  │
                    │  (Metrics + Logs) │
                    └───────────────────┘
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+ / pnpm
- Azure Functions Core Tools v4
- Azure account (free tier works for dev)
- Azure OpenAI resource with GPT-4o deployed

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp local.settings.example.json local.settings.json
# Fill in your Azure OpenAI and Blob Storage credentials
func start
```

### Frontend Setup

```bash
cd frontend
pnpm install
cp .env.example .env.local
# Fill in your API base URL
pnpm dev
```

### Run with Docker

```bash
docker-compose up --build
```

## API Endpoints

| Method | Endpoint            | Status | Description                                        |
| ------ | ------------------- | ------ | -------------------------------------------------- |
| `POST` | `/api/validate`     | ✅     | Send prompt, get compliance-validated LLM response |
| `POST` | `/api/rules/ingest` | ✅     | Upload compliance rule documents (PDF/DOCX/MD/TXT) |
| `GET`  | `/api/rules`        | ✅     | List all active compliance rules with previews     |
| `GET`  | `/api/audit`        | 🔲     | Retrieve audit logs with filters                   |
| `GET`  | `/api/metrics`      | 🔲     | Dashboard metrics (compliance rate, flags, trends) |

## Environment Variables

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER_RULES=compliance-rules
AZURE_STORAGE_CONTAINER_AUDIT=audit-logs
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Tests

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
python -m pytest tests/ -v
```

**51 tests passing** across 5 test modules:

- `test_models.py` — 12 tests (Pydantic request/response validation)
- `test_openai_client.py` — 7 tests (Azure OpenAI wrapper, mocked)
- `test_validate.py` — 7 tests (POST /api/validate endpoint)
- `test_rag_pipeline.py` — 16 tests (extraction, chunking, embedding, FAISS, semantic search)
- `test_ingest_rules.py` — 4 tests (POST /api/rules/ingest endpoint)

## Build Progress

- [x] **Phase 1:** Core backend — Azure Functions + Azure OpenAI proxy
- [x] **Phase 2:** RAG pipeline — text extraction, chunking, FAISS indexing, rule ingestion
- [ ] **Phase 3:** Compliance engine — PII detection, bias check, safety filter, LLM-as-judge
- [ ] **Phase 4:** Metrics & audit API
- [ ] **Phase 5:** React/TypeScript dashboard
- [ ] **Phase 6:** Docker + deploy

## License

MIT
