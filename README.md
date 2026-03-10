# PaperMind

Multi-Agent Research Intelligence Platform for processing research papers with AI agents (ingestion, embeddings, clustering, and RAG).

## Tech Stack

- **Frontend**: Next.js (TypeScript)
- **Backend**: Flask API
- **Database**: PostgreSQL + pgvector
- **Cache / Message Broker**: Redis
- **Background Jobs**: Celery
- **Containerization**: Docker

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

1. **Clone and enter the repo**

   ```bash
   cd paperMind
   ```

2. **Create environment file**

   ```bash
   cp .env.example .env
   ```

   Add `OPENAI_API_KEY` to `.env` when ready for AI features.

3. **Run with Docker Compose**

   ```bash
   make up
   ```

   Or use `docker compose up --build` directly. Other useful commands:
   - `make down` – stop and remove containers
   - `make logs` – follow container logs
   - `make restart` – stop, rebuild, and start

4. **Access the app**

   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend health: [http://localhost:5000/healthz](http://localhost:5000/healthz)
   - Backend readiness: [http://localhost:5000/readyz](http://localhost:5000/readyz) (checks Postgres & Redis)

## Project Structure

```
/
├── frontend/          # Next.js TypeScript app
├── backend/           # Flask API
├── infra/             # Docker & deployment configs
├── docs/              # Architecture notes
├── docker-compose.yml
└── .env.example
```

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/papermind
export REDIS_URL=redis://localhost:6379/0
python run.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Ensure PostgreSQL and Redis are running (e.g. via `docker compose up postgres redis -d`).

## API

- `GET /healthz` – Returns `{"status": "ok"}` (liveness)
- `GET /readyz` – Returns readiness status; checks PostgreSQL and Redis. Returns 503 if either is unreachable.

## Milestone 1 – Core Application

This milestone introduces the core application layer:

- **Authentication** – Email/password signup & login with bcrypt-hashed passwords and JWT-based auth (`/auth/signup`, `/auth/login`, `/auth/me`).
- **Workspaces** – Multi-tenant workspaces with membership and roles; endpoints to create and list workspaces and fetch a workspace (`/workspaces`, `/workspaces/:id`).
- **Paper upload** – Authenticated PDF uploads (max 20MB) into workspaces via `/papers/upload`, saving files under the backend `uploads/` directory and recording metadata in PostgreSQL.
- **Library listing** – Workspace-specific library listing via `/papers?workspace_id=...`, returning all papers for a workspace.

## Milestone 2 – Async Ingestion Pipeline

Milestone 2 adds an asynchronous ingestion pipeline and job tracking:

- **Jobs table** – Tracks background jobs (`jobs` table) including type, status (`queued`, `running`, `completed`, `failed`), progress, and errors.
- **Chunks table** – Stores extracted text chunks for each paper (`chunks` table) with `chunk_index`, `text`, and `token_count`.
- **Celery + Redis** – Uses Celery workers with Redis as the broker and result backend for asynchronous processing.
- **PDF extraction** – Extracts text from uploaded PDFs using `pypdf`, then splits text into chunks (~800–1200 characters) with simple paragraph-based chunking.
- **Job-triggered ingestion** – After a successful PDF upload, an `ingestion` job is created and a Celery task processes the paper in the background (updating paper status from `uploaded` → `processing` → `ready` or `failed`).
- **APIs** – New `/jobs` and `/jobs/:id` endpoints expose job metadata, and paper APIs expose processing status for frontend visibility.

## Milestone 3 – Local Embeddings & Semantic Search

Milestone 3 adds native embedding generation and vector search powered by Postgres `pgvector` and Sentence Transformers. Fast, private, zero external AI costs.

- **Vector Storage** – Adds `.embedding vector(384)` columns with `ivfflat` indexes for both `papers` and `chunks` tables.
- **Local Embedding Pipeline** – Uses local, open-source models (default: `BAAI/bge-small-en-v1.5`) via `sentence-transformers`, removing the need for paid external APIs.
- **Chained Jobs** – The ingestion pipeline automatically queues an `embedding` job after chunking, chaining the workflow smoothly: `upload -> ingestion -> chunking -> embedding -> semantic search`.
- **Search APIs** – Exposes two new semantic vector-search endpoints: `/search` (find chunks matching a text query in a workspace) and `/papers/<id>/similar` (find related papers using their cached centroid vector).

## LLM Provider (Gemini)

PaperMind keeps **embeddings local** (Sentence Transformers + pgvector) and uses an external LLM **only for text generation** (answering questions, summarisation, future RAG features).

- **Provider**: Gemini (via the `google-generativeai` Python SDK).
- **Usage**: LLMs are wrapped by `LLMService` in `backend/app/services/llm_service.py`, which exposes a simple `generate_text(prompt)` API and a `generate_answer(question, context_chunks)` helper for RAG-style prompts.
- **Model**: Default model is `gemini-1.5-flash` (configurable via `GEMINI_MODEL`).
- **Configuration**:
  - Set `GEMINI_API_KEY` in your `.env` (get a key from [Google AI Studio](https://ai.google.dev/)).
  - Optional: override `LLM_PROVIDER` (currently only `"gemini"` is supported) or `GEMINI_MODEL`.

This prepares the system for Milestone 4 RAG features, where retrieved chunks from pgvector search will be passed into Gemini for high-quality answer generation.

## Milestone 4 – RAG Chat with Citations

Milestone 4 adds a retrieval-augmented chat experience over workspace libraries:

- **Conversation storage** – New `conversations` and `messages` tables track chat sessions, participants, and message history (including JSONB `citations` on assistant messages).
- **Retrieval service** – A dedicated retrieval layer uses local embeddings + pgvector (`chunks.embedding`) to fetch the most relevant chunks for a question, scoped to a workspace (and optionally a single paper).
- **RAG answers with Gemini** – The `LLMService` uses Gemini to generate grounded answers from retrieved chunks via `generate_answer_with_citations`, returning both an answer and structured citation metadata.
- **Chat APIs** – New `/chat` endpoints:
  - `POST /chat/conversations` – create a workspace-scoped conversation.
  - `GET /chat/conversations?workspace_id=...` – list conversations in a workspace.
  - `GET /chat/conversations/<conversation_id>/messages` – fetch message history.
  - `POST /chat/ask` – ask a question within a conversation, run retrieval, generate an answer with citations, and persist both user and assistant messages.
- **Workspace & paper scoping** – All chat and retrieval operations enforce workspace membership, and `POST /chat/ask` can optionally restrict retrieval to a single paper via `paper_id`.
- **Frontend chat UI** – A simple chat interface at `/workspace/[id]/chat` shows conversations, message history, and assistant answers with inline citations (paper title, chunk index, and labels like `[1]`, `[2]`).

The full pipeline is now:

`upload → ingestion → chunking → embedding → retrieval → Gemini answer (with citations)`.

For **new databases**, the schema is created via `backend/db/schema.sql` on first container startup.

For **existing local databases**, you can either:

- Reset the Postgres volume and re-run initialization:

  ```bash
  docker compose down -v
  docker compose up --build
  ```

- Or apply the Milestone 2 migration SQL manually:

  ```bash
  # From the project root, with Postgres running
  docker compose exec postgres psql -U postgres -d papermind -f /docker-entrypoint-initdb.d/schema.sql
  docker compose exec postgres psql -U postgres -d papermind -f /path/to/backend/db/migrations/002_milestone2.sql
  docker compose exec postgres psql -U postgres -d papermind -f /path/to/backend/db/migrations/003_milestone3.sql
  ```

### Running the Celery worker

The Celery worker is defined as a separate service in `docker-compose.yml` and is started automatically with:

```bash
docker compose up --build
```

The worker shares the same code and environment as the backend API and mounts the same `uploads` volume so that uploaded PDFs are available during ingestion.

## Database Initialization

When you run:

```bash
docker compose up --build
```

the PostgreSQL container automatically runs the schema defined in:

- `backend/db/schema.sql`

This uses Postgres' standard entrypoint mechanism by mounting the file into `/docker-entrypoint-initdb.d/schema.sql`. The script is only executed on **first initialization** of the `postgres_data` volume; subsequent `docker compose up` runs will not re-apply the schema.

If you want to reset the database state and re-run schema initialization (for example during early development), you can remove the volume:

```bash
docker compose down -v
```

Then start the stack again:

```bash
docker compose up --build
```

## License

Private
