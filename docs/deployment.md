# Deployment Guide

Everything you need to install, configure and operate TreeVuln. For a product overview, see the [README](../README.md).

## Requirements

- Docker Engine 24+ with the Docker Compose plugin
- 2 GB RAM and 1 CPU are enough for evaluation; add headroom for large batches

## Installation

```bash
git clone <repository-url> && cd TreeVuln
cp .env.example .env
```

Edit `.env` before the first start — at minimum:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL superuser password (schema management). Generate one: `python -c "import secrets; print(secrets.token_urlsafe(24))"` |
| `APP_DB_PASSWORD` | Password for the least-privilege application role used by the backend. Recommended for any non-throwaway install (with `DATABASE_URL` switched to the application-role variant, see the comments in `.env.example`) |
| `SECRET_KEY` | Fernet key encrypting webhook secrets and ingest API keys at rest. Generate one: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. If left empty, an auto-generated key is stored in the database next to the data it protects — acceptable for development only |
| `DEBUG` | `false` in production. `true` enables the Swagger UI at `/docs` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins if you serve the UI from another host |

Then:

```bash
docker compose up -d
```

## First launch

Open http://localhost:3000. TreeVuln ships with **no default credentials**: the first screen is a setup wizard that creates the initial admin account. Alembic migrations run automatically at backend startup.

Three example trees are pre-loaded: **SSVC Example** (default tree, with 8 sample assets), **Equation Example** and **CSAF VEX Example**.

| Service | URL | Notes |
|---------|-----|-------|
| Application | http://localhost:3000 | nginx, serves the UI and proxies the API |
| API | http://localhost:8000 | FastAPI backend |
| API docs (Swagger) | http://localhost:8000/docs | only when `DEBUG=true` |

Both ports are bound to `127.0.0.1` only. To expose TreeVuln beyond the local machine, put your own reverse proxy (with TLS) in front of port 3000 — the bundled nginx already applies rate limiting and security headers (CSP, X-Frame-Options, …).

## Day-2 operations

```bash
docker compose up -d              # Start
docker compose down               # Stop (data is preserved)
docker compose up -d --build      # Rebuild after an update
docker compose logs -f backend    # Backend logs (JSON, rotated)
docker compose ps                 # Health status
```

> **Warning — data loss**: `docker compose down -v` deletes the PostgreSQL volume, i.e. **all trees, assets, users and settings**. Never use `-v` unless you intend to wipe the instance.

### Backup and restore

```bash
# Backup (custom format, compressed)
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > treevuln_$(date +%Y%m%d_%H%M%S).dump

# Restore into a fresh instance
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < treevuln_YYYYMMDD_HHMMSS.dump
```

If you set `SECRET_KEY`, back it up alongside the dumps: encrypted webhook secrets and ingest API keys are unreadable without it.

## Production checklist

- [ ] Strong `POSTGRES_PASSWORD` and `APP_DB_PASSWORD` set, `DATABASE_URL` using the application role
- [ ] `SECRET_KEY` set and stored in your secret manager
- [ ] `DEBUG=false`
- [ ] TLS-terminating reverse proxy in front of port 3000
- [ ] Scheduled database backups (see above)
- [ ] `docker compose down` (never `-v`) in operating procedures

## Local development (without Docker)

Requires Python 3.11+, Node 20+, a local PostgreSQL 15 and the environment variables from `.env.example`.

```bash
# Backend (CSAF signing requires the gpg binary: apt install gnupg)
cd backend && pip install -e . && uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Tests

```bash
cd backend && python -m pytest tests/ -v
cd frontend && npm test
```

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Browser shows *"SSL received a record that exceeded the maximum permissible length"* | You opened `https://localhost:3000` — the bundled nginx serves plain HTTP. Use `http://` or put a TLS proxy in front |
| `/docs` returns 404 | `DEBUG=false` (expected in production) |
| Backend logs an ERROR about the encryption key at startup | `SECRET_KEY` is empty while `DEBUG=false` — generate and set it |
| Trees/users gone after a restart | The volume was removed (`down -v`). Restore from a backup |
