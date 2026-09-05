import pytest
from datetime import datetime, timezone, timedelta
from app.agents.correlation_engine import correlate

def test_correlate_flags_within_window():
    base_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    flags = [
        {"metric": "latency_ms", "severity_score": 2.0, "detected_at": base_time.isoformat()},
        {"metric": "packet_loss_pct", "severity_score": 3.0, "detected_at": (base_time + timedelta(seconds=10)).isoformat()},
        {"metric": "throughput_mbps", "severity_score": 1.5, "detected_at": (base_time + timedelta(seconds=25)).isoformat()}
    ]

    clusters = correlate(flags, window_seconds=30)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert len(cluster["correlated_flags"]) == 3
    symptom_chain = cluster["symptom_chain"]
    assert symptom_chain[0]["offset_seconds"] == 0.0
    assert symptom_chain[1]["offset_seconds"] == 10.0
    assert symptom_chain[2]["offset_seconds"] == 25.0

def test_correlate_lone_flag():
    base_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    flags = [
        {"metric": "latency_ms", "severity_score": 2.0, "detected_at": base_time.isoformat()}
    ]
    clusters = correlate(flags, window_seconds=30)
    assert len(clusters) == 1
    assert len(clusters[0]["correlated_flags"]) == 1
    assert clusters[0]["symptom_chain"][0]["offset_seconds"] == 0.0

def test_correlate_flags_outside_window():
    base_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    flags = [
        {"metric": "latency_ms", "severity_score": 2.0, "detected_at": base_time.isoformat()},
        {"metric": "packet_loss_pct", "severity_score": 3.0, "detected_at": (base_time + timedelta(minutes=5)).isoformat()}
    ]
    clusters = correlate(flags, window_seconds=30)
    assert len(clusters) == 2
    assert len(clusters[0]["correlated_flags"]) == 1
    assert len(clusters[1]["correlated_flags"]) == 1
