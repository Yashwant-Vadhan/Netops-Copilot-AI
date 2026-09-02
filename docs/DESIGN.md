# DESIGN — NetOps Copilot AI

## Design Philosophy

- **Visual Style:** A NOC (Network Operations Center) console feel — dark-mode-first, information-dense but not cluttered, status-color-driven (green/amber/red), monospace accents for metric values to evoke a technical console without looking like a spreadsheet.
- **Branding Direction:** Understated and technical rather than playful — this is a tool for an administrator making decisions under mild time pressure, not a consumer app. Avoid heavy illustration; favor clean data density.
- **UX Goals:**
  1. The admin can answer "is everything OK?" in under 2 seconds from the top of the dashboard.
  2. Every AI claim (cause, confidence) is never more than one glance away from its evidence.
  3. The Approve/Reject action is always visually distinct and impossible to trigger accidentally (confirm-on-click for Reject-with-consequence flows is not required for MVP, but the buttons must not sit adjacent to any other primary action).

## Information Architecture

### Navigation Structure
A single admin app with a persistent left sidebar (or top bar on mobile):
- **Overview** (default landing) — network health + live metrics + active incidents summary
- **Incidents** — full incident list (active + historical), filterable by severity/status
- **Incident Detail** (drill-in from Incidents) — diagnosis, evidence, causal graph, recommendation, approve/reject, similar past incidents
- **History / Metrics** — longer-range historical charts
- **Settings** (Should Have) — collector/threshold config, auth

### Screen Hierarchy
```
Overview (/)
 ├─ Incidents (/incidents)
 │   └─ Incident Detail (/incidents/[id])
 ├─ History (/history)
 └─ Settings (/settings)            [Should Have]
```

### User Flow — Primary Path
```
Admin opens dashboard
      ↓
Sees Network Health = DEGRADED + 1 Active Incident badge
      ↓
Clicks into Incident Detail
      ↓
Reads: Probable Cause, Confidence, Evidence list, Causal Graph
      ↓
Reads: Recommended Action + rationale
      ↓
Clicks APPROVE or REJECT
      ↓
Decision recorded, incident status updates (Acknowledged/Dismissed)
      ↓
Incident moves into History with outcome field editable later
```

## Screen Specifications

### 1. Overview
- **Purpose:** At-a-glance network health and current incident awareness.
- **Components:** Network Health badge (GOOD/DEGRADED/CRITICAL), 4 MetricCards (Latency, Packet Loss, Throughput, Utilization) each with current value + mini sparkline, an Active Incidents strip (0–N incident chips sorted by severity), a primary historical chart (last 1h latency + packet loss overlay).
- **Layout Structure:** Health badge full-width top banner; 4 MetricCards in a responsive grid below it; Active Incidents strip beneath; historical chart occupies the lower half.
- **Interactions:** Clicking an incident chip navigates to Incident Detail. Hovering a MetricCard sparkline shows exact recent values in a tooltip.
- **Empty State:** No incidents → "No active incidents — network nominal" with a subtle green check, still shows metrics.
- **Error State:** Backend unreachable → banner: "Can't reach the telemetry service — showing last known data from [timestamp]" (never a blank screen).
- **Loading State:** Skeleton cards for the 4 metrics + skeleton chart on first load; subsequent polling updates are silent (no flicker/skeleton on refresh).
- **Responsive Behavior:** MetricCards collapse from 4-across to 2-across (tablet) to 1-across (mobile); chart becomes horizontally scrollable on mobile rather than squeezed.

### 2. Incidents (list)
- **Purpose:** Browse and triage all incidents, active and resolved.
- **Components:** Filter bar (status: Active/Acknowledged/Dismissed/Resolved; severity: LOW–CRITICAL), sortable table/list (Time, Cause, Confidence, Severity, Status).
- **Layout Structure:** Filter bar top, list/table below, pagination or infinite scroll if the list is long.
- **Interactions:** Row click → Incident Detail. Column header click → sort.
- **Empty State:** "No incidents match this filter."
- **Error State:** Same reach-failure banner pattern as Overview.
- **Loading State:** Skeleton rows.
- **Responsive Behavior:** Table collapses into stacked cards on mobile (one card per incident, key fields only).

