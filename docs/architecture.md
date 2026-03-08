# PaperMind Architecture Overview

## Overview

PaperMind is a Multi-Agent Research Intelligence Platform where users upload research papers and the system processes them with AI agents for ingestion, embeddings, clustering, and RAG-powered question answering.

## Milestone 0 – Foundation

This milestone establishes the monorepo structure and local development environment.

## Tech Stack

| Layer        | Technology   | Purpose                                  |
| ------------ | ------------ | ---------------------------------------- |
| Frontend     | Next.js      | React app with TypeScript                |
| Backend API  | Flask        | REST API                                 |
| Database     | PostgreSQL   | Relational data + pgvector for embeddings |
| Cache/Broker | Redis        | Caching, Celery message broker           |
| Background   | Celery       | Async job processing                     |
| Containers   | Docker       | Local & deployment orchestration         |

## Monorepo Structure

```
/
├── frontend/          # Next.js app
├── backend/           # Flask API
├── infra/             # Docker & deployment configs
├── docs/              # Architecture & design notes
├── docker-compose.yml
└── .env.example
```

## Services

| Service   | Port | Description                    |
| --------- | ---- | ------------------------------ |
| Frontend  | 3000 | Next.js web app                |
| Backend   | 5000 | Flask REST API                 |
| PostgreSQL| 5432 | Primary database (with pgvector) |
| Redis     | 6379 | Cache & Celery broker          |

## API Endpoints

- `GET /healthz` – Liveness check, returns `{"status": "ok"}`
- `GET /readyz` – Readiness check; verifies PostgreSQL and Redis connectivity, returns 503 if either fails

## Future Milestones

- **Milestone 1**: Paper upload & ingestion pipeline
- **Milestone 2**: Embeddings & vector store (pgvector)
- **Milestone 3**: Clustering & topic modeling
- **Milestone 4**: RAG pipeline & question answering
- **Milestone 5**: CI/CD with GitHub Actions
