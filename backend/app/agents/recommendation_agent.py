"""
Recommendation Agent Module
===========================
Input contract:
- probable_cause: str
- severity: str (low | medium | high | critical)
- evidence: list[str]

Output contract:
- Returns dict:
  {
    "action_text": str,
    "rationale": str
  }

Rules & Logic:
1. Maps cause + severity to actionable guidance.
2. Text MUST be phrased as decision support (never using banned certainty terms: "will fix", "guaranteed", "definitely").
3. Safe generic fallback for unknown causes.
"""

from typing import List, Dict, Any

BANNED_CERTAINTY_WORDS = ["will fix", "guaranteed", "definitely"]

RULE_TABLE = {
    "network_congestion": {
        "action_text": "Investigate high-bandwidth processes and consider applying QoS rate limiting or traffic shaping on the active interface.",
        "rationale": "Sustained high throughput combined with latency spikes indicates link saturation."
    },
    "interface_issue": {
        "action_text": "Inspect physical link health, check interface error counters, and consider re-seating cable connections.",
        "rationale": "Isolated packet loss without throughput spikes points to hardware or physical layer signal degradation."
    },
    "routing_anomaly": {
        "action_text": "Examine BGP/OSPF routing tables and traceroute hops to identify downstream latency bottlenecks.",
        "rationale": "High latency without packet loss suggests suboptimal routing or path congestion outside local segment."
    },
    "possible_security_anomaly": {
        "action_text": "Review netflow logs and inspect top talker IPs for unauthorized outbound burst patterns.",
        "rationale": "Abnormal throughput surge inconsistent with baseline usage warrants secondary security audit."
    }
}

DEFAULT_RECOMMENDATION = {
    "action_text": "Review general interface status and monitor telemetry logs for recurring anomaly patterns.",
    "rationale": "Unclassified anomaly requires standard operational review."
}

def recommend(probable_cause: str, severity: str, evidence: List[str]) -> Dict[str, str]:
    entry = RULE_TABLE.get(probable_cause, DEFAULT_RECOMMENDATION)
    action_text = entry["action_text"]
    rationale = f"{entry['rationale']} Evidence noted: {'; '.join(evidence[:2]) if evidence else 'Telemetry flags'}"

    # Verify banned certainty words do not exist
    for banned in BANNED_CERTAINTY_WORDS:
        assert banned not in action_text.lower(), f"Banned certainty word '{banned}' found in recommendation action_text"

    return {
        "action_text": action_text,
        "rationale": rationale
    }
