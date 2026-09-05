"""
Correlation Engine Module
=========================
Input contract:
- flags: list of anomaly flag dicts, e.g.:
  [
    {"id": int, "telemetry_id": int, "metric": str, "severity_score": float, "detected_at": "ISO-8601 string or datetime"},
    ...
  ]
- window_seconds: int = 30 (time window within which flags are considered correlated)

Output contract:
- Returns list of correlated cluster dicts:
  [
    {
      "correlated_flags": [flag_dict, ...],
      "symptom_chain": [
        {"metric": "latency_ms", "offset_seconds": 0.0, "severity_score": 2.5},
        {"metric": "packet_loss_pct", "offset_seconds": 5.2, "severity_score": 3.0}
      ]
    },
    ...
  ]

Rules & Logic:
1. Sort flags chronologically by `detected_at`.
2. Group flags into clusters via chained grouping: a flag belongs to the current cluster if its `detected_at` is within `window_seconds` of the previous flag in the cluster.
3. For each cluster, compute relative `offset_seconds` for each flag from the cluster's earliest timestamp.
4. Single-flag clusters (size 1) produce a valid cluster payload.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any

def _parse_datetime(dt_val: Any) -> datetime:
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val
    if isinstance(dt_val, str):
        # Handle trailing Z
        clean_str = dt_val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    raise ValueError(f"Cannot parse datetime from: {dt_val}")

def correlate(flags: List[Dict[str, Any]], window_seconds: int = 30) -> List[Dict[str, Any]]:
    if not flags:
        return []

    # Sort flags by detected_at timestamp
    sorted_flags = sorted(flags, key=lambda f: _parse_datetime(f["detected_at"]))

    clusters: List[List[Dict[str, Any]]] = []
    current_cluster: List[Dict[str, Any]] = [sorted_flags[0]]

    for flag in sorted_flags[1:]:
        prev_flag_dt = _parse_datetime(current_cluster[-1]["detected_at"])
        curr_flag_dt = _parse_datetime(flag["detected_at"])

        if (curr_flag_dt - prev_flag_dt).total_seconds() <= window_seconds:
            current_cluster.append(flag)
        else:
            clusters.append(current_cluster)
            current_cluster = [flag]
    
    if current_cluster:
        clusters.append(current_cluster)

    result = []
    for cluster in clusters:
        base_dt = _parse_datetime(cluster[0]["detected_at"])
        symptom_chain = []
        for flag in cluster:
            flag_dt = _parse_datetime(flag["detected_at"])
            offset = round((flag_dt - base_dt).total_seconds(), 2)
            symptom_chain.append({
                "metric": flag.get("metric", "unknown"),
                "offset_seconds": offset,
                "severity_score": flag.get("severity_score", 1.0),
                "detected_at": flag.get("detected_at")
            })

        result.append({
            "correlated_flags": cluster,
            "symptom_chain": symptom_chain
        })

    return result
