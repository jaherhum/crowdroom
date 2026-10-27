# AGENTS.md

This file provides guidance to agentic coding tools working in this repository.

## Project overview

CrowdRoom is a real-time, room-based collaborative music app. Hosts create rooms, manage invites, playback, and a shared song queue; guests join over WebSockets and get live state updates. FastAPI + SQLModel backend, Vue 3 + Vite frontend. Works with PostgreSQL (Docker/production) or SQLite (native dev). Only streaming provider currently integrated is Spotify; the adapter layer exists to add more.

## Commands

Backend deps managed with `uv` (see `uv.lock`); frontend with `pnpm`.

```bash
# Backend
uv sync --dev                 # install deps
uv run uvicorn backend.main:app --reload   # dev server (native, no Docker)
alembic upgrade head           # apply migrations (native dev)
uv run pytest                 # all backend tests
uv run pytest -k test_queue_service   # single backend test
uv run ruff check             # lint
uv run ruff format            # format

# Frontend (run from repo root or frontend/)
cd frontend && pnpm install
pnpm dev                      # Vite dev server
pnpm build
pnpm test                     # Vitest run
pnpm lint / pnpm format

# Docker
docker compose up --build -d     # full stack (db + app); tables auto-created
make down  # alias for down; `make up`, `make logs`, `make shell`, `make migrate`
```

API docs at `http://localhost:8000/docs` — but note docs routes are IP-gated (see below).

## Architecture

Layered: `api/` → `services/` → `repositories/` → `db/models/`. Requests flow HTTP route → service (business logic) → repository (persistence) → SQLModel entity. Schemas (`schemas/`) are Pydantic validate/serialize contracts; adapters (`adapters/`) talk to external providers; drivers (`services/drivers/`) isolate DB-specific runtime behavior.

- `api/`: FastAPI routers, auth dependencies, WebSocket entrypoint (`websocket.py`). Each router has a sibling `dependencies.py` exposing the service factory for its layer.
- `services/`: business logic + orchestration. Notable: `playback_poller_service.py` polls the provider and broadcasts state; `stream_service.py`, `fallback_service.py`, `music_service.py` handle metadata/fallback flows.
- `repositories/`: data access. Receive/return SQLModel models, never schemas.
- `adapters/`: external integrations. `BaseAdapter` (search/get_metadata/get_track_uri) is the app-scoped interface; per-user credential flows live in separate user-scoped classes (e.g. `SpotifyPlaybackAdapter` takes an access_token). `AdapterFactory` maps `StreamingPlatforms` enum → concrete adapter.
- `drivers/` (`postgres.py`, `sqlite.py`): DB-specific logic. `PGQueueLock` does queue-group advisory locking with transactions; SQLite uses WAL.
- `core/`: config (`AUTH_MODE=LOCAL|ONLINE`, DATABASE_URL derived from it), security (JWT, Argon2), encryption (Fernet for stored tokens), exceptions.

### Deployment modes

`AUTH_MODE` drives DB choice: `LOCAL` → SQLite (native dev), `ONLINE` → PostgreSQL. `create_db_and_tables()` (SQLModel `create_all`) runs idempotently on startup and in the Docker entrypoint before uvicorn binds; Alembic migrations are only for upgrading existing databases.

### Concurrency

Queue operations use advisory locks on PostgreSQL behind a `QueueLock` context manager provided by the drivers; concurrency tests exist as `test_queue_concurrency.py` (SQLite) and `test_queue_concurrency_pg.py` (PostgreSQL).

## Key behaviors to know

- **WebSocket broadcast**: room state changes are pushed to clients via WebSocket (`/ws`). New real-time flows should reuse this broadcast pattern.
- **`song_changed` emission**: never emit `song_changed` based on `position == 0` — only when the player is genuinely idle (`current_song_id` / `playback_status`). Queue index 0 = currently-playing song (frontend drops it via `slice(1)`); keep that ordering stable.
- **Docs access control**: `/docs`, `/redoc`, `/openapi.json` respond 404 unless the client IP is in `settings.docs_allowed_networks`; `DOCS_TRUST_PROXY` enables X-Forwarded-For handling (only behind a trusted proxy).
- **Exceptions**: domain exceptions subclass `AppException` (`core/exceptions.py`); global handlers map them to status codes (404/409/401/410/502…). Per-endpoint try/except converts to `HTTPException` and takes precedence.
- **Host-permission checks**: use `RoomService.assert_host(room_id, user_id)` — inject `RoomService`, never write a local `_assert_host` helper (see `.claude/rules/host-permission.md`).
- **DI wiring**: reuse existing dependency factories (e.g. import `get_room_service` from `api/rooms/dependencies.py`). Never re-define a factory that exists (see `.claude/rules/di-wiring.md`).
- **Adapter separation**: user-scoped vs app-scoped adapters are separate classes; don't mix (see `.claude/rules/adapters.md`).
- **Layer boundaries**: repositories return DB models, not schemas; data normalization (`.lower()` on emails/usernames) happens in services (see `.claude/rules/layer-boundaries.md`).

## Testing conventions (backend)

Rules from `.claude/rules/testing.md`:
- Use `MagicMock(spec=ClassName)` for all mocks — enforces interface compliance.
- Async methods tested via `anyio.run()` wrapper.
- Fixtures per-test-class, no shared `conftest.py`.
- Host-permission tests mock `room_service.assert_host`, not `room_repo.get_by_id`.

## Branching & contribution

- PRs open against `develop`, never `main` (main is release/stable).
- Conventional Commits for all commits and PR titles: `feat(scope): ...`, `fix(scope): ...` etc.
- Issues and PRs written in English.