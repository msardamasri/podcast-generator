# Personal Podcast Generator

**disclaimer -> this project is part of a take-home assignment**

This app generates personalized news podcasts from a curated set of sources, on a user-configured schedule or on-demand. The main workflow is the following one: pulls news, ranks it against the listener's interests, drafts a script with GPT, synthesizes audio withElevenLabs, and stitches everything into an MP3.

## TL;DR setup

```bash
cp .env.example .env       # add OPENAI_API_KEY, ELEVENLABS_API_KEY, NEWSAPI_KEY, FIRECRAWL_API_KEY
docker compose up
```

Then:

- **Frontend:** http://localhost:5173
- **API + Swagger:** http://localhost:8000/docs
- **Admin metrics:** http://localhost:5173/admin

Configure topics + a schedule under `/preferences`. Click *Generate now* or
wait for the scheduled time (Celery Beat fires automatic generations).

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         React + Vite SPA                                 │
│              preferences  ·  library  ·  admin dashboard                 │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ /api/v1/*
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            FastAPI  (api)                                │
│           thin routers  ·  services  ·  Pydantic schemas                 │
└─────────────┬─────────────────────────────────────────┬──────────────────┘
              │ enqueue                                 │ read / write
              ▼                                         ▼
   ┌─────────────────────┐                ┌──────────────────────────┐
   │  Redis  (broker)    │                │      Postgres 16         │
   └──────────┬──────────┘                │  users · preferences     │
              │                           │  podcasts · segments     │
              ▼                           │  events                  │
   ┌─────────────────────┐                └────────────┬─────────────┘
   │  Celery worker      │ ─────── updates ──────────► │
   │  runs the pipeline  │                             │
   └──────────┬──────────┘                             │
              │                                        │
              ▼                                        │
   ┌─────────────────────┐                             │
   │  Celery Beat        │ ── reads schedules ────────►│
   │  every 60s          │                             │
   └─────────────────────┘                             │

   Pipeline stages (inside the worker process):

   ┌────────┐   ┌────────┐   ┌─────────┐   ┌────────┐   ┌──────┐   ┌────────┐
   │ fetch  │ → │ rank   │ → │ enrich  │ → │ script │ → │ tts  │ → │ stitch │
   └────────┘   └────────┘   └─────────┘   └────────┘   └──────┘   └────────┘
    RSS +        OpenAI        Firecrawl     GPT-4o-      Eleven-    pydub
    NewsAPI      embed +       (top N        mini         Labs       + mp3
                 MMR           only)         JSON         async
```

Seven containers orchestrated by Compose: `postgres`, `redis`, `migrate`
(one-shot), `api`, `worker`, `beat`, `frontend`.

## Key decisions

### Separation: pipeline / api / worker

The core generation logic lives in its own Python package
(`packages/pipeline/`), with zero dependencies on FastAPI, SQLAlchemy or
Celery. It takes a `PipelineConfig` dataclass and returns a `PipelineResult`.
The backend imports it as a local editable install.

Three callers use the same code:

1. The Celery worker (production path)
2. A CLI (`python -m pipeline ...` — useful for ad-hoc generation, prompt
   iteration, debugging)
3. Tests (no infra needed)

This was the first decision and the most important one. Generating a podcast
takes 30–60s; binding that logic to the HTTP layer would have made everything
slower, harder to test, and impossible to schedule. Keeping it in a standalone
package also forced clean boundaries between domain logic and infrastructure.

### Async pipeline, sync worker

The pipeline itself is `async`: `fetch` hits 3 source types in parallel
(RSS feeds via `feedparser`, NewsAPI, Firecrawl), embeddings batch-fan-out to
OpenAI, TTS chunks parallelize with a concurrency cap. This cuts a single run
from ~90s down to ~35–40s on average.

The Celery worker is sync — Celery tasks are sync by convention, and most
worker pools (prefork, gevent) play poorly with native asyncio. We bridge it
with `asyncio.run(...)` inside the task. Imperfect but pragmatic.

### News pipeline: 3 sources, layered

| Layer | Source | Role |
|------:|--------|------|
| 1 | RSS feeds (TechCrunch, BBC, Ars Technica, NPR, CNBC, …) | Free, fast, predictable. Default backbone. |
| 2 | NewsAPI `/everything` with **domain whitelist** | Topical breadth that RSS misses. The whitelist is critical — without it you get junk PR sites and job-board scraping. |
| 3 | Firecrawl `/scrape` | Used *after ranking*, only on top-N articles, to upgrade snippet content to full text before the LLM sees it. |

Tier 3 runs after ranking on purpose — scraping every article would waste
credits on the 90% we discard. Tiered fallback also means failures degrade
gracefully: if NewsAPI is down (a 401 we saw repeatedly during dev), RSS
alone returns ~80 candidates.

### Ranking: embeddings + MMR

Two-stage scoring:

1. **Relevance**: cosine similarity between each article's embedding and the
   weighted sum of the user's interest embeddings, minus a soft penalty for
   similarity to exclusions. Plus a recency bonus that decays over 48h.
2. **MMR** (Maximal Marginal Relevance) for diversity. Without it, when 5
   outlets cover the same Mira Murati announcement, the ranker picks all 5.
   MMR with λ=0.7 picks the best one and moves on to the next distinct story.

`text-embedding-3-small` (1536-d, ~$0.0003/run). Embeddings are stored on the
`Article` object — in production we'd persist them in `pgvector` so the same
article doesn't get re-embedded across users.

### Script generation: structured output + iterative prompting

GPT-4o-mini with `response_format={"type": "json_schema", "strict": true}` —
the model is *guaranteed* to return valid JSON matching our schema. No
try/except, no regex, no surprise.

The prompt went through three iterations driven by reading actual output
critically:

- **v1** (instructions only): generic AI clichés ("let's get into it",
  rhetorical questions, vague summaries).
- **v2** (banned-phrases list): improved but still bland — negative rules
  don't teach the model what *good* looks like.
- **v3** (positive Good/Bad examples for hooks, transitions, and takes): the
  output started sounding like a real host. This is the version that ships.

The prompt is treated as part of the codebase — committed, reviewed,
defended.

### Async with Celery + Beat

Generating a podcast is a 30–60s job. Doing it inside an HTTP request would
mean:

- Browser timeouts
- No retries
- No telemetry
- Workers tied up serving long requests

So the `POST /api/v1/podcasts/generate` endpoint:

1. Inserts a `pending` Podcast row
2. Enqueues a Celery task
3. Returns 202 with `podcast_id` in ~200ms

The worker runs the pipeline, updates the row's `status` and `stage_progress`
through the pipeline stages via a callback, and the frontend polls
`GET /podcasts/{id}` every 2s. Celery Beat fires `check_user_schedules` every
60s; it walks active schedules, respects timezones, and enqueues generations
for users whose time has come — idempotent against duplicate same-day runs.

### Telemetry: an append-only events table

Every important action is logged into `events`: `podcast_requested`,
`podcast_completed`, `podcast_failed`, `preferences_updated`, with a
`trigger` property distinguishing manual vs. scheduled generations. The admin
dashboard queries this table directly with SQL aggregations — no separate
analytics pipeline, no pre-computed roll-ups. At take-home scale (thousands
of rows) plain `GROUP BY` is instant; for production you'd materialize daily
aggregates.

### Storage

| Concern | Choice | Why |
|---------|--------|-----|
| Relational | Postgres 16 | JSONB for interests/schedule, FK cascades, mature |
| ORM | SQLAlchemy 2.0 (typed) | First-class async, typed `Mapped[...]` columns |
| Migrations | Alembic | Versioned, reversible, autogenerate from models |
| Cache + queue | Redis 7 | Celery broker + result backend in one |
| Audio | Local volume (`audio_data`) | Fine for take-home; S3 in production |

Migrations run in a dedicated `migrate` service before `api` and `worker`
start. Cleaner than embedding migration logic in app startup (which doesn't
work with multiple replicas).

## What lives where

```
podcast-generator/
├── packages/
│   └── pipeline/                  # Standalone domain logic
│       └── pipeline/
│           ├── fetch.py           # RSS + NewsAPI + Firecrawl orchestrator
│           ├── sources/           # one file per source
│           ├── rank.py            # embeddings + cosine + MMR
│           ├── script.py          # GPT prompt + structured output
│           ├── tts.py             # ElevenLabs synthesis with concurrency
│           ├── stitch.py          # pydub concat with pauses
│           └── cli.py             # `python -m pipeline`
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── routers/           # preferences, podcasts, admin
│   │   │   ├── services/          # business logic
│   │   │   ├── worker/            # Celery app + tasks
│   │   │   ├── models.py          # SQLAlchemy 2.0 models
│   │   │   ├── schemas.py         # Pydantic in/out
│   │   │   ├── db.py              # async + sync engines
│   │   │   └── config.py          # pydantic-settings
│   │   └── migrations/            # Alembic
│   └── frontend/
│       └── src/
│           ├── api/               # typed clients per resource
│           ├── hooks/             # TanStack Query wrappers
│           ├── pages/             # Library, PreferencesPage, Admin
│           └── components/Layout.tsx
├── docker-compose.yml
└── solution.md
```

## Known limitations

- **Single user, no auth.** A demo user is bootstrapped at startup. Adding
  auth is a swap of `app/deps.py:get_current_user_id` to parse a JWT — all
  routers already depend on it via an `Annotated` type.
- **Avg cost in the admin dashboard is mocked at 0.** The pipeline stores
  `cost_cents=0`; computing real cost would mean tracking OpenAI tokens +
  ElevenLabs char counts per run and multiplying by current pricing. Per the
  brief's "feel free to use mocked data for the dashboard", left as a stub.
- **Length labels are approximate.** GPT doesn't always hit the requested
  word budget exactly; a 5-minute target frequently produces 3–4 minutes of
  audio. The UI labels them "Short ~3 min" / "Medium ~7 min" / "Long ~15 min"
  to set honest expectations rather than promise an exact runtime.
- **Pagination is offset-based.** Fine for any reasonable take-home volume;
  keyset pagination would be needed if the library grows past tens of
  thousands of episodes per user.
- **Article embeddings aren't persisted.** Each generation re-embeds the
  candidate pool from scratch. In production I'd cache them in `pgvector`
  and share across users — easily a 10x cost reduction at scale.
- **Hot-reload via `usePolling`.** Necessary for the Vite container on
  Windows + WSL2. Mild CPU cost during dev, irrelevant in production.

## What I'd build with more time

1. **Auth + multi-user.** Clerk or Auth0 for a single afternoon's work.
2. **Article cache with `pgvector`.** Major cost win; also enables "trending
   topics across all users".
3. **Per-segment feedback.** Thumbs up/down per story, feeding back into the
   ranking model as a personalization signal.
4. **Real cost telemetry.** Token + char tracking + pricing table → cost per
   podcast, cost per user, cost-to-value ratio per topic.
5. **Drop-off analytics.** The schema already has `segments.start_sec` /
   `end_sec`; with frontend playback events I could chart "which topics
   cause listeners to skip", which is the most actionable product metric
   possible.
6. **Prompt A/B testing.** Three prompt variants, randomized at generation
   time, listener thumbs-up rate as the metric.
7. **Multi-language.** ElevenLabs `eleven_multilingual_v2` already supports
   it; would need a language selector and a localized prompt.
8. **Production deployment.** Fly.io for the API + worker, Neon for
   Postgres, Upstash for Redis, Vercel for frontend. ~2 hours.

## Stack

- **Pipeline:** Python 3.12, OpenAI SDK, ElevenLabs SDK, httpx, feedparser,
  trafilatura, pydub, tenacity
- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, psycopg v3,
  Pydantic v2
- **Frontend:** Vite, React 18, TypeScript, TanStack Query, React Router,
  Tailwind, Recharts, lucide-react
- **Infra:** Postgres 16, Redis 7, Docker Compose

## Trade-offs I'd defend

1. **Modular monolith over microservices.** One backend image, two process
   types (api + worker). Same code path everywhere. Splittable if scale
   demands it, but not before.
2. **Postgres for everything, not a separate analytics store.** Until the
   events table grows past hundreds of millions of rows, plain SQL is faster
   to write, easier to evolve, and good enough.
3. **GPT-4o-mini over GPT-4o.** News synthesis is well within mini's
   capability. ~20x cheaper, 2–3x faster. The quality difference would only
   matter for content where nuance is the product — not here.
4. **Whitelist over blacklist for news sources.** The long tail of
   low-quality sources is infinite; the head of reputable ones is small and
   stable.
5. **Polling over WebSockets for job status.** A 2-second polling interval
   is simpler, survives reconnects, and keeps both sides stateless.
   WebSockets would be nicer UX with no real benefit at this scale.
