"""
Unit Tests for Diagnosis Agent (TY-002)
=======================================
"""

import pytest
from app.agents import diagnosis_agent


def test_diagnose_congestion_pattern():
    flags = [
        {"metric": "throughput_mbps", "severity_score": 3.0, "detected_at": "2026-09-06T00:00:00Z"},
        {"metric": "latency_ms", "severity_score": 3.5, "detected_at": "2026-09-06T00:00:05Z"},
        {"metric": "packet_loss_pct", "severity_score": 2.5, "detected_at": "2026-09-06T00:00:10Z"}
    ]
    context = {
        "throughput_mbps": 45.0,
        "latency_ms": 180.0,
        "packet_loss_pct": 8.5
    }
    result = diagnosis_agent.diagnose(flags, context)

    assert result["probable_cause"] == "network_congestion"
    assert result["confidence"] >= 60
    assert len(result["evidence"]) >= 2
    assert any("180.0" in ev for ev in result["evidence"])


def test_diagnose_interface_issue():
    flags = [
        {"metric": "packet_loss_pct", "severity_score": 4.0, "detected_at": "2026-09-06T00:00:00Z"}
    ]
    context = {
        "packet_loss_pct": 12.0
    }
    result = diagnosis_agent.diagnose(flags, context)

    assert result["probable_cause"] == "interface_issue"
    assert len(result["evidence"]) >= 2


def test_two_evidence_invariant():
    """Assert minimum 2 evidence items invariant always holds."""
    test_cases = [
        ([], {}),
        ([{"metric": "latency_ms"}], {"latency_ms": 100.0}),
        ([{"metric": "throughput_mbps"}], {"throughput_mbps": 50.0}),
    ]
    for flags, ctx in test_cases:
        res = diagnosis_agent.diagnose(flags, ctx)
        assert len(res["evidence"]) >= 2