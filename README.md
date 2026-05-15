# Podcast Generator

Personalized news podcasts on a schedule. Pick what you care about, get an episode delivered when you want it.

## Quick start

```bash
cp .env.example .env   # add OPENAI_API_KEY, ELEVENLABS_API_KEY, NEWSAPI_KEY, FIRECRAWL_API_KEY
docker compose up
```

Seven containers spin up (~30s on first run): `postgres`, `redis`, `migrate`, `api`, `worker`, `beat`, `frontend`.

- **Web UI**: http://localhost:5173
- **API docs**: http://localhost:8000/docs
- **Admin dashboard**: http://localhost:5173/admin

Open Preferences, pick topics and a schedule, save. Hit *Generate now* in Library or wait for the scheduler.

## Architecture

![Architecture diagram](./docs/architecture.jpg)

The core generation logic lives in `packages/pipeline/`, a standalone Python package with zero dependencies on FastAPI or Celery. It takes a `PipelineConfig` and returns a `PipelineResult`. Three things call it: the Celery worker, a CLI (`python -m pipeline`), and tests. Keeping it decoupled means the 30–60s generation job never blocks an HTTP request and can be tested without any infra running.

`POST /api/v1/podcasts/generate` inserts a `pending` row, enqueues a Celery task, and returns 202 in ~200ms. The worker runs the pipeline and updates `status` + `stage_progress` via a callback; the frontend polls every 2s. Celery Beat fires `check_user_schedules` every 60s to kick off scheduled generations.

### News pipeline

| Layer | Source | Notes |
|------:|--------|-------|
| 1 | RSS (TechCrunch, BBC, Ars Technica, NPR, CNBC, …) | Free and fast |
| 2 | NewsAPI `/everything` with domain whitelist | Filters out PR sites and job boards |
| 3 | Firecrawl `/scrape` | Runs *after* ranking, only on top-N articles to save credits |

### Ranking

Two-stage scoring: cosine similarity between article embeddings and the user's weighted interest embeddings (with recency decay over 48h), then MMR (λ=0.7) for diversity. Uses `text-embedding-3-small`. Embeddings live on the `Article` object for now; in production they'd go into `pgvector` to avoid re-computing across runs.

### Script generation

GPT-4o-mini with `response_format={"type": "json_schema", "strict": true}`, which guarantees valid JSON with no regex fallbacks. Prompt is example-driven to get a natural voice rather than a news-reader tone.

### Storage

Postgres 16 stores users, preferences, podcasts, segments, and an append-only `events` table (`podcast_requested`, `podcast_completed`, `podcast_failed`, `preferences_updated`). Admin dashboard runs `GROUP BY` queries directly on events (fine at this scale; production would materialize daily aggregates). SQLAlchemy 2.0 async + Alembic for migrations, Redis 7 as Celery broker/backend, audio on a local volume (S3 in production).

## Project layout

```
podcast-generator/
├── packages/pipeline/       # Core logic: fetch → rank → script → TTS → stitch
│   └── pipeline/
│       ├── fetch.py         # RSS + NewsAPI + Firecrawl orchestrator
│       ├── sources/         # one file per source
│       ├── rank.py          # embeddings + cosine + MMR
│       ├── script.py        # GPT structured output
│       ├── tts.py           # ElevenLabs with concurrency cap
│       ├── stitch.py        # pydub concat with pauses
│       └── cli.py           # python -m pipeline
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── routers/     # preferences, podcasts, admin
│   │   │   ├── services/    # business logic
│   │   │   ├── worker/      # Celery app + tasks
│   │   │   ├── models.py    # SQLAlchemy 2.0
│   │   │   ├── schemas.py   # Pydantic in/out
│   │   │   └── config.py    # pydantic-settings
│   │   └── migrations/      # Alembic
│   └── frontend/
│       └── src/
│           ├── api/         # typed clients per resource
│           ├── hooks/       # TanStack Query wrappers
│           ├── pages/       # Library, Preferences, Admin
│           └── components/
└── docker-compose.yml
```

## Stack

**Pipeline:** Python 3.12 · OpenAI SDK · ElevenLabs SDK · httpx · feedparser · trafilatura · pydub · tenacity  
**Backend:** FastAPI · SQLAlchemy 2.0 (async) · Alembic · Celery · psycopg v3 · Pydantic v2  
**Frontend:** Vite · React 18 · TypeScript · TanStack Query · React Router · Tailwind · Recharts  
**Infra:** Postgres 16 · Redis 7 · Docker Compose

## Known limitations

- **Auth:** a demo user is bootstrapped at startup; real auth is a one-afternoon swap in `app/deps.py:get_current_user_id` to parse a JWT.
- **Episode length:** GPT-4o-mini under-budgets long outputs, so a 7-minute target lands at ~5–6 min. Real fix: one LLM call per segment instead of one for the full script (~5x cost).
- **Embedding cache:** article embeddings are recomputed every generation; persisting in `pgvector` would cut cost and unlock cross-user trending topics.
- **Cost telemetry:** `avg_cost` in the admin dashboard is mocked; production would track OpenAI tokens and ElevenLabs characters per run.
- **Pagination:** offset-based works at current volume; keyset pagination needed at tens of thousands of episodes per user.
- **Feedback loop:** per-segment thumbs-up/down as a ranking signal + prompt A/B testing with thumbs-up rate as the metric.
- **Multi-language:** ElevenLabs `eleven_multilingual_v2` already supports it, just needs a language selector and localized prompts.
