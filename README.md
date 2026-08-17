# YantraSetu - The Bridge of Machines

Intelligent agricultural machinery **allocation and rebalancing** platform for
Custom Hiring Centres (CHCs). YantraSetu predicts where machinery demand will
exceed supply, finds idle machines elsewhere, and recommends cross-CHC
relocation plus optimized multi-farmer routes.

> Built for Smart India Hackathon. The core innovation is:
> **Demand Prediction -> Allocation -> Cross-CHC Rebalancing -> Route Optimization -> Utilization Improvement.**

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, Tailwind CSS, React Router, Axios, Leaflet + OpenStreetMap |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL (SQLite for quick local dev) |
| Optimization | Google OR-Tools (VRP with time windows) |
| Data / Prediction | Pandas, NumPy, explainable weighted scoring |

## Project structure

```
.
├── backend/            FastAPI application + engines
│   ├── app/
│   │   ├── main.py     API entrypoint
│   │   ├── config.py   Environment-based settings
│   │   ├── models/     SQLAlchemy models
│   │   ├── schemas/    Pydantic request/response schemas
│   │   ├── routers/    API endpoints
│   │   ├── services/   Demand, allocation, relocation, route, utilization engines
│   │   └── utils/      Shared helpers
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/           React + Vite app (added in Phase 0)
└── docs/               Architecture, API, and demo notes
```

## Running the backend (development)

From the `backend/` folder:

```bat
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs

## Status

Currently at **Phase 0 - Environment Setup**. Built incrementally, phase by phase.
