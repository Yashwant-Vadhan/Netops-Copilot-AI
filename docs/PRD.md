# PRD — NetOps Copilot AI

> A Human-in-the-Loop Multi-Agent Platform for Explainable Cloud-Based Network Operations

## Executive Summary

- **Project Name:** NetOps Copilot AI
- **Problem Statement:** Network administrators (and, in this project's context, any small network's admin — a hostel Wi-Fi, a lab LAN, a college department network) receive raw, disconnected metrics (latency, packet loss, throughput) but must manually figure out *why* several symptoms are happening together, *what* is probably wrong, and *what* to do about it. Traditional dashboards show numbers; they don't reason about incidents.
- **Solution Overview:** A cloud-hosted platform that collects real Wi-Fi/Ethernet telemetry, detects abnormal behaviour, correlates related symptoms into a single incident, performs probable root-cause analysis with evidence and a confidence score, estimates impact/severity, recommends an action, and requires human (administrator) approval before anything is treated as "acted upon." Every past incident and its outcome is retained as searchable operational memory.
- **Target Audience:** College network/IT administrators and lab admins as primary users; the SOP evaluators/faculty as a secondary audience who need to see the reasoning ("why congestion, not something else") demonstrated clearly.

## Goals & Objectives

### Business/Academic Goals
- Deliver a demonstrable, end-to-end working system (not slideware) that satisfies the SOP (Societal-Oriented Project) evaluation criteria: real-world relevance, technical depth across multiple CS domains, and a working prototype.
- Show genuine integration of Computer Networks + Cloud Computing + AI/ML + Explainable AI + Multi-agent systems, not a single-domain toy project.
- Ship entirely on free-tier infrastructure — no paid subscriptions, no paid API keys, no credit-card-gated services required for the system to run end-to-end.

### User Goals
- An administrator should be able to glance at a dashboard and know: is the network healthy right now, is there an active incident, why did it happen, how confident is the system, and what should I do about it.
- An administrator should never feel like the system is a black box or that it is silently changing their network.

### Success Metrics (KPIs)
- **Detection latency:** an injected/real anomaly (e.g., latency spike) appears as a flagged incident on the dashboard within **≤ 15 seconds** of the telemetry sample that caused it (given a 5–10s polling interval).
- **Root-cause explainability coverage:** **100%** of raised incidents ship with at least 2 pieces of supporting evidence and a numeric confidence score — no un-explained diagnoses are ever shown.
- **False-incident rate (demo baseline):** on a quiet/idle network, fewer than **1 false incident per 30 minutes** using the tuned threshold/statistical detector.
- **Human-in-the-loop compliance:** **0** code paths exist that apply a "recommended action" without an explicit Approve click stored in the database.
- **End-to-end uptime for demo window:** backend + dashboard reachable and responsive for the full length of the live demo (target **≥ 95%** across rehearsals).
- Note: these are project-defined target KPIs for the SOP evaluation, not externally benchmarked industry figures — record the actual measured numbers in `docs/eval_results.md` before submission rather than presenting these targets as achieved results.

## User Personas

**1. Priya — College Network Administrator**
- Pain Points: Gets "Wi-Fi is slow" complaints with no way to quickly tell if it's congestion, a bad access point, or something else. Has to manually correlate three different monitoring tools.
- Goals: One place that tells her *what's* wrong, *why*, and *what to try*, without her having to dig through raw graphs.

**2. Faculty Evaluator**
- Pain Points: Sees many student projects that are "just a dashboard" or "just an ML prediction demo" with no operational story.
- Goals: Wants to see a coherent pipeline — real data in, reasoned incident out, human decision recorded — that demonstrates depth across networks, cloud, and AI.

**3. Hostel/Lab Student User (indirect)**
- Pain Points: Experiences the slow network but has no visibility into what's being done about it.
- Goals: (Out of scope for MVP UI, but informs why the system exists — implicitly served by the admin persona resolving issues faster.)

