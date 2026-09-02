# TECH_RULES — NetOps Copilot AI

## Tech Stack Decision

All choices below are free-tier, no-credit-card, no-paid-API-key services. Verified current as of Sept 2026 — free-tier terms change over time, so re-check the official pricing pages before final deployment/submission.

| Layer | Choice | Why | Free-tier notes |
|---|---|---|---|
| Frontend | Next.js (React) + Tailwind CSS + Recharts | Fast to build, matches DESIGN.md component needs, huge free ecosystem | Hosted free on **Vercel** (Hobby plan) |
| Backend API | FastAPI (Python) | Async, auto docs (`/docs`), Pydantic validation fits our strict schema needs, team already knows Python from ML coursework | Hosted free on **Render** (Web Service, free tier) |
| Database | PostgreSQL via **Neon** (serverless Postgres) | Genuinely free tier with **no forced expiry** and no credit card, unlike Render's own free Postgres which **expires ~30–90 days** after creation — Neon is the safer pick for a project that needs the DB alive through the whole SOP evaluation window. [Medium confidence on exact current Render Postgres expiry window — verify on Render's pricing page before final submission, as free-tier terms shift.] | 0.5 GB storage, scale-to-zero, standard Postgres — works with any ORM/driver |
| ORM | SQLAlchemy + Alembic (migrations) | Standard, well-documented, works cleanly with FastAPI | — |
| ML (anomaly detection upgrade) | scikit-learn (Isolation Forest / simple z-score baseline) | No paid inference cost — runs in-process on the backend, not an external API | — |
| Telemetry collector | Python script using `psutil` (interface counters) + `ping3` or subprocess `ping` (latency/loss) | Real, verifiable data — no simulated numbers | Runs on the demo machine(s); no hosting cost |
| Multi-agent orchestration | Plain Python modules/classes with explicit function-call handoffs (Monitoring → Correlation → Diagnosis → Security → Recommendation → Safety Governor), each independently testable | Avoids depending on any paid/metered LLM-agent framework; keeps the "agents" auditable and deterministic for explainability | — |
| Auth (Should Have) | Simple JWT-based session or a single shared admin token in `.env` | Lightweight; this is a course project, not a multi-tenant SaaS | — |
| Containerization | Docker + docker-compose (local dev) | Consistent local dev across 5 team members' machines | — |
| CI (optional stretch) | GitHub Actions free tier (public repo = unlimited free minutes) | Basic lint/test on push | Free for public repos |
| Optional local LLM polish (stretch only) | Ollama running a small local model (e.g., a Llama/Mistral-class model pulled locally) | If the team wants nicer natural-language incident summaries, keep it **local and free**, never a paid/metered API key | Requires a machine with enough RAM; purely optional, must not be a dependency for core functionality |

### Explicitly rejected / avoided
- **Azure paid services** — the team has a college Microsoft account with access to Azure Basic services, but this is kept as a documented fallback option only, not the primary path, per the team's own stated preference for a fully free non-Azure stack.
- **Any paid LLM API** (OpenAI, Anthropic, etc.) for the core pipeline — not needed; diagnosis and recommendation are rule/ML-based and fully explainable without an LLM.
- **Render's own free Postgres** as the primary datastore — usable for quick local testing but not recommended for the project's lifetime datastore due to its expiry window (see table above); use Neon instead.
- **Supabase** as an alternative to Neon was considered — its free projects auto-pause after 7 days of inactivity, which is a worse fit for an intermittently-demoed college project than Neon's scale-to-zero-without-pause-deletion model. [Medium confidence — re-verify both platforms' current auto-pause/expiry behavior close to deployment, since free-tier policies are revised frequently.]

## Repository / Folder Structure

