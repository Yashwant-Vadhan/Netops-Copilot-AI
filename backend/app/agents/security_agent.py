"""
Security Agent Module (TV-003)
==============================
A secondary, low-confidence heuristic detector that scans rolling telemetry windows
for abnormal traffic patterns (e.g., massive outbound bursts, unusual upload-to-download
ratios, or abnormal throughput spikes) that might indicate data exfiltration, port scanning,
or botnet activity.

Design Invariants:
1. Always ships with an explicit caveat stating this is a heuristic signal and NOT
   a substitute for a dedicated IDS/security tool.
2. Confidence score is STRICTLY capped at <= 40% to prevent over-reliance on heuristic signals.

Input contract:
- telemetry_window: list[dict]
    A chronological list of recent telemetry records (min 2 for baseline comparison).
    Each dict contains: "bytes_sent", "bytes_recv", "throughput_mbps", "latency_ms", "timestamp".

Output contract:
- If suspicious pattern detected:
    {
      "flag": "possible_suspicious_pattern",
      "confidence": int,  # 0 to 40 inclusive (hard cap)
      "caveat": str,       # Mandatory disclaimer
      "reason": str        # Contextual explanation of the detected anomaly
    }
- If nominal:
    None

Rules & Logic:
1. Baseline calculation: Computes average outbound bytes/sec and ratio over the initial window.
2. Anomaly triggers:
   - High Outbound Ratio: Outbound bytes sent surge > 4x the historical baseline while download remains low.
   - Sudden Outbound Spike: Delta bytes_sent in the latest sample exceeds mean + 3*std of the window.
3. Max confidence cap: min(40, calculated_confidence).
"""

from typing import List, Dict, Any, Optional
import math

MANDATORY_CAVEAT = (
    "This is a low-confidence heuristic signal, not a substitute for a dedicated "
    "security/IDS tool - investigate independently before acting."
)
MAX_CONFIDENCE_CAP = 40


def scan(telemetry_window: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Scans recent telemetry window for unusual outbound traffic spikes.
    Returns anomaly flag with caveat if triggered, or None if nominal.
    """
    if not telemetry_window or len(telemetry_window) < 3:
        # Insufficient data to form a heuristic baseline
        return None

    # Extract outbound metrics
    outbound_series = []
    inbound_series = []
    throughput_series = []

    for item in telemetry_window:
        if isinstance(item, dict):
            bs = item.get("bytes_sent") or 0
            br = item.get("bytes_recv") or 0
            tp = item.get("throughput_mbps") or 0.0
            outbound_series.append(float(bs))
            inbound_series.append(float(br))
            throughput_series.append(float(tp))

    if len(outbound_series) < 3:
        return None

    # Calculate deltas for outbound traffic
    outbound_deltas = [
        max(0.0, outbound_series[i] - outbound_series[i - 1])
        for i in range(1, len(outbound_series))
    ]
    inbound_deltas = [
        max(0.0, inbound_series[i] - inbound_series[i - 1])
        for i in range(1, len(inbound_series))
    ]

    if not outbound_deltas:
        return None

    latest_out_delta = outbound_deltas[-1]
    latest_in_delta = inbound_deltas[-1] if inbound_deltas else 1.0
    baseline_out_deltas = outbound_deltas[:-1]

    mean_out = sum(baseline_out_deltas) / len(baseline_out_deltas) if baseline_out_deltas else 0.0
    variance = (
        sum((x - mean_out) ** 2 for x in baseline_out_deltas) / len(baseline_out_deltas)
        if baseline_out_deltas
        else 0.0
    )
    std_out = math.sqrt(variance)

    triggered = False
    reasons = []
    raw_confidence = 20

    # Heuristic 1: Outbound burst exceeds 3x baseline mean + 2 std
    if mean_out > 0 and latest_out_delta > (mean_out * 3.0 + 2 * std_out) and latest_out_delta > 500_000:
        triggered = True
        multiplier = round(latest_out_delta / mean_out, 1)
        reasons.append(f"Outbound byte burst is {multiplier}x the baseline average.")
        raw_confidence += 15

    # Heuristic 2: Extreme upload-to-download ratio (e.g. huge outbound upload with tiny inbound)
    if latest_out_delta > 1_000_000 and (latest_out_delta / max(1.0, latest_in_delta)) > 10.0:
        triggered = True
        reasons.append("Extreme upload-to-download traffic asymmetry detected.")
        raw_confidence += 15

    # Heuristic 3: Sudden high throughput spike in telemetry
    latest_tp = throughput_series[-1] if throughput_series else 0.0
    if latest_tp > 80.0 and len(throughput_series) >= 3:
        tp_baseline = sum(throughput_series[:-1]) / (len(throughput_series) - 1)
        if latest_tp > tp_baseline * 4.0:
            triggered = True
            reasons.append(f"Throughput surge ({latest_tp:.1f} Mbps vs baseline {tp_baseline:.1f} Mbps).")
            raw_confidence += 10

    if not triggered:
        return None

    # Enforce strict confidence cap <= 40
    final_confidence = min(MAX_CONFIDENCE_CAP, int(raw_confidence))
    assert final_confidence <= MAX_CONFIDENCE_CAP, f"Invariant violated: confidence {final_confidence} > {MAX_CONFIDENCE_CAP}"

    return {
        "flag": "possible_suspicious_pattern",
        "confidence": final_confidence,
        "caveat": MANDATORY_CAVEAT,
        "reason": " ".join(reasons)
    }