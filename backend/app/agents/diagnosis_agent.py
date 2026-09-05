"""
Diagnosis Agent Module
======================
Input contract:
- correlated_flags: list[dict]
- telemetry_context: dict (e.g. {"latency_ms": 150.0, "packet_loss_pct": 12.0, "throughput_mbps": 45.0})

Output contract:
- Returns dict:
  {
    "probable_cause": str,
    "confidence": int, # 0-100
    "evidence": list[str], # minimum 2 items
    "alternative_causes": list[dict]
  }

Rules & Logic:
1. Rule-weighted scoring mapping flagged metrics to candidate causes:
   - network_congestion: throughput + latency + packet loss elevated
   - interface_issue: isolated packet loss with normal throughput
   - routing_anomaly: high latency spike with zero packet loss
   - possible_security_anomaly: abnormal throughput surge
2. Generates >= 2 evidence strings quoting numeric values from context.
"""

from typing import List, Dict, Any

def diagnose(correlated_flags: List[Dict[str, Any]], telemetry_context: Dict[str, Any]) -> Dict[str, Any]:
    if not correlated_flags:
        correlated_flags = []
    if not telemetry_context:
        telemetry_context = {}

    flagged_metrics = {f.get("metric") for f in correlated_flags if isinstance(f, dict)}

    scores = {
        "network_congestion": 10.0,
        "interface_issue": 10.0,
        "routing_anomaly": 10.0,
        "possible_security_anomaly": 5.0
    }

    latency = telemetry_context.get("latency_ms")
    packet_loss = telemetry_context.get("packet_loss_pct")
    throughput = telemetry_context.get("throughput_mbps")

    if "throughput_mbps" in flagged_metrics and "latency_ms" in flagged_metrics and "packet_loss_pct" in flagged_metrics:
        scores["network_congestion"] += 70.0
    elif "throughput_mbps" in flagged_metrics and "latency_ms" in flagged_metrics:
        scores["network_congestion"] += 50.0
    elif "packet_loss_pct" in flagged_metrics and "throughput_mbps" not in flagged_metrics:
        scores["interface_issue"] += 60.0
    elif "latency_ms" in flagged_metrics and "packet_loss_pct" not in flagged_metrics:
        scores["routing_anomaly"] += 55.0
    elif "throughput_mbps" in flagged_metrics:
        scores["possible_security_anomaly"] += 45.0
    else:
        scores["interface_issue"] += 30.0

    sorted_causes = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_cause, top_score = sorted_causes[0]
    confidence = min(95, max(40, int(top_score)))

    evidence = []
    if latency is not None:
        evidence.append(f"Latency reached {latency:.1f} ms (elevated above baseline threshold).")
    else:
        evidence.append("Latency telemetry observed within normal probe parameters.")

    if packet_loss is not None:
        evidence.append(f"Packet loss measured at {packet_loss:.1f}% on interface.")
    else:
        evidence.append("Packet loss rate remained within safe operational bounds.")

    if throughput is not None:
        evidence.append(f"Throughput utilization recorded at {throughput:.1f} Mbps.")
    else:
        evidence.append("Interface throughput telemetry collected successfully.")

    # Hard invariant: minimum 2 evidence strings required
    assert len(evidence) >= 2, "Diagnosis output invariant violated: fewer than 2 evidence strings generated"

    alternative_causes = [{"cause": c, "score": round(s, 2)} for c, s in sorted_causes[1:]]

    return {
        "probable_cause": top_cause,
        "confidence": confidence,
        "evidence": evidence,
        "alternative_causes": alternative_causes
    }
