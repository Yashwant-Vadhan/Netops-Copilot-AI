"""
Unit Tests for Security Agent (TV-003)
=====================================
"""

import pytest
from app.agents import security_agent


def test_normal_traffic_returns_none():
    """Normal steady traffic pattern does not trigger any security flag."""
    window = [
        {"bytes_sent": 100_000, "bytes_recv": 500_000, "throughput_mbps": 5.0, "latency_ms": 15.0},
        {"bytes_sent": 150_000, "bytes_recv": 600_000, "throughput_mbps": 5.2, "latency_ms": 16.0},
        {"bytes_sent": 200_000, "bytes_recv": 700_000, "throughput_mbps": 4.9, "latency_ms": 15.5},
        {"bytes_sent": 250_000, "bytes_recv": 800_000, "throughput_mbps": 5.1, "latency_ms": 15.2},
    ]
    res = security_agent.scan(window)
    assert res is None


def test_insufficient_samples_returns_none():
    """Window with fewer than 3 samples returns None due to insufficient baseline."""
    assert security_agent.scan([]) is None
    assert security_agent.scan([{"bytes_sent": 100}]) is None
    assert security_agent.scan([{"bytes_sent": 100}, {"bytes_sent": 200}]) is None


def test_outbound_burst_triggers_flag_with_caveat():
    """Massive outbound burst triggers suspicious pattern flag with caveat and capped confidence."""
    window = [
        {"bytes_sent": 100_000, "bytes_recv": 1_000_000, "throughput_mbps": 2.0},
        {"bytes_sent": 150_000, "bytes_recv": 2_000_000, "throughput_mbps": 2.1},
        {"bytes_sent": 200_000, "bytes_recv": 3_000_000, "throughput_mbps": 2.2},
        # Massive outbound surge: 50MB sent in one interval with zero receive
        {"bytes_sent": 50_200_000, "bytes_recv": 3_010_000, "throughput_mbps": 85.0},
    ]
    res = security_agent.scan(window)

    assert res is not None
    assert res["flag"] == "possible_suspicious_pattern"
    assert "not a substitute for a dedicated security" in res["caveat"].lower()
    assert 0 < res["confidence"] <= 40


@pytest.mark.parametrize("surge_mb,tp", [
    (5, 50.0),
    (20, 90.0),
    (100, 150.0),
    (500, 300.0),
])
def test_confidence_strictly_capped_at_40(surge_mb, tp):
    """Assert confidence never exceeds 40 regardless of how severe the synthetic burst is."""
    window = [
        {"bytes_sent": 100_000, "bytes_recv": 500_000, "throughput_mbps": 1.0},
        {"bytes_sent": 200_000, "bytes_recv": 1_000_000, "throughput_mbps": 1.0},
        {"bytes_sent": 300_000, "bytes_recv": 1_500_000, "throughput_mbps": 1.0},
        {"bytes_sent": 300_000 + (surge_mb * 1_000_000), "bytes_recv": 1_510_000, "throughput_mbps": tp},
    ]
    res = security_agent.scan(window)
    if res is not None:
        assert res["confidence"] <= 40, f"Confidence {res['confidence']} exceeded maximum cap of 40"
        assert res["flag"] == "possible_suspicious_pattern"
        assert len(res["caveat"]) > 0