```
netops-copilot-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint
│   │   ├── agents/                  # every "intelligence" module — independently testable
│   │   │   ├── anomaly_detector.py
│   │   │   ├── correlation_engine.py
│   │   │   ├── diagnosis_agent.py
│   │   │   ├── recommendation_agent.py
│   │   │   ├── safety_governor.py
│   │   │   └── security_agent.py
│   │   ├── api/                     # FastAPI routers (one file per resource)
│   │   │   ├── telemetry.py
│   │   │   ├── incidents.py
│   │   │   └── health.py
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── schema.py
│   │   │   ├── telemetry.py
│   │   │   ├── incident.py
│   │   │   └── human_decision.py
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── telemetry.py
│   │   │   └── incident.py
│   │   ├── db/
│   │   │   ├── session.py           # DB engine/session (Neon connection string via env)
│   │   │   └── init_db.py
│   │   └── core/
│   │       ├── config.py            # env var loading (.env)
│   │       └── errors.py            # shared error envelope / exception handlers
│   ├── alembic/                     # DB migrations
│   │   └── versions/
│   ├── tests/
│   │   ├── test_anomaly_detector.py
│   │   ├── test_correlation_engine.py
│   │   ├── test_diagnosis_agent.py
│   │   ├── test_recommendation_agent.py
│   │   ├── test_safety_governor.py
│   │   ├── test_security_agent.py
│   │   └── test_incidents_api.py
│   ├── eval/
│   │   └── run_eval.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── collector/
│   ├── collector.py                 # standalone telemetry collector (psutil + ping)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx             # Overview
│   │   │   ├── incidents/
│   │   │   │   ├── page.tsx         # Incidents list
│   │   │   │   └── [id]/page.tsx    # Incident Detail
│   │   │   ├── history/page.tsx
│   │   │   └── settings/page.tsx    # Should Have
│   │   └── layout.tsx
│   ├── components/
│   │   ├── NetworkHealthBadge.tsx
│   │   ├── MetricCard.tsx
│   │   ├── CausalGraph.tsx
│   │   ├── IncidentCard.tsx
│   │   ├── RecommendationPanel.tsx
│   │   └── ui/                      # shared buttons/inputs/badges
│   ├── lib/
│   │   ├── api.ts                   # fetch wrappers to the backend
│   │   └── types.ts
│   ├── package.json
│   └── .env.example
├── scripts/
│   └── simulate_congestion.py       # synthetic congestion generator for testing/demo
├── docs/
│   ├── PRD.md
│   ├── DESIGN.md
│   ├── TECH_RULES.md
│   ├── ROADMAP.md
│   ├── eval_results.md              # written near submission (see todo.md, TH-003)
│   └── demo_script.md               # written near submission (see ROADMAP.md, Phase 4)
├── todo.md
├── README.md
├── docker-compose.yml               # local dev: backend + local Postgres (prod DB is Neon)
└── .github/
    └── workflows/
        └── ci.yml                   # optional: lint + pytest on push (free for public repos)
```

Notes:
- Every file under `backend/app/agents/` corresponds 1:1 to a module in PRD.md's Functional Requirements — this makes the explainability/auditability claims verifiable by just opening the matching file.
- `docs/PRD.md`, `docs/DESIGN.md`, `docs/TECH_RULES.md`, `docs/ROADMAP.md` are the canonical planning docs (mirrored at the repo root initially for convenience during team setup; move them into `docs/` once the skeleton exists on Day 1).
- `todo.md` stays at the repo root so it's the first thing anyone opens.

## Coding Standards

- **Language versions:** Python 3.11+, Node.js 20 LTS.
- **Naming conventions:** Python — `snake_case` for functions/variables, `PascalCase` for classes; TypeScript/React — `camelCase` for variables/functions, `PascalCase` for components.
- **File organization:** Backend organized by domain (`app/agents/`, `app/api/`, `app/models/`, `app/schemas/`, `app/db/`); frontend organized by feature (`app/(dashboard)/overview`, `app/(dashboard)/incidents`, `components/`, `lib/`).
- **Comment requirements:** Every agent module (`anomaly_detector.py`, `correlation_engine.py`, `diagnosis_agent.py`, `recommendation_agent.py`, `safety_governor.py`) must have a module-level docstring stating its input contract, output contract, and the rule/logic it applies — this is what makes the explainability claims in the PRD auditable.
- **Git workflow:** `main` (always deployable) + `dev` (integration branch) + `feature/<name>` branches per task; PRs into `dev`, merge to `main` only after a working demo checkpoint.

