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


## Voice input (Phase 17) — deliberate scope + un-verified integration

**Free-form NLU is NOT built.** Spoken transcripts are mapped to form fields by
a simple **rule-based keyword match** (operation type + urgency only). Extracting
crop/field/date, or understanding paraphrased/free-form sentences, would need an
NLU/LLM step — deliberately deferred. The transcript is always shown for the
farmer to edit and **never auto-submits**; field/date are still chosen manually.

**Bhashini integration is coded to the documented contract but NOT live-verified
here.** This environment has no Bhashini credentials and cannot reach the
government API, so `bhashini_client` is only exercised via mocks. Before it works
live, the user must:
- set `BHASHINI_USER_ID` + `BHASHINI_API_KEY` (and possibly `BHASHINI_PIPELINE_ID`)
  on the backend;
- verify the **audio format** path — the browser records `audio/webm` (opus) via
  `MediaRecorder`, and Bhashini's ASR may require WAV/FLAC. If webm is rejected, a
  transcoding step (client-side WAV encode, or server-side ffmpeg) is the
  follow-up. The proxy passes the format through and degrades gracefully
  meanwhile.

Until then, the mic **degrades gracefully**: proxy 503/502 → browser Web Speech
API (if supported) → button disabled with a tooltip; typed entry always works.

**Rate-limiting is size-only.** The proxy rejects oversized clips
(`VOICE_MAX_UPLOAD_BYTES`) and requires authentication, but there is no per-user
request-rate limiter (no such infra in the app). True rate-limiting is a
follow-up.

**Budget-Android verification is manual.** Web Speech API support is patchy in
in-app WebViews / older Chrome — this can only be verified on a physical device,
not in this environment.
