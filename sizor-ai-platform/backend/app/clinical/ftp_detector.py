"""Failure to Progress (FTP) detection across consecutive calls."""
from __future__ import annotations


def detect_ftp(domain: str, scores: list[dict]) -> dict:
    """
    scores: list of {"day": int, "score": int, "upper_bound": int} sorted by day
    Returns {"ftp": bool, "consecutive_above_bound": int, "first_ftp_day": int|None}
    """
    if len(scores) < 2:
        return {"ftp": False, "consecutive_above_bound": 0, "first_ftp_day": None}

    consecutive = 0
    first_ftp_day = None
    for s in scores:
        if s["score"] >= s["upper_bound"]:
            consecutive += 1
            if consecutive >= 2 and first_ftp_day is None:
                first_ftp_day = s["day"]
        else:
            consecutive = 0

    return {
        "ftp": consecutive >= 2,
        "consecutive_above_bound": consecutive,
        "first_ftp_day": first_ftp_day,
    }


def get_ftp_domains(domain_score_history: dict[str, list[dict]]) -> list[str]:
    """Returns list of domain names with active FTP flags."""
    return [d for d, scores in domain_score_history.items() if detect_ftp(d, scores)["ftp"]]
