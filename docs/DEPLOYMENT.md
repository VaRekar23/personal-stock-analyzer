# Deployment & Going Live (Google Cloud) + Mock → Live Provider Guide

This app is **container-ready**. In V1 everything runs on deterministic **MOCK** providers
so nothing external is required to deploy. To connect real Kite/OpenAI/etc, see §3.

---

## 1. What ships in the repo
| File | Purpose |
|---|---|
| `backend/Dockerfile` | FastAPI image (uvicorn). Reads all config from env. Auto-creates the DB schema on startup. |
| `frontend/Dockerfile` + `frontend/nginx.conf` | Builds the React app and serves it via nginx (SPA fallback). `REACT_APP_BACKEND_URL` is a **build-arg** (baked at build time). |
| `docker-compose.yml` | Full stack (backend + frontend + postgres + redis) for local or a single GCE VM. |
| `backend/.env.example` | All environment variables. |

---

## 2. Deploying to Google Cloud

### Option A — Cloud Run (recommended: serverless, managed)
Uses **Cloud Run** (containers) + **Cloud SQL for PostgreSQL** + **Memorystore for Redis**.

```bash
PROJECT=your-gcp-project
REGION=asia-south1                     # Mumbai
gcloud config set project $PROJECT

# --- Managed datastores ---
# 1) Cloud SQL (PostgreSQL 15) — create instance, db 'stockai', user 'stockapp'.
gcloud sql instances create stockai-pg --database-version=POSTGRES_15 \
  --tier=db-f1-micro --region=$REGION
gcloud sql databases create stockai --instance=stockai-pg
gcloud sql users create stockapp --instance=stockai-pg --password=YOUR_DB_PASSWORD

# 2) Memorystore (Redis) — note the instance host IP (needs a VPC connector for Cloud Run).
gcloud redis instances create stockai-redis --size=1 --region=$REGION

# --- Backend image ---
gcloud builds submit ./backend --tag gcr.io/$PROJECT/stockai-backend
gcloud run deploy stockai-backend \
  --image gcr.io/$PROJECT/stockai-backend --region $REGION --allow-unauthenticated \
  --add-cloudsql-instances $PROJECT:$REGION:stockai-pg \
  --set-env-vars "DATABASE_URL=postgresql://stockapp:YOUR_DB_PASSWORD@/stockai?host=/cloudsql/$PROJECT:$REGION:stockai-pg" \
  --set-env-vars "REDIS_URL=redis://REDIS_HOST:6379/0,DATA_PROVIDER=mock,FUNDAMENTAL_PROVIDER=mock,NEWS_PROVIDER=mock,AI_PROVIDER=mock,AI_MODEL=mock-analyst-v1,CORS_ORIGINS=*"
# (Add a Serverless VPC connector so Cloud Run can reach Memorystore Redis.)

# --- Frontend image (bake the backend URL from the previous deploy) ---
BACKEND_URL=$(gcloud run services describe stockai-backend --region $REGION --format='value(status.url)')
gcloud builds submit ./frontend \
  --substitutions=_URL=$BACKEND_URL --config=/dev/stdin <<'YAML'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build','--build-arg','REACT_APP_BACKEND_URL=${_URL}','-t','gcr.io/$PROJECT_ID/stockai-frontend','.']
images: ['gcr.io/$PROJECT_ID/stockai-frontend']
YAML
gcloud run deploy stockai-frontend --image gcr.io/$PROJECT/stockai-frontend \
  --region $REGION --allow-unauthenticated
```
Notes:
- Store real API keys in **Secret Manager** and mount with `--set-secrets` instead of `--set-env-vars`.
- Redis is optional — the app falls back to an in-memory cache if `REDIS_URL` is unreachable.

### Option B — Single GCE VM (simplest)
1. Create an Ubuntu VM, install Docker + docker-compose.
2. Copy the repo, create `.env` at repo root (see variables below).
3. `REACT_APP_BACKEND_URL=http://<VM_PUBLIC_IP>:8001 docker compose up -d --build`
4. Frontend on `:8080`, backend on `:8001`. Put nginx/HTTPS in front for production.

---

## 3. MOCK APIs → what to replace to go LIVE

> **Important:** V1 ships provider **interfaces + mock implementations**. Switching the
> `*_PROVIDER` env var to a live value is **not enough on its own** — the concrete live
> adapters (Kite, OpenAI, TrueData) still need to be implemented and wired in
> `backend/stockai/providers/registry.py`. Share your keys and I'll implement + wire them
> (OpenAI via the verified integration playbook; Kite/TrueData after verifying their exact
> current API). Nothing is fabricated until verified.

### Mock inventory
| # | Mock (current) | File | Replaces (live) | Env var to set | Keys you provide |
|---|---|---|---|---|---|
| 1 | `MockMarketDataProvider` | `providers/mock/market.py` | **Zerodha / Kite Connect** — instruments, historical OHLCV, quotes | `DATA_PROVIDER=zerodha` | `ZERODHA_API_KEY`, `ZERODHA_API_SECRET`, `ZERODHA_ACCESS_TOKEN` |
| 2 | `MockPortfolioProvider` | `providers/mock/portfolio.py` | **Zerodha / Kite** — holdings & positions | (same as #1) | (same as #1) |
| 3 | `MockFundamentalDataProvider` | `providers/mock/fundamental.py` | **TrueData** (or chosen fundamentals API) | `FUNDAMENTAL_PROVIDER=truedata` | `FUNDAMENTAL_API_KEY` (+ any TrueData login) |
| 4 | `MockNewsProvider` | `providers/mock/news.py` | **News provider** (TrueData/other) | `NEWS_PROVIDER=<provider>` | `NEWS_API_KEY` |
| 5 | `MockAIProvider` | `ai/mock_provider.py` | **OpenAI** (explanation layer) | `AI_PROVIDER=openai`, `AI_MODEL=<model>` | `OPENAI_API_KEY` |

Live adapter placeholder (already scaffolded, marked *pending verification*):
`backend/stockai/providers/zerodha/client.py`.

### Kite Connect specifics (what I'll need from you)
- **API Key** and **API Secret** from https://developers.kite.trade (Kite Connect app).
- A valid **Access Token** — Kite access tokens are generated via the login `request_token`
  → `generate_session` flow and **expire daily**. Tell me whether you want:
  (a) to paste a fresh access token into env each day, or
  (b) a small server-side login endpoint that completes the Kite login flow and stores the
  daily token. (b) is the practical choice; I'll build it when you share the API key/secret.
- Note: Kite historical data needs the **historical data** subscription add-on.

### OpenAI specifics
- Just the `OPENAI_API_KEY` and the model you want (e.g. a current GPT model).
- I'll implement `OpenAIProvider` behind the existing `AIProvider` interface (structured
  JSON output, versioned prompts, same Redis caching) — no other code changes needed.

---

## 4. Full environment variable list
See `backend/.env.example` and `docs/CONFIGURATION.md`. Minimum to run (mock mode):
`DATABASE_URL`, `REDIS_URL` (optional), and the five `*_PROVIDER` vars left as `mock`.
Add the live keys above only for the providers you switch off `mock`.

---

## 5. Pushing the code to GitHub
Use Emergent's built-in **"Save to GitHub"** control in the UI (top-right of the chat) —
see the assistant message for the exact steps returned by support. That connects your
GitHub account and pushes the repository; you don't run git manually from here.
