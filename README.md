# Podcast Generator

Personalized news podcasts on a schedule. Pick what you care about, get an episode delivered when you want it.

## Quick start

```bash
cp .env.example .env       # add OPENAI_API_KEY, ELEVENLABS_API_KEY, NEWSAPI_KEY, FIRECRAWL_API_KEY
docker compose up
```

Wait for the seven containers to be healthy (~30s on first run, after the build).

- **Web UI** — http://localhost:5173
- **API docs** — http://localhost:8000/docs
- **Admin dashboard** — http://localhost:5173/admin

Open Preferences, pick a few topics and a schedule, click *Save*. Then either hit *Generate now* in Library or wait for the scheduler to fire.

## Architecture

See [solution.md](./solution.md) for the full write-up, architecture diagram, design decisions, trade-offs and known limitations.

## Project layout

```text
podcast-generator/
├── packages/pipeline/      # Core generation: fetch → rank → script → TTS → stitch
├── apps/backend/           # FastAPI + Celery worker + Celery Beat scheduler
├── apps/frontend/          # React + Vite (Library, Preferences, Admin)
└── docker-compose.yml      # postgres · redis · migrate · api · worker · beat · frontend
```

## Stack

Python 3.12 · FastAPI · Celery · SQLAlchemy 2.0 · Postgres 16 · Redis 7 · React 18 · TypeScript · Tailwind · OpenAI · ElevenLabs · Firecrawl