## API Design Standards

- **REST conventions:** Resource-based paths (`/api/telemetry`, `/api/incidents`, `/api/incidents/{id}/decision`), plural nouns, standard verbs (GET/POST/PATCH).
- **Response format:** JSON, consistent envelope:
  ```json
  { "data": { ... }, "error": null }
  ```
  or on failure:
  ```json
  { "data": null, "error": { "code": "string", "message": "string" } }
  ```
- **Error handling:** FastAPI `HTTPException` mapped to the envelope above via a shared exception handler; never leak raw stack traces to the client.
- **Status codes:** `200` success, `201` created, `400` bad request, `401` unauthorized, `404` not found, `422` validation error, `500` unexpected server error.

## Data Models (core schema)

- **Telemetry**: `id, timestamp, source_id, interface, latency_ms, packet_loss_pct, throughput_mbps, bytes_sent, bytes_recv, probe_failed`
- **AnomalyFlag**: `id, telemetry_id, metric, severity_score, detected_at`
- **Incident**: `id, opened_at, closed_at, status (active/acknowledged/dismissed/resolved), severity, probable_cause, confidence, evidence (JSON), correlated_flags (FK list)`
- **Recommendation**: `id, incident_id, action_text, rationale, safe_to_present, created_at`
- **HumanDecision**: `id, incident_id, decision (approve/reject), decided_by, decided_at, notes`
- **IncidentMemory link**: derived via similarity query over `Incident.probable_cause` + evidence signature — no separate table required for MVP; can become its own table if the team implements vector similarity later.

## Security Requirements

- **Authentication:** Dashboard mutating routes (decision, settings) require a valid admin session/token (Should Have; document clearly if MVP demo ships without it due to time).
- **Authorization:** Single-role (admin) for MVP — no multi-role permission matrix needed.
- **Data encryption:** Use HTTPS everywhere in production (Render/Vercel provide this by default on their free tiers); Neon connections use TLS by default.
- **Input validation:** All incoming payloads validated via Pydantic schemas; reject anything outside expected ranges (e.g., negative latency, malformed timestamps) with `422`.
- **Secrets:** Collector-to-backend shared secret, DB connection string, and any auth secret live in environment variables / `.env` (git-ignored) — never committed, never hardcoded.

## Performance Requirements

- **Page load times:** ≤ 3s initial load on the Overview screen on a typical connection (per PRD NFRs).
- **API response times:** `/api/telemetry/latest` ≤ 300ms p95; `/api/incidents` list ≤ 500ms p95 for demo-scale data volumes.
- **Concurrent users:** MVP need only support the demo scenario (a handful of concurrent dashboard viewers) — no dedicated load-testing required, but avoid obviously O(n²) queries on the incident list.

## Testing Requirements

- **Unit test coverage target:** Every agent module (`anomaly_detector`, `correlation_engine`, `diagnosis_agent`, `recommendation_agent`, `safety_governor`) has unit tests covering at least one "should flag/diagnose" case and one "should not flag/diagnose" case, using `pytest`.
- **Integration testing:** At least one end-to-end test that pushes synthetic telemetry through ingest → anomaly → correlation → diagnosis → recommendation and asserts a coherent Incident record is produced.
- **E2E testing:** Manual scripted walkthrough (see `docs/demo_script.md`, to be written closer to demo day) that reproduces a real congestion event (e.g., a large download) and confirms the dashboard reflects it within the KPI latency target from PRD.md.
