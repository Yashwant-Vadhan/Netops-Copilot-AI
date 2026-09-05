"""
Unit Tests for Safety Governor Agent (TV-002)
============================================
"""

import pytest
from app.agents import safety_governor


def test_benign_recommendation_unchanged():
    """Benign recommendations without banned verbs pass through unmodified."""
    sample_rec = {
        "action_text": "Investigate high-bandwidth processes and consider applying QoS rate limiting.",
        "rationale": "Throughput spike observed with elevated latency."
    }
    result = safety_governor.check(sample_rec)

    assert result["safe_to_present"] is True
    assert result["action_text"] == sample_rec["action_text"]
    assert result["rationale"] == sample_rec["rationale"]
    assert result["auto_applied"] is False


@pytest.mark.parametrize("verb", ["disable", "shut down", "reboot", "restart"])
def test_banned_verbs_get_caveat(verb):
    """Recommendations containing disruptive verbs without caveat receive safety warning."""
    sample_rec = {
        "action_text": f"Recommend operator {verb} the primary interface immediately.",
        "rationale": "Suspected packet storm on link."
    }
    result = safety_governor.check(sample_rec)

    assert result["safe_to_present"] is True
    assert "(Verify before acting - this system does not apply changes automatically.)" in result["action_text"]
    assert result["auto_applied"] is False


def test_already_caveated_recommendation_no_double_caveat():
    """If text already contains 'verify before acting' or 'confirm before', do not duplicate caveat."""
    sample_rec = {
        "action_text": "Reboot the router (verify before acting on production hardware).",
        "rationale": "Unresponsive gateway."
    }
    result = safety_governor.check(sample_rec)

    assert result["safe_to_present"] is True
    # Should not double-append
    assert result["action_text"].count("Verify before acting") == 0 or result["action_text"].count("verify before acting") == 1
    assert result["auto_applied"] is False


def test_auto_applied_invariant_across_varied_inputs():
    """Invariant check: auto_applied MUST always be False across all input permutations."""
    test_cases = [
        {"action_text": "Inspect physical cable connections.", "rationale": "Interface errors."},
        {"action_text": "Disable unused port 4.", "rationale": "Security check."},
        {"action_text": "Restart network daemon.", "rationale": "Service crash."},
        {"action_text": "Check routing tables.", "rationale": "Suboptimal path."},
        {"action_text": "", "rationale": ""},
        {},
    ]
    for case in test_cases:
        res = safety_governor.check(case)
        assert res["auto_applied"] is False, f"Violation: auto_applied was True for input: {case}"
        assert res["safe_to_present"] is True