# ROADMAP — NetOps Copilot AI

> Timeline note: the team asked for "as early as possible." This roadmap is compressed into **3 weeks (21 days)** assuming all 5 members can work in parallel most days. If your actual available time is less concentrated (classes, other SOPs, exams), stretch each phase proportionally rather than cutting scope from Phase 1–2 — the MVP loop (telemetry → detection → correlation → diagnosis → recommendation → human decision) is the part that must not be cut, since it's the entire thesis of the project. See `todo.md` for the day-by-day, person-by-person breakdown.

## Phase 1: Foundation (Days 1–5)
**Goal:** Every team member can run the full skeleton locally; real telemetry is flowing into a real database and showing up, unstyled, on a page.

- Repo, branching strategy, Docker/docker-compose skeleton for backend + Postgres.
- Neon Postgres project created; SQLAlchemy models + Alembic migration for `Telemetry`.
- Telemetry collector (Module 1) pushing real `psutil` + ping data to `/api/telemetry/ingest`.
- FastAPI skeleton with ingest + `latest`/`history` endpoints, deployed once (even bare-bones) to Render to de-risk deployment early.
- Next.js skeleton deployed once (even a placeholder page) to Vercel, wired to hit the live Render backend — proves the whole free-tier chain works before real feature work begins.
- **Milestone:** Real latency/packet-loss numbers from a real interface visible in a raw JSON response from the deployed backend.

## Phase 2: Core Development (Days 6–13)
**Goal:** The full reasoning pipeline exists end-to-end for at least the "network congestion" scenario, and the Overview + Incident Detail screens are functional (even if not fully styled).

- Anomaly Detection (threshold/statistical baseline) — Module 3.
- Correlation Engine grouping symptoms into an Incident — Module 4.
- Root-Cause / Diagnosis Agent (rule-weighted scoring, evidence, confidence) — Module 5.
- Explainability Layer + basic Causal Graph component — Module 6.
- Severity/Impact scoring — Module 7.
- Recommendation Agent (rule table) — Module 8.
- Safety Governor gate — Module 9.
- Human-in-the-Loop Approve/Reject, persisted — Module 10.
- Overview screen (health badge, MetricCards, active incidents strip) — real data, DESIGN.md layout, not yet fully polished.
- Incident Detail screen — diagnosis, evidence, causal graph, recommendation, approve/reject — functionally complete.
- **Milestone:** Deliberately induce a real congestion event (e.g., a large download) on the demo machine and watch a correctly-diagnosed, evidence-backed incident appear on the dashboard, then Approve it.

## Phase 3: Polish & Extended Scope (Days 14–17)
**Goal:** Should-Have features land, UI is brought fully in line with DESIGN.md, and the system is hardened against demo-day surprises.

- Incidents list screen with filters — full CRUD-read + filtering.
- History screen with time-range picker and multi-metric chart.
- Incident Memory similarity surface ("similar past incident found").
- ML-based anomaly detection (Isolation Forest) added alongside the rule-based baseline.
- Security Agent (low-confidence "possible suspicious pattern" flag), clearly caveated in the UI copy.
- Basic auth on mutating routes.
- Accessibility pass (contrast, keyboard nav, aria-labels) per DESIGN.md.
- Error/loading/empty states implemented on every screen (not just happy path).
- **Milestone:** A team member unfamiliar with the code can use the dashboard for 10 minutes without hitting a broken/blank state.

## Phase 4: Testing & Launch Readiness (Days 18–21)
**Goal:** The system is demo-proof, documented, and deployed on its final free-tier infrastructure.

- Unit tests for all 5 core agent modules (pytest) — at least one positive and one negative case each.
- One end-to-end integration test (synthetic telemetry → incident produced).
- Full run-through of the induced-congestion demo scenario, timed against the PRD's detection-latency KPI, with real numbers recorded in `docs/eval_results.md`.
- Final deploy: Render (backend) + Vercel (frontend) + Neon (DB) — confirm the whole chain survives a cold start (Render free tier sleeps after inactivity — the demo script must account for a possible 30–60s wake-up on the first request, e.g., by "waking" the backend a minute before presenting).
- README finalized with setup, architecture, and demo instructions (see README.md).
- Dry-run the demo at least twice as a full team before the actual SOP presentation/evaluation.
- **Milestone:** Submission-ready repo + live URLs + rehearsed demo script.

## Future Phases (Post-Submission, Optional)

- Multi-host telemetry (more than one collector reporting into the same backend).
- Packet-level root-cause evidence via Scapy/PyShark.
- Formal agent-to-agent messaging layer instead of direct function calls, if the team wants to extend this beyond the SOP into a more literal distributed multi-agent architecture.
- Real, scoped remediation on a lab-only test network segment, closing the loop beyond "decision recorded" — would require explicit departmental authorization first.
- Optional local-LLM (Ollama) natural-language incident summaries, kept strictly free/local.

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Free-tier backend cold start (Render sleeps after 15 min idle) embarrasses the team mid-demo | Medium | "Wake" the backend a minute before presenting; consider a lightweight uptime-ping (e.g., a free UptimeRobot monitor) during the demo week only |
| College network conditions on demo day don't naturally produce a congestion event | High | Have a rehearsed, reliable way to induce one on demand (e.g., a large but reasonable file download on the demo machine) — decide and test this well before demo day |
| 5-person parallel work causes integration conflicts on the shared backend schema | Medium | Freeze the core data model (see TECH_RULES.md) by end of Phase 1; changes after that go through a quick team sync, not a silent PR |
| Compressed "as early as possible" timeline tempts scope cuts to the reasoning pipeline itself | High | Protect Phase 2 (the core pipeline) above all else — if time runs short, cut Should/Nice-Have UI polish (Phase 3), never the diagnosis→recommendation→human-decision loop, since that loop is the project's actual thesis |
| A teammate's evaluation of "possible suspicious pattern" (Security Agent) gets over-read as a real security tool | Low–Medium | Explicit, persistent UI caveat wherever this appears; do not oversell it in the PRD/report either |