### 3. Incident Detail
- **Purpose:** The core explainability + decision screen.
- **Components:** Header (cause + confidence badge + severity badge + timestamp), Evidence list (checkmarked bullet list), Causal Graph (see Component Library below), Recommendation Panel (action text + rationale + Approve/Reject buttons), Similar Past Incidents panel (Should Have), Human Decision history (once decided).
- **Layout Structure:** Two-column on desktop — left column: diagnosis + evidence + causal graph; right column: recommendation + decision + similar incidents. Single column, stacked, on mobile (diagnosis first, decision last).
- **Interactions:** Approve/Reject buttons are large, clearly labeled, color-coded (Approve = confirming green outline, Reject = neutral gray outline — deliberately **not** red, since rejecting isn't an error, just a decision); once clicked, buttons disable and show the recorded decision + timestamp.
- **Empty State:** N/A (only reached via an existing incident).
- **Error State:** If decision POST fails, buttons re-enable with an inline "Couldn't save your decision — try again" message; never silently drop the click.
- **Loading State:** Skeleton for diagnosis/evidence while incident detail loads.
- **Responsive Behavior:** Causal Graph switches from horizontal chain (desktop) to vertical chain (mobile).

### 4. History (metrics)
- **Purpose:** Longer time-range exploration for context/troubleshooting outside an active incident.
- **Components:** Time-range picker (1h/6h/24h/7d), multi-metric line chart with toggleable series.
- **Layout Structure:** Range picker top, chart below, full width.
- **Interactions:** Toggle chips to show/hide each metric series.
- **Empty State:** "No telemetry recorded yet for this range."
- **Loading/Error/Responsive:** Same patterns as Overview's chart.

### 5. Settings (Should Have)
- **Purpose:** Configure collector target, thresholds, and basic auth.
- **Components:** Form fields for ping target, polling interval, anomaly thresholds; simple login/token management.
- **States:** Standard form validation states (inline field errors), save confirmation toast.

## Design System

### Colors
| Token | Hex | Use |
|---|---|---|
| `--bg-base` | `#0B1120` | App background (dark mode primary) |
| `--bg-surface` | `#121A2C` | Card/panel surfaces |
| `--bg-surface-raised` | `#1A2438` | Hover/raised elements |
| `--text-primary` | `#E6EAF2` | Primary text |
| `--text-secondary` | `#8B96AB` | Secondary/meta text |
| `--border` | `#243049` | Card borders, dividers |
| `--accent` | `#3B82F6` | Links, primary actions, focus rings |
| `--status-good` | `#22C55E` | Network Health: GOOD, Approve |
| `--status-degraded` | `#F59E0B` | Network Health: DEGRADED, MEDIUM severity |
| `--status-critical` | `#EF4444` | Network Health: CRITICAL, HIGH/CRITICAL severity |
| `--status-neutral` | `#64748B` | Reject, dismissed states |

### Typography
- **Font families:** UI/body — `Inter` (system-ui fallback); metric values / monospace-flavored numbers — `JetBrains Mono` (or `ui-monospace` fallback) to reinforce the "console" feel for latency/percentage figures.
- **Scale:** `12 / 14 / 16 / 20 / 24 / 32` px, base 16px.
- **Weights:** 400 body, 500 labels/buttons, 600 headings/metric values.

### Spacing
- Base unit: **4px**. Scale: 4, 8, 12, 16, 24, 32, 48, 64.

### Grid System
- 12-column grid, 24px gutters on desktop, 16px on tablet, single-column stack on mobile.
- Breakpoints: `mobile < 640px`, `tablet 640–1024px`, `desktop > 1024px`.

### Component Library
- **Buttons:** Primary (accent-filled), Secondary (outline), Approve (status-good outline, fills on hover), Reject (status-neutral outline). States: default, hover, active, disabled, loading (spinner replaces label).
- **Inputs:** Standard text/number/select with label-above pattern; states: default, focus (accent ring), error (red border + inline message), disabled.
- **Cards:** MetricCard (value + label + sparkline + trend arrow), IncidentCard (severity badge + cause + timestamp + status chip).
- **Tables:** Sticky header, zebra-striping optional, row hover highlight, sortable column headers with a small caret indicator.
- **Modals:** Reserved for destructive/irreversible actions only (none in MVP — Approve/Reject are inline, not modal, since they are reviewable decisions, not destructive ones).
- **Notifications/Toasts:** Bottom-right, auto-dismiss after 4s for success, persistent-until-dismissed for errors.
- **Causal Graph component:** A simple horizontal (desktop) / vertical (mobile) chain of connected nodes, each node = symptom name + small icon + timestamp offset (e.g., "+2s"), connected by directional arrows; built as a lightweight custom SVG/React component (no heavy graph library needed for a linear chain — reserve a real graph library only if the team wants to render branching causal graphs later).

## Accessibility Requirements

- **WCAG Compliance Level:** AA target for all core screens (Overview, Incidents, Incident Detail).
- **Keyboard Navigation:** All interactive elements (nav links, table rows, Approve/Reject, filters) reachable via Tab in logical order; Approve/Reject also triggerable via Enter/Space when focused.
- **Screen Reader Support:** Severity/status badges carry `aria-label`s spelling out the state (not color alone); the causal graph chain has a text-equivalent list rendered for screen readers alongside the visual chain.
- **Color Contrast Ratios:** Status colors chosen/tested against `--bg-surface` to meet ≥ 4.5:1 for text and ≥ 3:1 for large text/icons.

## Micro-interactions

- **Hover Effects:** Cards lift slightly (subtle shadow) on hover; sparkline tooltips fade in.
- **Page Transitions:** Simple fade/slide (150–200ms) between routes — no heavy animation that would slow down an admin trying to react quickly.
- **Loading Animations:** Skeleton shimmer for first loads; a subtle pulsing dot on the Network Health badge while a fresh poll is in flight.
- **Success States:** Toast + a brief highlight flash on the Incident Detail decision area after Approve/Reject saves successfully.
- **Error States:** Inline red text + retry affordance; never a silent failure.

## Mobile Responsiveness Strategy

- **Breakpoints:** as defined in Grid System above.
- **Layout shifts:** Two-column Incident Detail → single column (diagnosis stack first, decision area last but still reachable without excessive scrolling — keep Approve/Reject within the first two screen-heights on mobile).
- **Touch targets:** Minimum 44×44px for Approve/Reject and all nav/filter controls, per standard mobile accessibility guidance.
