# Policy & Knowledge Assistant (RAG)

An enterprise-grade Retrieval-Augmented Generation (RAG) assistant for company HR, IT, and leave policy documents. Built with FastAPI, PostgreSQL + pgvector, Redis background job queues, and a premium React B2B SaaS frontend.

---

## System Architecture

```
                                +-----------------------------+
                                |  React (Vite) Single Page   |
                                |   Admin & Employee Client   |
                                +--------------+--------------+
                                               |
                                               | HTTP / REST (Bearer JWT)
                                               v
                                +-----------------------------+
                                |     FastAPI Server (v1)     |
                                |  Auth, Ingestion, Retrieval |
                                +-------+--------------+------+
                                        |              |
                      pgvector cosine   |              | Enqueue jobs
                         search         v              v
                               +---------------+ +---------------+
                               |  PostgreSQL   | |     Redis     |
                               |  + pgvector   | |   Job Queue   |
                               +---------------+ +-------+-------+
                                                         |
                                                         | Dequeue & process
                                                         v
                                                 +---------------+
                                                 |  Background   |
                                                 |  Worker       |
                                                 +---------------+
```

---

## Technology Stack

### Frontend
- **Framework**: React 18, Vite (vanilla JavaScript, no TypeScript)
- **Styling**: Vanilla CSS design system with custom properties (deep navy `#090d16`/`#0f172a`, slate cards, indigo `#6366f1` accents)
- **Icons**: Zero-dependency, accessible handcrafted SVG icon library
- **State & Auth**: React Context API (`AuthContext`), persistent bearer token storage, 401 interceptor
- **Architecture**: Modular layout with component separation (`admin`, `auth`, `chat`, `common`, `layout`)

### Backend
- **Core**: Python 3.12, FastAPI, Pydantic v2
- **Database & ORM**: PostgreSQL 16 with `pgvector` (`Vector(1536)`), SQLAlchemy 2.0 (async & sync engines), Alembic migrations
- **Queue & Cache**: Redis 7 for asynchronous document processing and retry management
- **Authentication**: JWT (JSON Web Tokens) with `admin` and `employee` roles, bcrypt password hashing
- **RAG Services**: Custom PDF/DOCX/TXT text extraction, token-aware chunking, cosine vector similarity retrieval, prompt-sandboxed grounded question answering, citation verification
- **Providers**: Pluggable `EmbeddingProvider` and `LLMProvider` abstractions (Mock, OpenAI, and Gemini)
- **Testing**: `pytest`, `pytest-asyncio`, in-memory test fixtures, live pgvector container integration tests
- **Operations**: Docker, Docker Compose, structured JSON logging

---

## Directory Structure

```
.
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py       # DB sessions, JWT extraction, role-based dependencies
│   │   │   └── routes/       # /health, /ready, /auth, /documents, /jobs, /chat
│   │   ├── core/             # Structured JSON logging, password hashing, JWT
│   │   ├── evaluation/       # Benchmark dataset (4 docs, 28 queries) and RAGEvaluator
│   │   ├── models/           # SQLAlchemy ORM models (users, docs, chunks, jobs, chat_logs)
│   │   ├── providers/        # LLM and Embedding provider interfaces & adapters
│   │   ├── schemas/          # Pydantic request/response validation schemas
│   │   ├── services/         # Text extraction, chunking, retrieval, grounded answering, Redis queue
│   │   ├── cli.py            # CLI management commands (create-admin, create-user)
│   │   ├── config.py         # Application settings loaded from .env
│   │   ├── database.py       # Async & sync SQLAlchemy engines and sessions
│   │   ├── main.py           # FastAPI entrypoint, lifespan, CORS, error handling
│   │   └── worker.py         # Redis background worker entrypoint
│   ├── scripts/
│   │   └── run_evaluation.py # Standalone RAG evaluation benchmark CLI runner
│   ├── tests/                # 68 unit/integration tests (retrieval, answering, chat API, evaluation)
│   ├── Dockerfile            # Container build for API and Worker
│   ├── requirements.txt      # Pinned Python dependencies
│   ├── .env.example          # Sample environment configuration
│   └── pytest.ini            # Pytest configuration
├── frontend/
│   ├── src/
│   │   ├── api/              # Centralized API client (auth, documents, jobs, chat)
│   │   │   ├── client.js     # Base fetch wrapper, bearer token injection, 401 interceptor
│   │   │   ├── auth.js       # Login, profile (/auth/me), logout
│   │   │   ├── documents.js  # Document upload, listing, chunks, deletion
│   │   │   ├── jobs.js       # Ingestion job status polling
│   │   │   └── chat.js       # Policy question answering and query audit logs
│   │   ├── components/
│   │   │   ├── admin/        # AdminDashboard, DocumentUpload, DocumentList, ChunksModal
│   │   │   ├── auth/         # LoginForm with quick-fill demo accounts
│   │   │   ├── chat/         # ChatInterface, ChatComposer, ChatMessage, CitationCard, EmptyState, ChatHistoryDrawer
│   │   │   ├── common/       # SVG Icons, Button, StatusBadge, RoleBadge, Modal dialog
│   │   │   └── layout/       # AppHeader (responsive desktop + mobile drawer), Shell
│   │   ├── context/          # AuthContext (session hydration, login, logout, role state)
│   │   ├── App.jsx           # Root app view & role-guarded tab navigation
│   │   ├── App.css           # Premium B2B SaaS styles, responsive grid, animations
│   │   ├── index.css         # Design tokens, CSS variables, typography, reset
│   │   └── main.jsx          # React DOM entrypoint
│   ├── package.json          # Vite and React dependencies
│   └── vite.config.js        # Vite dev proxy configuration (/api -> http://localhost:8000)
├── docker-compose.yml        # Orchestrates db (pgvector), redis, api, and worker
├── .gitignore
├── pytest.ini                # Root pytest configuration
└── README.md
```

