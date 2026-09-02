# NetOps Copilot AI

A human-in-the-loop, multi-agent platform that turns raw network telemetry into an **explainable** incident diagnosis — probable cause, evidence, confidence, severity, and a recommended action — with a human administrator always in control of the final decision.

Built as a Societal-Oriented Project (SOP) by a 5-person team: Yashwant Vadhan M, M A Sushil Kumar, Yaashwanth S K P, Vishal Khanna Chandra Sekaran, Harish T.

## Why this exists

Standard network monitoring dashboards show you numbers. They don't tell you *why* latency, packet loss, and throughput are all misbehaving at once, *how confident* you should be in a guess, or *what to do* about it — and no admin wants a black-box system silently making changes to their network. NetOps Copilot AI closes that gap: real telemetry in, a reasoned and evidence-backed incident out, and a human decision recorded before anything is treated as "handled."

## Documentation

| Doc | What's in it |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Problem statement, goals/KPIs, personas, user stories, functional & non-functional requirements, MVP scope |
| [`docs/DESIGN.md`](docs/DESIGN.md) | Screens, user flows, design system (colors/type/spacing), accessibility requirements |
| [`docs/TECH_RULES.md`](docs/TECH_RULES.md) | Tech stack + rationale, repository folder structure, coding/API/security/testing standards |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 4-phase, 21-day build plan with milestones and a risk register |

## How it works (high level)

```
Real Wi-Fi/Ethernet telemetry (collector.py)
        ↓  POST every 5s
Backend ingest + storage (FastAPI + Neon Postgres)
        ↓
Anomaly Detection  →  Correlation Engine  →  Diagnosis Agent
        ↓                                          ↓
Severity/Impact Scoring                    Explainability Layer
        ↓                                          ↓
Recommendation Agent  →  Safety Governor  →  Dashboard (Next.js)
                                                    ↓
                                    Admin reviews evidence + Approves/Rejects
                                                    ↓
                                    Decision persisted — nothing is ever auto-applied
```

A secondary **Security Agent** runs alongside this chain producing a clearly-caveated, low-confidence "possible suspicious pattern" signal — it is explicitly not a substitute for a real IDS/IPS.

## Tech stack (100% free tier)

- **Frontend:** Next.js + Tailwind + Recharts → deployed on **Vercel** (free)
- **Backend:** FastAPI (Python) → deployed on **Render** (free Web Service)
- **Database:** PostgreSQL via **Neon** (free, no forced expiry — chosen over Render's own free Postgres, which expires)
- **ML:** scikit-learn, in-process — no external/paid LLM API required anywhere in the core pipeline
- **Collector:** standalone Python script (`psutil` + ping) reading real interface telemetry

Full rationale and the complete repository folder structure are in [`docs/TECH_RULES.md`](docs/TECH_RULES.md). An Azure Basic deployment (via the team's college Microsoft account) is documented as an optional fallback only — the primary target is the fully free stack above.

## Getting started

```bash
git clone https://github.com/Yashwant-Vadhan/Netops-Copilot-AI
cd Netops-Copilot-AI
cp backend/.env.example backend/.env      # fill in DATABASE_URL, COLLECTOR_SECRET
cp collector/.env.example collector/.env  # fill in BACKEND_URL, TARGET_HOST
docker-compose up                         # local backend + local Postgres
```

Then, in separate terminals:
```bash
cd collector && python collector.py       # starts pushing real telemetry
cd frontend && npm install && npm run dev # dashboard at http://localhost:3000
```

To test the full reasoning pipeline without waiting for a real network event:
```bash
python scripts/simulate_congestion.py --duration 120 --severity medium
```

## Project status

Follow along in [`docs/ROADMAP.md`](docs/ROADMAP.md) for milestones. Evaluation results against the PRD's KPIs will be published in `docs/eval_results.md` ahead of submission.

## Scope & honesty notes

- The team does not have authorization to reconfigure the college's production network — the human-in-the-loop step demonstrates "decision recorded," not "network automatically changed." This is a deliberate scope boundary, stated here rather than glossed over.
- All target KPIs in PRD.md are project-defined evaluation goals, not achieved results — see `docs/eval_results.md` for actual measured numbers once available.