## User Stories

### Telemetry & Monitoring
- As an admin, I want to see current latency, packet loss, throughput, and interface stats for my monitored interface so that I know the live network state.
- As an admin, I want historical graphs of these metrics so I can see trends, not just a snapshot.

### Incident Detection & Correlation
- As an admin, I want the system to automatically flag abnormal behaviour (not require me to eyeball thresholds) so that I don't miss slow degradations.
- As an admin, I want related symptoms (traffic spike + packet loss + latency spike) grouped into **one incident**, not five separate alerts, so I'm not overwhelmed by alert fragmentation.

### Diagnosis & Explainability
- As an admin, I want a probable root cause with a confidence percentage so I know how much to trust the diagnosis.
- As an admin, I want the specific evidence behind the diagnosis (e.g., "bandwidth increased by 72%") so I can verify the reasoning myself.

### Recommendation & Human-in-the-Loop
- As an admin, I want a recommended next action in plain language so I know what to try.
- As an admin, I want to explicitly Approve or Reject every recommendation — the system must never act on its own — so that I stay in control of my network.

### Incident Memory
- As an admin, I want to see if a similar incident happened before and what worked, so I can resolve repeat problems faster.

### Security (secondary)
- As an admin, I want the system to flag traffic patterns that look potentially suspicious (as distinct from ordinary congestion) so I have an early, low-confidence signal — with an explicit caveat that this is not a substitute for a real IDS/IPS.

## Functional Requirements

### Module 1 — Telemetry Collection
- **Description:** A Python collector reads live network interface counters and derived metrics from the machine it runs on (or a lightweight agent per monitored host) and pushes them to the backend.
- **Inputs:** OS network-interface counters (via `psutil`), ping RTT to a configured target (gateway/DNS), optional periodic throughput sample.
- **Outputs:** A telemetry record (see schema in TECH_RULES.md) POSTed to `/api/telemetry/ingest` every N seconds (default 5s, configurable).
- **User Actions:** Admin configures which interface + ping target + polling interval via a `.env`/config file.
- **Validation Rules:** Every record must include `timestamp`, `interface`, and at least `latency_ms` OR `packet_loss_pct` — records missing all metric fields are rejected with `422`.
- **Edge Cases:** Target host unreachable (ping timeout) → record `latency_ms: null`, `packet_loss_pct: 100`, flag `probe_failed: true`; interface renamed/disconnected mid-run → collector logs and retries with backoff, does not crash.

### Module 2 — Telemetry Storage & Retrieval API
- **Description:** FastAPI backend persists telemetry and exposes read endpoints.
- **Inputs:** Telemetry POSTs from Module 1.
- **Outputs:** `GET /api/telemetry/latest`, `GET /api/telemetry/history?minutes=60`.
- **Validation Rules:** Pydantic schema validation on ingest; reject payloads with out-of-range values (e.g., negative latency).
- **Edge Cases:** Burst of telemetry from multiple collectors (multi-host, stretch goal) — each record tagged with a `source_id` so streams don't collide.

### Module 3 — Anomaly Detection
- **Description:** Compares each new telemetry record (and a rolling window) against a learned/rule-based baseline.
- **Inputs:** Rolling window of recent telemetry (e.g., last 5–10 minutes).
- **Outputs:** An `anomaly_flag` per metric (latency/packet_loss/throughput/utilization) with a severity score.
- **User Actions:** None directly — runs automatically on a schedule/on ingest.
- **Validation Rules:** Baseline must warm up on ≥ N samples (e.g., 30) before flagging; cold-start period shows "Learning baseline…" instead of false incidents.
- **Edge Cases:** Sudden legitimate traffic (e.g., a large download the admin expects) — the system still flags it (it cannot know intent) but the explanation must make this legible so the admin can quickly recognize and reject it.