---

## Frontend Architecture & User Experience

The frontend is crafted as a high-end B2B SaaS application tailored for enterprise knowledge management.

### Design System & Visual Foundation
- **Color Palette**: Deep slate and navy foundations (`#090d16` canvas, `#0f172a` surfaces, `#1e293b` borders) accented with electric indigo (`#6366f1`) and vibrant state colors (emerald for completed/high confidence, amber for processing/abstention, rose for errors/failed jobs).
- **Typography**: Inter for crisp UI text and JetBrains Mono for metadata, token counts, and chunk IDs.
- **Responsiveness**: Fluid layout scaling from mobile viewports (375px) to ultra-wide displays with zero horizontal overflow.
- **Accessibility & Motion**: Semantic HTML, distinct keyboard focus rings (`:focus-visible`), and `@media (prefers-reduced-motion: reduce)` support.

### Main Screens

#### 1. Authentication Screen (`LoginForm.jsx`)
- Complete email and password fields with client-side validation.
- Password reveal toggle for usability.
- Server error alerts mapping backend Pydantic/FastAPI validation messages.
- Convenient **Quick Demo Credentials** chips for instant login as Admin (`admin@example.com` / `Admin@ChangeMe123!`) or Employee (`employee@example.com` / `EmployeePass123!`).

#### 2. Admin Dashboard (`AdminDashboard.jsx`)
- **Metric Cards**: Dynamic KPI counters for total uploaded documents, completed ingestions, and failed jobs derived directly from real backend data.
- **Document Ingestion (`DocumentUpload.jsx`)**: Drag-and-drop file uploader supporting `.pdf`, `.docx`, and `.txt` up to 15MB with live upload status and file-type validation.
- **Document Registry (`DocumentList.jsx`)**: Comprehensive data table displaying file format badges, upload timestamp, chunk count, file size, status badges, and actions.
- **Chunk Inspector Modal (`ChunksModal.jsx`)**: Admin capability to inspect extracted passage chunks, section headers, page numbers, character/token counts, and `Vector(1536)` embedding status.
- **Delete Confirmation Modal (`Modal.jsx`)**: Safeguards against accidental document deletion with a confirmation dialog.
- **Smart Polling**: Automatically polls background ingestion jobs every 3 seconds while documents are in `processing` or `queued` state, and immediately tears down the interval timer when jobs complete or fail.

#### 3. Employee Chat Interface (`ChatInterface.jsx`)
- **Welcoming Empty State (`EmptyState.jsx`)**: Displays interactive suggestion cards for common policy queries (PTO policies, remote work stipend, password rotation, travel per diem, and pet insurance abstention check).
- **Message Composer (`ChatComposer.jsx`)**: Multiline auto-expanding textarea, Enter-to-submit (Shift+Enter for newline), 1000-character counter, and send state indicators.
- **Grounded Answer Rendering (`ChatMessage.jsx`)**: Safe markdown formatting for lists and paragraphs without raw `dangerouslySetInnerHTML`.
- **Distinct Abstention Callout**: When the system cannot find sufficient evidence, it highlights the answer in an amber badge with a shield alert:
  > *"I don't know based on the provided documents."*
- **Expandable Evidence Citations (`CitationCard.jsx`)**: Collapsible citation cards exposing source document title, filename, page/section header, snippet text, and verified chunk UUID.
- **Audit History Drawer (`ChatHistoryDrawer.jsx`)**: Allows employees to view their own past queries, timestamps, confidence scores, and answer snippets directly from `GET /api/v1/chat/logs`.

### Centralized API Client & Security Analysis

