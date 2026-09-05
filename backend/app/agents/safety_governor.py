"""
Safety Governor Module (TV-002)
===============================
An auditable safety gate that intercepts recommendations before they are presented
or stored in the database. Enforces strict safety policies:
1. Detects potentially disruptive or destructive verbs (disable, shut down, reboot, restart)
   and appends an explicit verification caveat if one is not already present.
2. Strictly enforces the Human-in-the-Loop invariant: `auto_applied` is ALWAYS False.

Input contract:
- recommendation: dict containing:
    - "action_text": str (required)
    - "rationale": str (optional)

Output contract:
- Returns dict:
  {
    "safe_to_present": bool,  # True for valid recommendations
    "action_text": str,       # Possibly amended with safety caveat
    "rationale": str,         # Preserved or updated rationale
    "auto_applied": bool      # Invariant: ALWAYS False
  }

Rules & Logic:
1. Banned disruptive action verbs: ["disable", "shut down", "reboot", "restart"]
2. Caveat phrases allowed: ["verify before acting", "confirm before"]
3. If a banned verb is present without a caveat phrase, the mandatory warning
   "(Verify before acting - this system does not apply changes automatically.)" is appended.
4. Auto-applied is hard-coded to False across all code paths.
"""

from typing import Dict, Any

BANNED_VERBS = ["disable", "shut down", "reboot", "restart"]
CAVEAT_PHRASES = ["verify before acting", "confirm before"]
MANDATORY_CAVEAT = "(Verify before acting - this system does not apply changes automatically.)"


def check(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and softens recommendations, ensuring no automated destructive action is taken.
    """
    if not isinstance(recommendation, dict):
        recommendation = {}

    action_text = recommendation.get("action_text", "")
    rationale = recommendation.get("rationale", "")

    action_lower = action_text.lower()
    has_banned_verb = any(verb in action_lower for verb in BANNED_VERBS)
    has_caveat = any(caveat in action_lower for caveat in CAVEAT_PHRASES)

    if has_banned_verb and not has_caveat:
        action_text = f"{action_text} {MANDATORY_CAVEAT}".strip()

    return {
        "safe_to_present": True,
        "action_text": action_text,
        "rationale": rationale,
        "auto_applied": False  # Hard invariant: no automated changes permitted
    }