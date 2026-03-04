# SafeGen — Architecture

## System Design

SafeGen is a **serverless middleware** that sits between client applications and Azure OpenAI. It uses a RAG-based compliance engine to validate LLM outputs against dynamically loaded policy documents.

### Design Principles

1. **Serverless-first** — Azure Functions for zero-ops scaling
2. **Policy-as-data** — Compliance rules are documents, not code; update rules without redeployment
3. **Audit everything** — Every request/response pair is logged for regulatory compliance
4. **Separation of concerns** — Validation logic is decoupled from LLM interaction

## Folder Structure

> ✅ = implemented and tested | 🔲 = planned

```
safegen/
├── backend/
│   ├── function_app.py              # ✅ Azure Functions app entry point (v2 blueprint model)
│   ├── requirements.txt             # ✅ All dependencies
│   ├── host.json                    # ✅ Azure Functions host config
│   ├── local.settings.example.json  # ✅ Template for local settings
│   ├── .funcignore                  # ✅ Azure Functions deploy ignore
│   ├── pytest.ini                   # ✅ Test configuration
│   │
│   ├── functions/                   # HTTP trigger functions (Blueprint pattern)
│   │   ├── __init__.py              # ✅
│   │   ├── validate.py              # ✅ POST /api/validate — LLM proxy (Phase 3: + compliance)
│   │   ├── ingest_rules.py          # ✅ POST /api/rules/ingest — upload rule docs (file + JSON)
│   │   ├── list_rules.py            # ✅ GET /api/rules — list active rules with previews
│   │   ├── audit.py                 # 🔲 GET /api/audit — retrieve audit logs (Phase 4)
│   │   └── metrics.py               # 🔲 GET /api/metrics — dashboard data (Phase 4)
│   │
│   ├── core/                        # Business logic (no Azure Functions dependencies)
│   │   ├── __init__.py              # ✅
│   │   ├── models.py                # ✅ Pydantic models: ValidateRequest/Response, ComplianceResult, ValidationFlag
│   │   ├── openai_client.py         # ✅ Azure OpenAI wrapper with GenerationResult dataclass
│   │   ├── rag_pipeline.py          # ✅ Text extraction, chunking, HF embeddings, FAISS index
│   │   ├── blob_storage.py          # ✅ Azure Blob Storage CRUD with BlobMetadata
│   │   ├── compliance_engine.py     # 🔲 Rule evaluation & scoring orchestrator (Phase 3)
│   │   └── validators.py            # 🔲 PII detection, bias checks, safety filters (Phase 3)
│   │
│   └── tests/                       # 51 tests, all passing
│       ├── __init__.py              # ✅
│       ├── conftest.py              # ✅ Shared fixtures (mock_env, mock_openai_client, etc.)
│       ├── test_models.py           # ✅ 12 tests — Pydantic model validation
│       ├── test_openai_client.py    # ✅ 7 tests — Azure OpenAI wrapper
│       ├── test_validate.py         # ✅ 7 tests — /api/validate endpoint
│       ├── test_rag_pipeline.py     # ✅ 16 tests — extract, chunk, embed, FAISS, semantic search
│       ├── test_ingest_rules.py     # ✅ 4 tests — /api/rules/ingest endpoint
│       ├── test_compliance_engine.py # 🔲 Phase 3
│       └── test_validators.py       # 🔲 Phase 3
│
├── frontend/                        # 🔲 Phase 5 — React/TypeScript dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── layout/              # Sidebar, Header
│       │   ├── dashboard/           # ComplianceRateCard, TrendChart, RuleHitChart
│       │   ├── rules/               # RuleUploader, RuleList
│       │   └── audit/               # AuditLogTable, AuditDetail
│       ├── pages/                   # DashboardPage, RulesPage, AuditPage
│       ├── services/api.ts          # Typed API client
│       └── types/index.ts           # Shared TypeScript types
│
├── rules/                           # ✅ Sample compliance rule documents
│   ├── gdpr_content_rules.md        # ✅ 5 GDPR rules (PII, data minimization, consent, etc.)
│   ├── bias_detection_policy.md     # ✅ 5 bias rules (gender, racial, accessibility, etc.)
│   └── pii_handling_rules.md        # ✅ 4 PII rules (detection categories, masking, etc.)
│
├── docker-compose.yml               # 🔲 Phase 5
├── Dockerfile.backend               # 🔲 Phase 5
├── Dockerfile.frontend              # 🔲 Phase 5
├── .gitignore                       # ✅
├── .env.example                     # ✅
└── README.md                        # ✅
```

## Data Flow

### Validation Pipeline (`POST /api/validate`)

```
1. Client sends { prompt, context?, rules_category? }
2. Azure Function receives request
3. Call Azure OpenAI with prompt → get raw LLM response
4. Compliance Engine:
   a. Retrieve relevant rules from FAISS index (RAG)
   b. Run PII detector on response
   c. Run bias checker on response
   d. Run safety filter on response
   e. Score response against retrieved rules (LLM-as-judge)
   f. Return { passed: bool, score: float, flags: [], validated_response }
5. Log full request/response/validation to Azure Blob Storage
6. Return validated response to client (or rejection with reasons)
```

### Rule Ingestion (`POST /api/rules/ingest`)

```
1. Upload PDF/DOCX/MD compliance document
2. Store original in Azure Blob Storage
3. Extract text, chunk into ~500 token segments
4. Generate embeddings (Hugging Face all-MiniLM-L6-v2)
5. Add to FAISS index
6. Return { rule_id, chunk_count, status }
```

## Key Technical Decisions

| Decision           | Choice                          | Rationale                                                          |
| ------------------ | ------------------------------- | ------------------------------------------------------------------ |
| Serverless runtime | Azure Functions v2 (Python)     | Matches JD requirement; scales to zero; pay-per-use                |
| Vector store       | FAISS (in-memory)               | Fast, no infrastructure; sufficient for rule-set sizes (<10k docs) |
| Embeddings         | Hugging Face `all-MiniLM-L6-v2` | Free, fast, good quality for semantic search                       |
| Audit storage      | Azure Blob Storage (JSON)       | Cost-effective append-only log; easy to query with Azure tools     |
| Frontend           | React + Vite + Tailwind         | Fast dev cycle; matches JD stack                                   |
| Compliance scoring | LLM-as-judge pattern            | Azure OpenAI evaluates response against retrieved rules            |

## Compliance Engine Detail

The engine runs 4 validation layers in sequence:

1. **PII Detection** — Regex + NER-based detection of emails, phones, SSNs, credit cards
2. **Bias Check** — Keyword + sentiment analysis for discriminatory language
3. **Safety Filter** — Azure OpenAI content safety categories (hate, violence, self-harm, sexual)
4. **Rule Compliance** — RAG retrieves relevant policy chunks, LLM-as-judge scores adherence

Each layer returns a `ValidationFlag` (implemented in `core/models.py`):

```python
class ValidationFlag(BaseModel):
    layer: str           # "pii" | "bias" | "safety" | "compliance"
    severity: str        # "info" | "warning" | "critical"
    message: str         # Human-readable flag description
    details: dict        # Layer-specific metadata

class ComplianceResult(BaseModel):
    passed: bool         # Whether the response passed all checks
    score: float         # 0.0 to 1.0 overall compliance score
    flags: list[ValidationFlag]
    layers_run: list[str]  # Which validation layers were executed
```