The API layer is centralized in `frontend/src/api/client.js`:
- Automatically injects `Authorization: Bearer <token>` into authenticated requests.
- Intercepts 401 Unauthorized responses to trigger an automatic session logout and redirect.
- Normalizes server errors (including Pydantic 422 arrays) into readable error strings.

#### Token Storage Security Trade-offs
- **Current Implementation**: The JWT token is stored in browser `localStorage` to provide smooth session persistence across page refreshes and clean REST client compatibility with FastAPI's OAuth2 HTTPBearer schema.
- **Security Analysis**: While `localStorage` is vulnerable to Cross-Site Scripting (XSS) if untrusted scripts run, this risk is mitigated here by:
  - Strict text escaping (no raw HTML rendering from LLM outputs).
  - Zero external CDN script tags or third-party tracking scripts.
  - No secret keys or environment credentials in client bundles.
- **Enterprise Hardening Path**: For strict compliance environments, the backend can be configured to issue `HttpOnly`, `Secure`, `SameSite=Strict` cookies, preventing JavaScript access to tokens entirely.

---

## Retrieval & Grounded Answering Pipeline

### 1. Vector Retrieval (`app.services.retrieval`)
- **Input Validation**: Enforces non-empty strings and a configurable maximum length (`MAX_QUESTION_LENGTH=1000`).
- **Embedding Contract**: Generates query vector and validates dimension matches `EMBEDDING_DIMENSION=1536`.
- **pgvector Cosine Search**: Uses PostgreSQL's native `<=>` cosine distance operator in SQL. Cosine similarity is computed as $s = 1.0 - d$.
- **Database Filtering**: Filters out uncompleted or failed documents (`Document.status == 'completed'`) and applies the threshold in SQL: `cosine_dist <= (1.0 - threshold)`.
- **Top-K Retrieval**: Returns top-k passages with real chunk IDs, document metadata, page numbers, and similarity scores.

### 2. Prompt Sandboxing & Grounded Answering (`app.services.answering`)
- **Immediate Abstention**: If retrieval yields 0 chunks meeting the similarity threshold, the system immediately returns:
  > *"I don't know based on the provided documents."*
  (No LLM inference calls are dispatched, eliminating hallucination risks and saving costs).
- **Prompt Sandboxing**: Evidence passages are encased inside strict delimiter boundaries (`--- EVIDENCE EXCERPTS BEGIN ---` / `--- EVIDENCE EXCERPTS END ---`) and treated as untrusted data to defend against prompt injection.
- **Model Abstention**: If the LLM generates an abstention or cannot find the answer, the response normalizes to the canonical abstention message.

### 3. Citation Integrity & Provenance Verification
- **System-Controlled Metadata**: Document titles, filenames, page numbers, and section titles are resolved strictly from database records, never from model hallucinations.
- **Citation Extraction**: The model is instructed to cite chunk IDs in brackets (e.g., `[Chunk <uuid>]`).
- **ID Validation**: Every cited UUID is cross-referenced against the set of actually retrieved chunks. Fabricated or unretrieved chunk IDs are discarded.
- **Fail-Safe Abstention**: If an answer is generated but none of its citations can be validated against retrieved sources, the system abstains rather than returning misleading citations.
- **Audit Logging**: Every query, retrieved chunk IDs, answer, confidence score, and latency (ms) are recorded in the `chat_logs` table.

---

