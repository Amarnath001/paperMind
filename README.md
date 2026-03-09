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
