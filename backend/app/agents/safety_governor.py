"""
Safety Governor Module
======================
Input contract:
- recommendation: dict containing {"action_text": str, "rationale": str}

Output contract:
- Returns dict:
  {
    "safe_to_present": bool,
    "action_text": str,
    "rationale": str,
    "auto_applied": False # Invariant: auto_applied is ALWAYS False
  }

Rules & Logic:
1. Checks action_text for dangerous verbs (disable, shut down, reboot, restart).
2. Appends mandatory caveat "(Verify before acting - this system does not apply changes automatically.)" if needed.
3. Strictly enforces auto_applied = False.
"""

from typing import Dict, Any

BANNED_VERBS = ["disable", "shut down", "reboot", "restart"]
CAVEAT_PHRASE = "verify before acting"

def check(recommendation: Dict[str, Any]) -> Dict[str, Any]:
    action_text = recommendation.get("action_text", "")
    rationale = recommendation.get("rationale", "")

    action_lower = action_text.lower()
    needs_caveat = any(verb in action_lower for verb in BANNED_VERBS) and CAVEAT_PHRASE not in action_lower

    if needs_caveat:
        action_text = f"{action_text} (Verify before acting - this system does not apply changes automatically.)"

    return {
        "safe_to_present": True,
        "action_text": action_text,
        "rationale": rationale,
        "auto_applied": False # Hard invariant
    }
