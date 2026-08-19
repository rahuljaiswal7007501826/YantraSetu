# Assumptions & Deliberate Deferrals

A visible log of business rules that are intentionally simplified or deferred,
so they are explicit decisions rather than silent assumptions.

## Per-CHC manager scoping — DEFERRED (Phase 16)

**Current behavior:** Any `CHC_MANAGER` (or `ADMIN`) can act on **any** pending
request — assign a machine, reject with a reason — regardless of which CHC owns
the machine or serves the farmer. The manager's "pending requests" list is the
existing role-gated `GET /api/requests?status=pending`.

**Why:** This matches the app's existing authorization model — every staff
endpoint (allocation, relocation, forecast, machine/CHC management) is
**role-scoped, not CHC-scoped**. There is currently **no manager↔CHC link**: the
`User` model has no `chc_id`, and no endpoint filters by "the current user's
CHC."

**What a real per-CHC rule would require (not built):** a `users.chc_id` foreign
key, a way to assign managers to CHCs, and CHC-scoped queries/guards on the
assignment endpoints. That is a genuine data-modeling decision, planned as a
follow-up — **not** bolted on here.

**Consequence:** The Phase 16 assignment endpoints (`/api/requests/{id}/assign`,
`/reject`, `/cancel`) are role-gated only. There is deliberately **no**
cross-CHC 403 test, because there is no per-CHC boundary to enforce yet.
