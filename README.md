# YantraSetu - The Bridge of Machines

Intelligent agricultural machinery **allocation and rebalancing** platform for
Custom Hiring Centres (CHCs). YantraSetu predicts where machinery demand will
exceed supply in the coming days, finds idle machines at other CHCs, recommends
a cross-CHC relocation (a human always approves it), and builds an optimized
multi-farmer route for the moved machine - then proves the payoff with analytics.

> Built for the Smart India Hackathon. The core loop is:
> **Demand Prediction → Allocation → Cross-CHC Rebalancing → Human Approval → Live Map → Route Optimization → Utilization Improvement.**

All demo data is **synthetic** (no real people, farms, or CHCs).

## 🚀 Live Demo

[🌐 Open YantraSetu Live Demo](https://yantrasetu.netlify.app)

Experience the deployed YantraSetu application and explore its intelligent
agricultural machinery allocation and management workflow.

---

## 1. What it does (the problem)

Finding "a nearby machine" is the easy part. The hard question YantraSetu answers is:

> *Where will machinery demand exceed supply in the next few days, and which idle
> machine from another CHC should be relocated to prevent that shortage?*

It works across multiple CHCs to: predict demand, detect upcoming shortages,
identify idle machines, score machine↔request compatibility, recommend cross-CHC
relocations (with an explicit cost/benefit), optimize multi-stop routes, and
report the utilization/wait-time improvement.

## 2. Architecture

**Pipeline (the product's core loop):**

```
Demand engine        →  flags a CRITICAL shortage (explainable weighted scoring)
   ↓
Allocation engine    →  ranks compatible machines on 7 weighted factors
   ↓
Relocation engine    →  computes NetBenefit of moving an idle machine A→B
   ↓
Human approval       →  a CHC Manager / Admin approves; status → in_transit
   ↓
Live digital-twin map→  shows the machine moving toward the shortage zone
   ↓
Route optimization   →  OR-Tools VRP with time windows (one trip, many farmers)
   ↓
Analytics            →  Before vs After: utilization, idle hours, wait time, net benefit
```

**How the pieces fit:**

- **Backend (FastAPI)** exposes a REST API under `/api`. The intelligence lives in
  `app/services/` (demand, allocation, relocation, route, utilization/impact
  engines). SQLAlchemy models persist to PostgreSQL. JWT auth + role-based access
  control (RBAC) guard the endpoints.
- **Frontend (React + Vite)** is a role-aware SPA. It authenticates against the
  backend, stores a JWT, and every screen calls the API through a single Axios
  client that attaches `Authorization: Bearer <token>`. Leaflet + OpenStreetMap
  render the live map; Recharts render the analytics.
- **Database (PostgreSQL)** holds CHCs, machines, availability, farmers, fields,
  demand requests, relocation recommendations, routes, and the `users` table for
  auth. Schema is managed by Alembic in production and `create_all()` in dev.

## 3. Tech stack (pinned)

**Backend** (`backend/requirements.txt`, Python 3.13):

| Package | Version | Purpose |
|---|---|---|
| fastapi | 0.141.1 | web framework |
| uvicorn[standard] | 0.52.3 | ASGI server |
| pydantic | 2.13.4 | validation |
| pydantic-settings | 2.15.0 | env-based config |
| python-dotenv | 1.2.3 | `.env` loading |
| SQLAlchemy | 2.0.52 | ORM |
| psycopg2-binary | 2.9.12 | PostgreSQL driver |
| alembic | 1.19.1 | migrations |
| numpy | 2.5.2 | scoring math |
| pandas | 3.0.5 | data handling |
| ortools | 9.15.6755 | VRP route optimization |
| bcrypt | 5.0.0 | password hashing (used directly) |
| PyJWT | 2.13.0 | JWT create/verify (HS256) |
| email-validator | 2.3.0 | email field validation |
| pytest | 9.1.1 | tests |
| httpx | 0.28.1 | test-only (TestClient transport) |

> Note: `bcrypt` is used directly, not via `passlib` - passlib 1.7.4 is
> unmaintained and crashes on init with bcrypt ≥ 5.x.

**Frontend** (`frontend/package.json`, Node 22+):

| Package | Version |
|---|---|
| react / react-dom | ^19.2.8 |
| react-router-dom | ^7.18.2 |
| @tanstack/react-query | ^5.101.4 |
| axios | ^1.19.0 |
| leaflet / react-leaflet | ^1.9.4 / ^5.0.0 |
| recharts | ^3.10.1 |
| lucide-react | ^1.32.0 |
| vite | ^8.2.1 |
| tailwindcss / @tailwindcss/vite | ^4.3.3 |
| @vitejs/plugin-react | ^6.0.5 |

## 4. Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            API entrypoint (mounts all routers under /api)
│   │   ├── config.py          env-based settings + production hardening
│   │   ├── database.py        engine/session/Base + create_all (dev)
│   │   ├── core/              security.py (hashing, JWT) + deps.py (RBAC)
│   │   ├── models/            SQLAlchemy models (incl. user.py)
│   │   ├── schemas/           Pydantic request/response schemas
│   │   ├── routers/           API endpoints (auth, chcs, machines, ..., me)
│   │   └── services/          demand / allocation / relocation / route / impact engines
│   ├── alembic/               migration environment + versions/
│   ├── tests/                 pytest suite
│   ├── seed_database.py       synthetic business data
│   ├── seed_users.py          demo login users
│   ├── Dockerfile, start.sh   production image + entrypoint
│   └── requirements.txt, .env.example
├── frontend/
│   ├── src/
│   │   ├── context/           RoleContext (auth) + DemoContext
│   │   ├── lib/               apiClient (Bearer interceptor), apiConfig, authToken
│   │   ├── services/          per-domain API wrappers
│   │   ├── hooks/             React Query hooks
│   │   ├── pages/             screens (Login, Overview, Demand, Allocation, ...)
│   │   ├── components/        UI + demo/DemoOverlay
│   │   └── config/            nav.js (role-based nav) + demoSteps.js
│   ├── netlify.toml, public/_redirects
│   └── package.json, .env.example
├── render.yaml                optional Render blueprint (backend + managed PG)
└── docs/                      architecture / API / demo notes
```

## 5. Local setup

Prerequisites: **Python 3.13**, **Node 22+**, and a **PostgreSQL** server
(local install or Docker). SQLite works for quick throwaway runs, but the demo
targets PostgreSQL.

```bash
git clone <your-repo-url> yantrasetu
cd yantrasetu
```

**Backend:**
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env
# then edit backend/.env with your real DATABASE_URL + a SECRET_KEY
```

**Frontend:**
```bash
cd ../frontend
npm install
# Optional: cp .env.example .env  (only needed if you override the API base)
```

**Run (two terminals):**
```bash
# terminal 1 - backend
cd backend && uvicorn app.main:app --reload      # http://127.0.0.1:8000  (docs at /docs)

# terminal 2 - frontend
cd frontend && npm run dev                        # http://localhost:5173
```

In dev, the Vite server (`vite.config.js`) proxies `/api` and `/health` to
`http://127.0.0.1:8000`, so leaving `VITE_API_URL` unset "just works".

## 6. Environment variables

**Backend** (`backend/.env.example` → copy to `backend/.env`, git-ignored):

| Variable | What it does |
|---|---|
| `APP_ENV` | `development` or `production`. In `production`, settings are hardened (see below). |
| `DEBUG` | `true`/`false`. Forced to `false` in production regardless of value. |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg2://user:pass@localhost:5432/yantrasetu`. URL-encode special chars in the password. |
| `SECRET_KEY` | JWT signing secret (HS256). In production the app **refuses to start** with an insecure/placeholder key (`change-me-in-production`, `dev-only-secret-change-me`, or < 16 chars). Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime in minutes (default `1440` = 24h). |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins. Defaults to the Vite dev origins; set to your deployed frontend origin in production (e.g. `https://yantrasetu.netlify.app`). |

**Frontend** (`frontend/.env.example`):

| Variable | What it does |
|---|---|
| `VITE_API_URL` | Backend base URL, **no trailing slash**. Leave **unset** for local dev (uses the Vite proxy). Set to the deployed backend origin for production (e.g. `https://yantrasetu-api.onrender.com`). Only `VITE_`-prefixed vars are exposed to the browser. |

> Never commit real `.env` files - both are git-ignored. The JWT is stored in
> the browser's `localStorage` (see Known limitations).

## 7. Database setup

The schema has **10 tables**: the 9 business tables + `users` (auth). Current
Alembic head is **`50d598d2fdf9`**.

### 7a. Seed the synthetic business data
From `backend/` (with `.env` pointing at your DB):
```bash
python seed_database.py
```
This calls `create_all()` (so tables exist), clears the 6 business tables, and
reseeds a deterministic imbalance (fixed random seed → reproducible):
**8 CHCs, 46 machines, 150 farmers, fields, availability, ~77 demand requests**,
with idle combines at "Green Valley" (Cluster A) and a combine shortage in
Cluster B. Safe to re-run. It does **not** touch `users`.

### 7b. Migrations (two scenarios)

- **Fresh / empty database (production path):**
  ```bash
  alembic upgrade head
  ```
  Creates all tables through migration `50d598d2fdf9`.

- **Database already created by `create_all()` (common in dev, and what the demo
  DB was):** Alembic has no history for it, so a plain `upgrade` would try to
  `CREATE TABLE` things that already exist. Instead, tell Alembic the schema is
  already current **without running migrations**:
  ```bash
  alembic stamp head
  alembic current        # expect: 50d598d2fdf9 (head)
  ```
  `stamp` only writes the `alembic_version` bookkeeping row - it never creates,
  drops, or alters a table.

  > Pitfall: do **not** stamp an *older* revision and then `upgrade` if the newer
  > tables (e.g. `users`) already exist via `create_all` - that raises
  > `DuplicateTable: relation "users" already exists`. When every current table
  > already exists, use `alembic stamp head`.

### 7c. Seed the demo login users
```bash
python seed_users.py
```
Idempotent (upserts by email). Creates **4 demo accounts**, all with password
**`demo1234`**, and links the farmer account to a real Farmer profile so its
owner-scoped screens have data:

| Email | Password | Backend role | Frontend persona |
|---|---|---|---|
| `admin@yantrasetu.demo` | `demo1234` | ADMIN | District Admin |
| `manager@yantrasetu.demo` | `demo1234` | CHC_MANAGER | CHC Manager |
| `operator@yantrasetu.demo` | `demo1234` | OPERATOR | Machine Operator |
| `farmer@yantrasetu.demo` | `demo1234` | FARMER | Farmer |

> Tip: run `seed_database.py` first, then `seed_users.py`, so the farmer link
> points at a current Farmer id (ids shift on re-seed).

## 8. Authentication & roles (RBAC)

- **Login:** `POST /api/auth/login` with JSON `{email, password}` → `{access_token}`
  (JWT, HS256, `sub`/`role`/`email` claims). `GET /api/auth/me` returns the user.
- **Registration:** `POST /api/auth/register` is public but **only creates FARMER
  accounts**; privileged roles are seeded or assigned by an admin.
- **Guards** (`app/core/deps.py`): `get_current_user`, `require_role`, `require_roles`.
- **Role-based navigation:** the frontend maps the backend role to a persona and
  shows only the screens that role can use.

| Area | FARMER | OPERATOR | CHC_MANAGER | ADMIN |
|---|:--:|:--:|:--:|:--:|
| Own requests + own fields/booking (`/api/me/*`, `/api/requests`) | ✅ own only | ❌ | ✅ all | ✅ all |
| Machines / CHCs read | ❌ | ✅ | ✅ | ✅ |
| Machines / CHCs manage (write) | ❌ | ❌ | ✅ | ✅ |
| Allocation / Forecast / Relocations | ❌ | ❌ | ✅ | ✅ |
| Route optimize / view | ❌ | ✅ | ✅ | ✅ |
| Map | ✅ | ✅ | ✅ | ✅ |
| Admin dashboard / Analytics | ❌ | ❌ | ❌ | ✅ |
| `/api/demo/*` | open (no auth) | open | open | open |

Unauthenticated → **401**; authenticated but wrong role → **403**. FARMER request
and field access is owner-scoped **at the query level** (a farmer can never read
another farmer's data, and a submitted `farmer_id` is ignored in favour of the
identity in the JWT).

## 9. Backend deployment (Docker → Render/Railway/Fly/VPS)

`backend/Dockerfile` builds a `python:3.13-slim` image (adds `libgomp1` for
OR-Tools). `backend/start.sh` is the entrypoint: it runs `alembic upgrade head`
**then** starts Uvicorn, so the app never serves on an un-migrated schema.

```bash
docker build -t yantrasetu-api ./backend
docker run -p 8000:8000 --env-file ./backend/.env yantrasetu-api
```

`render.yaml` is an optional Render blueprint (Docker web service + managed
PostgreSQL). It sets `APP_ENV=production`, generates `SECRET_KEY`, wires
`DATABASE_URL` from the managed DB, and leaves `CORS_ORIGINS` to set in the
dashboard. No secrets are committed. Verify blueprint keys against Render's
current schema before use.

## 10. Frontend deployment (Netlify / any static host)

`netlify.toml` builds `frontend/` (`npm run build`, publish `dist`, Node 22) and
adds an SPA fallback so deep links / refreshes don't 404 (`public/_redirects`
covers other static hosts). Set **`VITE_API_URL`** to your deployed backend
origin in the host's environment variables, and add that frontend origin to the
backend's `CORS_ORIGINS`.

## 11. Running the demo (end to end)

1. Ensure the backend and frontend are running, the business data is seeded
   (`seed_database.py`) and the demo users exist (`seed_users.py`).
2. Open `http://localhost:5173`, and **log in as `admin@yantrasetu.demo` /
   `demo1234`**. Run the walkthrough as **admin** - admin can view every screen
   the demo visits (other personas would hit 403s on some steps by design).
3. **Prepare relocation recommendations (needed after a fresh re-seed):** a new
   seed has the shortage but *no* recommendations yet. Go to **Relocation
   Approvals** and click **Generate** (as Admin or CHC Manager) to run the
   relocation engine and create the pending recommendation(s). (The demo overlay
   also has a **Reset scenario** button that rewinds an already-approved move
   back to `pending` so you can approve it live again.)
4. Click **Run Demo** (top bar) and step through with **Next**:
   1. The scenario → Overview (`/`)
   2. Detect the shortage → Demand (`/demand`) - Cluster B combine is CRITICAL
   3. Find the best machine → Allocation (`/allocation`)
   4. Weigh the move → Relocations (`/relocations`)
   5. Operator approves → **click Approve** on the pending combine move → `in_transit`
   6. Machine in transit → Map (`/map`)
   7. One trip, many farmers → Routes (`/routes`) → **click Optimize route**
   8. The measurable payoff → Analytics (`/analytics`) - Before vs After

The demo stays logged in as the same user throughout (no client-side role
switching - roles come from the JWT).

## 12. Testing

**Backend** (from `backend/`):
```bash
.venv\Scripts\python.exe -m pytest tests/ -q     # 143 tests
```
Covers the engines (demand/allocation/relocation/route/utilization),
booking/conflict rules, config hardening, auth (hashing, JWT, register/login),
and RBAC/ownership over the real HTTP layer. Tests run against an in-memory
SQLite DB - the real database is never touched.

**Frontend** (from `frontend/`):
```bash
npm run build     # production build; also the CI smoke check
```
> Troubleshooting: behind a TLS-inspecting proxy, npm may need
> `NODE_OPTIONS=--use-system-ca`.

## 13. Known limitations (honest list)

Not yet production-hardened:

- **Token storage:** the JWT lives in `localStorage` (an MVP trade-off) - readable
  by JS, so vulnerable to XSS. Hardening would move to httpOnly refresh cookies.
- **No refresh tokens / revocation:** access tokens are valid for 24h and cannot
  be revoked server-side before expiry (no blacklist).
- **No rate limiting / brute-force protection** on `/api/auth/login`.
- **No CI/CD** pipeline is configured.
- **Frontend has no automated tests** - only the production build is verified.
  (Backend has 143 tests.)
- **Farmer self-service depends on a linked profile:** New Request / My Booking
  work for a FARMER whose account is linked to a Farmer (`farmer_id`), which the
  demo seed sets. A self-registered farmer with no linked profile sees empty
  fields/requests and cannot create a request until staff link them.
- **Map needs internet:** OpenStreetMap tiles are fetched from the public tile
  server; offline/air-gapped demos won't render tiles.
- **Demo data is synthetic** and the relocation recommendation must be
  **generated** after each fresh re-seed (step 3 above). `seed_database.py`
  clears the 6 business tables but not `relocation_recommendations`/`routes`, so
  stale recommendations from a previous seed should be regenerated.
- **Deployment configs are provided, not yet run** against a live production
  deployment; verify `render.yaml`/`netlify.toml` keys against the platforms'
  current schemas.
- **Scale:** free-tier defaults (`WEB_CONCURRENCY=1`); OR-Tools routing is sized
  for the demo (a handful of stops), not fleet-scale planning.
- **No observability** (structured logging, metrics, tracing, alerting) beyond
  the basic `/health` probe.

---

*Synthetic demo data throughout. Built for the Smart India Hackathon.*
