"""
Unit Tests for Anomaly Detector (TY-001)
=======================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.agents import anomaly_detector


def test_warming_up_status():
    samples = [{"latency_ms": 10.0, "timestamp": datetime.now(timezone.utc)} for _ in range(15)]
    res = anomaly_detector.detect_anomalies("eth0", samples=samples)
    assert res["status"] == "warming_up"
    assert len(res["flags"]) == 0


def test_obvious_spike_flagged():
    base_time = datetime.now(timezone.utc)
    samples = [
        {"latency_ms": 15.0 + (i % 3), "packet_loss_pct": 0.0, "throughput_mbps": 10.0, "timestamp": base_time + timedelta(seconds=i*5)}
        for i in range(35)
    ]
    # Add an obvious latency spike as the latest sample
    samples.append({
        "latency_ms": 250.0,
        "packet_loss_pct": 0.0,
        "throughput_mbps": 10.0,
        "timestamp": base_time + timedelta(seconds=180)
    })

    res = anomaly_detector.detect_anomalies("eth0", samples=samples)
    assert res["status"] == "active"
    assert len(res["flags"]) >= 1
    flagged_metrics = [f["metric"] for f in res["flags"]]
    assert "latency_ms" in flagged_metrics


def test_stable_window_no_flags():
    base_time = datetime.now(timezone.utc)
    samples = [
        {"latency_ms": 20.0 + (i % 2), "packet_loss_pct": 0.0, "throughput_mbps": 15.0, "timestamp": base_time + timedelta(seconds=i*5)}
        for i in range(40)
    ]
    res = anomaly_detector.detect_anomalies("eth0", samples=samples)
    assert res["status"] == "active"
    assert len(res["flags"]) == 0