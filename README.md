# Podcast Generator

Generates personalized news podcasts on a schedule based on user interests.

## Quick start

\```bash
cp .env.example .env  # fill in API keys
docker compose up -d  # postgres + redis + api + worker
cd apps/web && npm install && npm run dev
\```

Web UI: http://localhost:5173
API docs: http://localhost:8000/docs
Admin dashboard: http://localhost:5173/admin

## Architecture

See [solution.md](./solution.md) for the full write-up.

## Project layout

- `packages/pipeline/` — core generation logic (fetch → rank → script → TTS)
- `apps/backend/` — FastAPI + Celery worker
- `apps/frontend/` — React frontend