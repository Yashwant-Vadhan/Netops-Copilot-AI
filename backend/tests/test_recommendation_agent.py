"""
Unit Tests for Recommendation Agent (TY-003)
============================================
"""

import pytest
from app.agents import recommendation_agent


def test_known_recommendation_mapping():
    result = recommendation_agent.recommend("network_congestion", "high", ["Latency reached 180ms", "Throughput at 45 Mbps"])
    assert "action_text" in result
    assert "rationale" in result
    assert len(result["action_text"]) > 0


def test_banned_words_scan_across_table():
    for cause, entry in recommendation_agent.RULE_TABLE.items():
        for banned in recommendation_agent.BANNED_CERTAINTY_WORDS:
            assert banned not in entry["action_text"].lower(), f"Banned word '{banned}' in {cause}"


def test_unknown_cause_fallback():
    result = recommendation_agent.recommend("unseen_future_anomaly", "low", [])
    assert result["action_text"] == recommendation_agent.DEFAULT_RECOMMENDATION["action_text"]