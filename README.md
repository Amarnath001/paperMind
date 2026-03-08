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

## License

Private