## API Endpoints Reference

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/health` | Public | Liveness health check |
| `GET` | `/ready` | Public | Readiness check (validates PostgreSQL & Redis) |
| `POST` | `/api/v1/auth/login` | Public | Authenticates credentials, returns JWT bearer token |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieves current user profile |
| `POST` | `/api/v1/documents/upload` | Admin only | Uploads PDF, DOCX, TXT; deduplicates and enqueues job |
| `GET` | `/api/v1/documents` | Authenticated | Lists uploaded policy documents |
| `GET` | `/api/v1/documents/{id}` | Authenticated | Retrieves document details and status |
| `GET` | `/api/v1/documents/{id}/chunks` | Authenticated | Inspects chunk texts, page numbers, and vector status |
| `DELETE`| `/api/v1/documents/{id}` | Admin only | Cascades document, chunks, jobs, and deletes file |
| `GET` | `/api/v1/jobs/{id}` | Authenticated | Retrieves ingestion job status and retry history |
| `POST` | `/api/v1/chat/query` | Authenticated | Answers employee policy queries with citations & logs audit |
| `GET` | `/api/v1/chat/logs` | Authenticated | Lists query audit history (Admin: all, Employee: own) |

---

## RAG Evaluation Benchmark

The repository includes an offline evaluation harness (`backend/scripts/run_evaluation.py`) that tests retrieval quality and abstention behavior across chunking strategies.

### Benchmark Dataset
- **Corpus**: 4 synthetic policy documents (`remote_work_policy`, `leave_and_time_off_policy`, `it_security_and_device_policy`, `travel_and_expense_policy`).
- **Question Set**: 28 benchmark questions covering:
  - 14 Direct answerable questions with known single-section sources.
  - 5 Cross-section / cross-document synthesis questions.
  - 4 Distractor / potentially confusing policy questions.
  - 5 Explicitly unanswerable questions (e.g., pet insurance, office dogs, car leases).

### Measured Evaluation Results (Top-k=3)

| Configuration | Approx Tokens | Chars (Size/Overlap) | Hit-Rate@3 | Fact Coverage | Abstention Acc. | Chunks/Doc | Latency |
|---|---|---|---|---|---|---|---|
| **Fine-Grained (Small)** | ~200 tokens | 800 / 100 | **100.0%** | 87.0% | **100.0%** | 4.0 | 56 ms |
| **Balanced (Medium)** | ~500 tokens | 2000 / 200 | **100.0%** | **91.3%** | **100.0%** | 1.8 | 26 ms |
| **Coarse-Grained (Large)**| ~800 tokens | 3200 / 400 | **100.0%** | **91.3%** | **100.0%** | 1.0 | 16 ms |

**Selection Rationale**: The **Balanced (~500 tokens / 2000 chars)** configuration is configured as default because it achieves optimal factual coverage (91.3%) and 100% retrieval hit-rate while capturing full policy clauses and approval procedures in single chunks.

Run the evaluation benchmark:
```bash
python backend/scripts/run_evaluation.py
```

---

## Local Development & Setup

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Docker and Docker Compose

### 1. Start Infrastructure (PostgreSQL + pgvector & Redis)
```bash
docker compose up -d db redis
```

### 2. Backend Setup & Database Migrations
```bash
# Create and activate virtual environment
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run Alembic migrations
alembic upgrade head
```

### 3. Provision Initial Users
```bash
# Seed initial admin user
python -m app.cli create-admin --email admin@example.com --password "Admin@ChangeMe123!" --full-name "System Administrator"

# Seed initial employee user
python -m app.cli create-user --email employee@example.com --password "EmployeePass123!" --full-name "Jane Employee" --role employee
```

### 4. Start Backend Services
```bash
# In terminal 1: Run the FastAPI API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In terminal 2: Run the Redis background worker
python -m app.worker
```

### 5. Start Frontend Development Server
```bash
# In terminal 3: Start Vite development server
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser. The Vite development server automatically proxies `/api` calls to `http://localhost:8000`.

---

## Configuration Settings (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime environment (`development`, `production`) |
| `SECRET_KEY` | `dev-secret...` | 32+ character secret for JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT token lifetime |
| `EMBEDDING_PROVIDER` | `mock` | `mock`, `openai`, or `gemini` |
| `LLM_PROVIDER` | `mock` | `mock`, `openai`, or `gemini` |
| `EMBEDDING_DIMENSION` | `1536` | Vector dimension (`Vector(1536)`) |
| `TOP_K_RETRIEVAL` | `5` | Maximum passages retrieved per query |
| `MIN_SIMILARITY_THRESHOLD` | `0.5` | Minimum cosine similarity score |
| `MAX_QUESTION_LENGTH` | `1000` | Question character limit |
| `MAX_UPLOAD_SIZE_BYTES` | `15728640` | Maximum file upload size (15 MB) |
| `REDIS_INGESTION_QUEUE` | `policy_rag_ingestion_queue` | Redis queue name |

---

## Actual Verification & Test Results

All verification suites have been executed directly in the repository with the following recorded results:

### 1. Frontend Production Build
```bash
cd frontend && npm run build
```
- **Result**: Built successfully in **416ms** with **0 warnings and 0 errors**.
- **Bundle Output**:
  - `dist/index.html`: `0.41 kB` (gzip: `0.28 kB`)
  - `dist/assets/index-Cj9JmiBv.css`: `33.42 kB` (gzip: `6.34 kB`)
  - `dist/assets/index-D430COTZ.js`: `191.59 kB` (gzip: `58.47 kB`)

### 2. Backend Pytest Suite
```bash
backend/.venv/bin/pytest -v
```
- **Result**: **67 passed, 1 skipped** in 10.08s.
- `test_pgvector_native_cosine_distance_query` skipped as intended when `TEST_POSTGRES_URL` is unset (requires a running live pgvector container).
- All auth, upload, chunking, retrieval, grounded answering, citation verification, and CLI tests passed.

### 3. Docker Compose Validation
```bash
docker compose config
```
- **Result**: Successfully validated service graph (`db`, `redis`, `api`, `worker`) with health checks, persistent volumes, and port forwardings.