### Module 4 — Correlation Engine
- **Description:** Groups multiple concurrent/sequential anomaly flags (within a configurable time window, e.g., 30s) into a single incident with an ordered symptom chain.
- **Inputs:** Stream of anomaly flags from Module 3.
- **Outputs:** An `Incident` record with an ordered list of correlated symptoms and timestamps.
- **Validation Rules:** A single isolated anomaly flag with no correlated symptoms after the window still becomes a (low-confidence) incident, not silently dropped.
- **Edge Cases:** Two unrelated anomalies overlapping in time (e.g., a real traffic spike and, independently, a flaky interface) — correlation confidence should reflect the ambiguity rather than force a single narrative.

### Module 5 — Root-Cause / Diagnosis Agent
- **Description:** Given a correlated incident, ranks candidate causes (Network Congestion, Interface Issue, Routing Anomaly, Possible Security Anomaly) using rule-weighted scoring over the evidence, and returns the top cause with a confidence percentage.
- **Outputs:** `probable_cause`, `confidence` (0–100), ranked list of alternative causes with their scores.
- **Validation Rules:** Confidence must always be accompanied by ≥ 2 evidence bullet points; the system never returns a bare label with no evidence.

### Module 6 — Explainability Layer
- **Description:** Renders the diagnosis as Cause + Evidence + Confidence + Impact, and a causal chain graph (Traffic Spike → High Utilization → Packet Loss → High Latency).
- **Outputs:** Structured explanation object consumed by the dashboard's Diagnosis Panel and Causal Graph component.

### Module 7 — Impact / Severity Estimation
- **Description:** Scores incident severity (LOW/MEDIUM/HIGH/CRITICAL) from magnitude, duration, and number of correlated symptoms.
- **Outputs:** `severity` field on the Incident record, used for sorting/prioritizing the incident list.

### Module 8 — Recommendation Agent
- **Description:** Maps `(probable_cause, severity)` to a recommended action from a curated, explainable rule table (e.g., Congestion → "Investigate the high-bandwidth source; consider traffic prioritization").
- **Outputs:** `recommended_action` (text) + `rationale` (why this action, tied back to the evidence).
- **Validation Rules:** Recommendation text must never claim certainty ("this will fix it") — always framed as decision support.

### Module 9 — Safety Governor
- **Description:** A rule-based gate that runs before any recommendation is shown/actioned — checks the recommendation against a safety policy (e.g., never recommend disabling an interface with active sessions above a threshold; never mark anything as "auto-applied").
- **Outputs:** `safe_to_present: bool`, and (if applicable) a downgraded/softened recommendation text.

### Module 10 — Human-in-the-Loop Approval
- **Description:** Presents the recommendation with Approve/Reject buttons; persists the admin's decision and timestamp; nothing is ever auto-applied to the network.
- **Outputs:** `HumanDecision` record linked to the Incident.
- **Validation Rules:** An incident cannot be marked "Resolved" without a stored human decision.

### Module 11 — Incident Memory
- **Description:** Stores every incident + diagnosis + recommendation + human decision + (manually logged) outcome; on a new incident, searches for similar past incidents (by cause + evidence signature) and surfaces them.
- **Outputs:** `GET /api/incidents/{id}/similar`.

### Module 12 — Dashboard (Admin UI)
- **Description:** Next.js web app showing network health, live + historical metrics, active incidents, diagnosis, causal graph, recommendation with Approve/Reject, and incident history.

## Non-Functional Requirements

- **Performance:** Dashboard initial load ≤ 3s on a typical broadband connection; `/api/telemetry/latest` responds ≤ 300ms p95 under demo load.
- **Scalability:** MVP targets a single monitored interface/host; architecture should not hard-code "one collector" assumptions so a second collector (multi-host) is addable later without a schema rewrite.
- **Security:** Backend endpoints that mutate state (Approve/Reject, config) require a simple admin auth (token or session — see TECH_RULES.md); telemetry ingest endpoint uses a shared collector secret, not open to the public internet.
- **Accessibility:** Dashboard aims for WCAG 2.1 **AA** on core screens (color contrast on severity badges, keyboard-operable Approve/Reject buttons).
- **Reliability:** No single component failure (e.g., collector offline) should crash the dashboard — it must show a clear "no recent telemetry" state instead of erroring.
- **Maintainability:** Every intelligence module (anomaly detector, correlation engine, root-cause, recommendation, safety governor) is a separate, independently testable Python module with a documented input/output contract.

