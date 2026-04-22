"""Red flag update logic — dynamic flag management during and after calls."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

ESCALATION_TIERS = {
    4: "999",
    3: "same_day",
    2: "urgent_gp",
    1: "next_call",
}


async def update_red_flags(
    patient_id: str,
    call_id: str,
    domain_scores: dict[str, int],
    current_red_flags: list[str],
    db=None,
) -> dict:
    """
    domain_scores: {domain: score}
    current_red_flags: list of currently active flag domain names
    Returns: {"new_flags": [...], "resolved_flags": [...], "escalation_actions": [...]}
    """
    new_flags = []
    resolved_flags = []
    escalation_actions = []

    for domain, score in domain_scores.items():
        if score == 4:
            if domain not in current_red_flags:
                new_flags.append(domain)
                escalation_actions.append({
                    "domain": domain,
                    "score": score,
                    "tier": "999",
                    "action": f"IMMEDIATE: Call 999 — {domain.replace('_', ' ')} score is 4",
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                })
        elif score == 3:
            if domain not in current_red_flags:
                new_flags.append(domain)
                escalation_actions.append({
                    "domain": domain,
                    "score": score,
                    "tier": "same_day",
                    "action": f"Same-day referral required — {domain.replace('_', ' ')}",
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                })

    # Flags can only be resolved when score is 0 or 1 — tracked across calls
    # Resolution requires 2 consecutive low scores (handled by caller with history)

    logger.info(
        "update_red_flags — patient=%s call=%s new=%d resolved=%d escalations=%d",
        patient_id, call_id, len(new_flags), len(resolved_flags), len(escalation_actions)
    )

    return {
        "new_flags": new_flags,
        "resolved_flags": resolved_flags,
        "escalation_actions": escalation_actions,
        "updated_flags": list(set(current_red_flags + new_flags) - set(resolved_flags)),
    }
