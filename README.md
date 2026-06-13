# CrowdRoom

![Python](https://img.shields.io/badge/Python-3.14+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-supported-4169E1?logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-supported-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-AGPL%203.0-E44BC2?logo=gnu&logoColor=white)

CrowdRoom is a real-time room-based music app built with FastAPI and Vue 3. It lets hosts manage shared rooms, invites, playback, queue interactions, and live updates over WebSockets.

## Features

- Real-time room updates over WebSockets
- Room, session, invite, moderation, and membership flows
- Queue management with voting and playback-related state
- Spotify integration for auth, search, and playback control
- Fallback music metadata flow and adapter-based external integrations
- `LOCAL` and `ONLINE` authentication modes
- PostgreSQL and SQLite support
- Docker setup for deployment and a separate frontend development workflow

## Supported platforms

Streaming providers are integrated through adapters (auth, search, playback).

| Platform | Status |
|----------|--------|
| Spotify | Supported |
| Tidal | Planned |

Spotify is the only provider currently implemented. The adapter layer (`backend/adapters/`) is built to host additional providers as they land.

## Companion hardware

[esp32-crowdroom](https://github.com/jaherhum/esp32-crowdroom) is an optional ESP32 firmware that receives a room's QR code and displays it on a physical device, so guests can scan and join the room without sharing a screen.

## Tech stack

### Backend
- FastAPI
- SQLModel
- Alembic
- PostgreSQL / SQLite (native dev only)
- Pydantic v2
- Argon2 password hashing

### Frontend
- Vue 3
- Vue Router
- Vite
- Vitest
- pnpm

## Quick start

### Docker

```bash
# 1. Configure secrets
cp .env.example .env
# Edit .env and set strong values for SECRET_KEY, ENCRYPTION_KEY and DEVICE_AUTH_TOKEN

# 2. Start the stack (tables are created automatically on first boot)
docker compose up --build -d

# 3. (Optional) Apply migrations — only needed when upgrading an
#    existing database to a newer schema
docker compose exec app alembic upgrade head
```

This starts the full stack:

- `app`: FastAPI backend and frontend serving container
- `db`: PostgreSQL 16 (`postgres:16-alpine`)

The application container waits for PostgreSQL to become healthy before starting.

Open the app at:

- `http://localhost:8000` on the same machine
- `http://<lan-ip>:8000` from other devices on the same network

By default the app is published on `0.0.0.0:8000`. Both the host bind IP and host port are configurable in `.env` (the container-side port stays fixed at `8000`):

```env
# Restrict exposure to localhost only
BIND_IP=127.0.0.1
# Publish on a different host port
HOST_PORT=9000
```

Persistent Docker volumes:

- `pgdata` for PostgreSQL data
- `avatars` for uploaded avatars

## Local development

For native development without Docker, point `DATABASE_URL` to SQLite or a local PostgreSQL instance.

### Backend

```bash
uv sync --dev
alembic upgrade head
uv run uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

API docs are available at `http://localhost:8000/docs`.

## Configuration

Settings are loaded from `.env` using Pydantic.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing key |
| `ENCRYPTION_KEY` | Fernet key for encrypted stored tokens |
| `AUTH_MODE` | Authentication mode: `LOCAL` or `ONLINE` |
| `DATABASE_URL` | PostgreSQL, or SQLite for native dev |
| `COOKIE_SECURE` | Set `True` only behind HTTPS |
| `FRONTEND_URL` | Frontend origin for CORS and redirects |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | Optional global Spotify credentials |
| `DEVICE_AUTH_TOKEN` | Shared secret for device/invite flows |
| `BIND_IP` | Host interface Docker publishes on (default `0.0.0.0`) |
| `HOST_PORT` | Host port mapped to container `8000` (default `8000`) |

See `.env.example` for the complete configuration.

## Authentication

- JWT-based authentication with long-lived access tokens
- Tokens stored in an httpOnly cookie
- Argon2 password hashing
- `LOCAL` mode for local host login plus lightweight guest flows
- `ONLINE` mode for full registration flows
- Token invalidation support through token versioning
- Cooldown and protection around incorrect PIN attempts

## Architecture

The backend follows a layered architecture with clear separation between API, business logic, persistence, and external integrations:

```text
API (backend/api/)
  -> Services (backend/services/)
  -> Repositories (backend/repositories/)
  -> Models (backend/db/models/)

Schemas (backend/schemas/) define request/response contracts
Adapters (backend/adapters/) integrate external providers
Drivers (backend/services/drivers/) isolate database-specific behavior
```

### Layer responsibilities

- `api/`: HTTP routes, auth dependencies, and WebSocket entrypoints
- `services/`: business logic and orchestration
- `repositories/`: data access and persistence
- `db/models/`: SQLModel entities
- `schemas/`: validation and serialization
- `adapters/`: third-party service integrations
- `services/drivers/`: backend-specific runtime behavior for PostgreSQL and SQLite

## Real-time and concurrency

- WebSocket events are used to broadcast room state changes in real time
- Queue and playback flows are handled in dedicated services
- PostgreSQL-specific coordination is isolated behind service/driver logic for operations that require stricter concurrency guarantees

## Testing

### Backend

```bash
uv run pytest
uv run pytest --cov=backend
uv run pytest -k "test_queue_service"
```

### Frontend

```bash
pnpm -C frontend test
```

### Lint and format

```bash
uv run ruff check
uv run ruff format
```

## Project layout

```text
backend/
  api/            # FastAPI routers, dependencies, WebSocket endpoints
  adapters/       # External service integrations
  core/           # Config, security, encryption, shared utilities
  db/             # Database setup and SQLModel models
  migrations/     # Alembic environment and migration versions
  repositories/   # Data access layer
  schemas/        # Pydantic schemas
  services/       # Business logic
  tests/          # Backend tests

frontend/
  src/            # Vue SPA source code
  public/         # Static public assets

docker/
  entrypoint.sh   # Container entrypoint
```

Project-specific conventions and assistant notes live in `AGENTS.md` and `CLAUDE.md`.

## Branching

- `main`: stable or release branch
- `develop`: integration branch
- `feature/*`, `fix/*`, `chore/*`: working branches

## Contributing

This project follows [Conventional Commits](https://www.conventionalcommits.org/) for all commits and pull request titles.

Common types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`.

Examples:
- `feat(queue): add vote weight calculation`
- `fix(auth): prevent token reuse after invalidation`
- `chore(deps): bump fastapi to 0.115`

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

See [LICENSE](LICENSE) for the full text, or read the license summary at:
https://www.gnu.org/licenses/agpl-3.0.html