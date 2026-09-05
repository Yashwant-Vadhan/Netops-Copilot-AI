"""
Anomaly Detector Module (TY-001)
================================
Input contract:
- interface: str
- window_minutes: int = 10
- db: Optional[Session]
- samples: Optional[List[Dict or Telemetry]] (in-memory test support)
- std_multiplier: float = 2.0
- min_samples: int = 30

Output contract:
- Returns dict:
  - If < 30 samples: {"status": "warming_up", "samples_count": N, "flags": []}
  - If >= 30 samples: {"status": "active", "flags": [flag_dict, ...]}
    where each flag is {"metric": str, "severity_score": float, "detected_at": str}
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

METRICS = ["latency_ms", "packet_loss_pct", "throughput_mbps"]


def detect_anomalies(
    interface: str,
    window_minutes: int = 10,
    db: Any = None,
    samples: Optional[List[Any]] = None,
    std_multiplier: float = 2.0,
    min_samples: int = 30
) -> Dict[str, Any]:
    telemetry_records = []

    if samples is not None:
        telemetry_records = samples
    elif db is not None:
        from app.models.telemetry import Telemetry
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        telemetry_records = (
            db.query(Telemetry)
            .filter(Telemetry.interface == interface, Telemetry.timestamp >= cutoff)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

    if len(telemetry_records) < min_samples:
        return {
            "status": "warming_up",
            "samples_count": len(telemetry_records),
            "flags": []
        }

    # Extract dict values
    def get_val(record: Any, key: str) -> Optional[float]:
        if isinstance(record, dict):
            return record.get(key)
        return getattr(record, key, None)

    baseline_records = telemetry_records[:-1]
    latest_record = telemetry_records[-1]
    latest_ts = get_val(latest_record, "timestamp")
    if isinstance(latest_ts, datetime):
        latest_ts_str = latest_ts.isoformat()
    elif isinstance(latest_ts, str):
        latest_ts_str = latest_ts
    else:
        latest_ts_str = datetime.now(timezone.utc).isoformat()

    flags = []

    for metric in METRICS:
        vals = [get_val(r, metric) for r in baseline_records if get_val(r, metric) is not None]
        latest_val = get_val(latest_record, metric)

        if len(vals) < 10 or latest_val is None:
            continue

        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / len(vals)
        std = math.sqrt(variance)

        # Baseline threshold
        threshold = mean + (std_multiplier * std)
        if latest_val > threshold and (latest_val - mean) > 0.01:
            z_score = (latest_val - mean) / std if std > 0 else 2.0
            severity = round(min(5.0, max(1.0, z_score)), 2)
            flags.append({
                "metric": metric,
                "severity_score": severity,
                "detected_at": latest_ts_str,
                "current_value": latest_val,
                "baseline_mean": round(mean, 2)
            })

    return {
        "status": "active",
        "flags": flags
    }