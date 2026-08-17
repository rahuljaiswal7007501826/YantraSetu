# YantraSetu - Architecture (working draft)

This document grows as the system is built. It captures the *why* behind the
design so the team and judges can follow the reasoning.

## The problem

Finding a nearby machine is easy. The hard, valuable problem is:

> Where will machinery demand exceed supply in the coming days, and which idle
> machine from another CHC should be moved to prevent that shortage?

## High-level flow

```
Farmer request
      |
      v
Demand Intelligence  ->  detect upcoming shortages per cluster
      |
      v
Allocation Engine    ->  compatibility gate + weighted scoring -> ranked machines
      |
      v
Relocation Engine    ->  NetBenefit of moving idle machines across CHCs
      |                  (recommendation only; operator approves)
      v
Route Optimization   ->  OR-Tools VRP with time windows -> multi-stop route
      |
      v
Utilization Engine   ->  measure improvement (idle down, coverage up)
```

## Components (filled in per phase)

- **Backend (FastAPI):** REST API, engines as services, SQLAlchemy models.
- **Database (PostgreSQL):** CHCs, machines, farmers, fields, requests,
  availability, bookings, routes, forecasts, relocation recommendations.
- **Frontend (React + Vite):** role-based dashboards, live Leaflet map, charts.
- **Optimization (OR-Tools):** vehicle routing with time windows.

## Design principles

1. **Explainable, not black-box.** Scores are weighted sums with visible
   reasons - important for trust and for judge Q&A.
2. **Recommend, never auto-act** on relocation. A human operator approves.
3. **Hard compatibility gate.** Incompatible machines are removed before scoring.
4. **PostgreSQL-compatible** even when SQLite is used for quick local dev.