## Assumptions & Constraints

- **No paid services of any kind** are required for the system to run end-to-end. Azure Basic services (via the team's college Microsoft account) are available as an *optional* alternative but are **not** the primary target — the team has chosen fully free non-Azure hosting (Render + Vercel + Neon Postgres, all free tiers) as the deployment target, per team decision.
- No LLM API (paid or free-tier-limited) is required for the core pipeline — diagnosis, correlation, and recommendations are rule/statistics/ML-based (scikit-learn), which keeps the system fully free and deterministic/explainable. An LLM-based natural-language explanation polish is an optional, clearly-labeled stretch goal only, using a genuinely free option (e.g., a local Ollama model) — never a metered paid key.
- The team does **not** have authorization to modify the college's production router/network — the Human-in-the-Loop step is demonstrated as "decision recorded," not "network actually reconfigured." This is explicitly stated as a scope boundary, not hidden.
- Real telemetry is collected from whatever Wi-Fi/Ethernet interface the demo machine(s) use; the system must gracefully degrade to controlled test conditions (e.g., a deliberate large download to induce a real, if small-scale, congestion event) for demonstration purposes, since a college network cannot be deliberately overloaded to prove detection.
- Team size: 5. Aggressive/compressed timeline ("as early as possible") — see ROADMAP.md and todo.md for the resulting scope trade-offs.

## MVP Scope

### Must Have
- Real telemetry collection (latency, packet loss, throughput, interface stats) from at least one live interface.
- FastAPI backend with telemetry ingest + retrieval endpoints, Postgres storage.
- Next.js dashboard: live metrics, historical chart, network health badge.
- Threshold/statistical anomaly detection (no ML dependency required for MVP).
- Correlation engine grouping symptoms into one incident.
- Rule-weighted root-cause ranking with confidence + evidence.
- Explainability panel (Cause + Evidence + Confidence) and a simple causal chain visual.
- Rule-table recommendation engine.
- Human Approve/Reject UI wired to a persisted decision.
- Incident list/history page.
- Dockerized backend + documented free-tier deployment (Render + Vercel + Neon).

### Should Have
- Severity/impact scoring (LOW/MEDIUM/HIGH/CRITICAL).
- Incident Memory similarity search ("similar past incident found").
- Safety Governor as an explicit, visible gate step (not just implicit logic).
- ML-based anomaly detection upgrade (Isolation Forest) alongside the rule-based baseline, with a toggle to compare both.
- Security Agent producing a low-confidence "possible suspicious pattern" flag, clearly caveated.
- Basic auth on the dashboard/admin actions.

### Nice To Have
- Multi-interface / multi-host telemetry (more than one collector reporting in).
- CSV/JSON export of incident history.
- Optional local-LLM-generated natural-language incident summary (clearly labeled as a generated summary of the same evidence, not a new source of truth).
- Notification (e.g., email via a free transactional-email tier) when a HIGH/CRITICAL incident is raised.

## Future Enhancements

- Multi-agent orchestration formalized with explicit agent-to-agent message passing (rather than direct function calls) if the team wants to demonstrate a more literal "multi-agent system" for viva/evaluation depth.
- Packet-level analysis via Scapy/PyShark for deeper root-cause evidence (e.g., identifying a specific noisy protocol/talker).
- Real controlled remediation on a lab-only, non-production test network segment, if the department can provide one, to demonstrate the loop closing beyond "decision recorded."
