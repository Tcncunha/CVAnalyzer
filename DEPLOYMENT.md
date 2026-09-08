# Deployment & Operations

Operational guide for the CV Analyzer Streamlit app: local run, container
deploy, secrets, persistence, release flow and rollback.

## Run locally

```bash
# 1. Install dependencies (Windows / Linux / macOS)
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest only

# 2. (Optional) default API keys
cp .env.example .env                  # fill the keys you want pre-loaded

# 3. Start the app
streamlit run src/app.py
```

Open `http://localhost:8501`. Adzuna `app_id`/`app_key` and provider keys can
also be entered in the sidebar at runtime (session-only).

## Run with Docker

```bash
# Build and start (single command)
docker compose up -d --build

# Or classic flow
docker build -t cv-analyzer .
docker run -d --name cv-analyzer -p 8501:8501 cv-analyzer

# Follow logs / stop
docker compose logs -f
docker compose down
```

The container exposes port **8501** and runs `streamlit run src/app.py`.

### Environment variables

| Variable | Purpose |
|---|---|
| `OPENCODE_ZEN_API_KEY` | OpenCode Zen (optional — free default models) |
| `GEMINI_API_KEY` | Google Gemini |
| `OPENAI_API_KEY` | OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `COPILOT_API_KEY` | GitHub Copilot |

`docker-compose.yml` passes these through from the host environment or a local
`.env` file (`${VAR:-}` keeps them optional). Keys are **never baked into the
image** and the app never writes them to disk — they live in session state
only.

### Healthcheck

```bash
curl -fsS http://localhost:8501/_stcore/health   # expect "ok"
```

The Dockerfile defines a HEALTHCHECK (every 30s, start period 15s) that probes
`/_stcore/health`. `docker compose ps` shows container health.

### Data persistence

Two named volumes survive recreation and upgrades:

- `cv_profiles` → `/app/src/profiles_json` (saved candidate profiles)
- `cv_tracker` → `/app/src/tracker.db` (application Tracker SQLite DB)

`docker compose down` keeps volumes; add `-v` to delete them permanently.
Prefer **graceful restarts** (`docker compose restart`) so SQLite WAL
checkpoints cleanly. A hard kill can lose the last few uncheckpointed
transactions.

## Proxy / exposure

For production reachability place the container behind a reverse proxy with
TLS. Streamlit needs **WebSocket upgrades** enabled for interactive widgets:

```nginx
# nginx example
server {
    listen 443 ssl;
    server_name cv.example.com;
    # ssl_certificate / ssl_certificate_key ...

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

Terminating TLS on the proxy keeps the container on a private interface. For
shared/multi-user deployments add an auth layer (SSO/forward-auth) at the
proxy — the app has no built-in authentication.

## CI/CD, releases and rollback

**CI (`.github/workflows/ci.yml`)** runs on every push/PR:

1. `test` job — Python 3.14: install deps, `compileall`, full pytest suite,
   entrypoint import smoke test, banner asset check.
2. `docker` job — `needs: test`; builds the image with BuildKit cache and then
   **boots the container** to verify the health endpoint and confirm
   `/app/src/img/MainBanner.png` is present at runtime.

The pipeline is intentionally **build-only** (no secrets, no registry push).
To publish, extend the `docker` job with `docker/login-action`
(`secrets.GITHUB_TOKEN` for GHCR) and set `push: true` with your image tags.

**Release flow**

1. All tests green on `main`.
2. Tag a release: `git tag v1.2.0 && git push --tags`
3. Build/publish the image with the tag (CI rebuilds on `v*` tags).
4. Deploy: `docker compose pull` (or `--build`) on the host, then
   `docker compose up -d`.

**Rollback plan**

```bash
# 1. Pin the previous image checkout and recreate — no data loss
git checkout <previous-release-tag>
docker compose up -d --build

# 2. Or roll back to a previously built image
docker compose stop
docker compose run --rm cv-analyzer bash   # inspect if needed
# set image: cv-analyzer:<previous-sha> in docker-compose.yml, then:
docker compose up -d
```

Volumes keep user data across rollbacks; only the app code changes.

## Observability

- Logs: `docker compose logs -f cv-analyzer` (app logs to stdout with
  `PYTHONUNBUFFERED=1`; structured INFO logging from `src/app.py`).
- Liveness: `/_stcore/health` (returns `ok`).
- Session errors surface in-app and in the container logs; AI provider 4xx/5xx
  retry behavior is handled inside `src/auto_match.py`.

That's it — no extra monitoring infrastructure is required for a personal /
small-team deployment.