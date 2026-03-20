"""Failure to Progress (FTP) assessment service."""
from .nice_guidelines import get_guidelines_for_condition


def interpolate_expected(curves: dict, day: int) -> float | None:
    """Linearly interpolate expected score for a given day from NICE recovery curves."""
    days = sorted(curves.keys())
    if not days:
        return None
    if day <= days[0]:
        return float(curves[days[0]])
    if day >= days[-1]:
        return float(curves[days[-1]])
    for i in range(len(days) - 1):
        d1, d2 = days[i], days[i + 1]
        if d1 <= day <= d2:
            ratio = (day - d1) / (d2 - d1)
            return float(curves[d1] + ratio * (curves[d2] - curves[d1]))
    return None


def assess_ftp_status(variance_per_domain: dict) -> str:
    """Determine FTP status from variance dict."""
    worst = 0.0
    for domain, data in variance_per_domain.items():
        if data.get("worse", False):
            worst = max(worst, data.get("variance", 0))
    if worst > 3:
        return "significantly_behind"
    elif worst > 2:
        return "behind"
    elif worst > 1:
        return "watch"
    return "on_track"


def compute_ftp(condition: str, day: int, actual_scores: dict) -> tuple[dict, dict, dict, str]:
    """
    Compute FTP assessment.
    Returns (expected_scores, actual_scores, variance_per_domain, ftp_status)
    """
    guidelines = get_guidelines_for_condition(condition)
    recovery_curves = guidelines.get("recovery_curves", {})
    expected = {}
    variance = {}

    for domain in ["pain", "breathlessness", "mobility", "mood", "appetite"]:
        actual = actual_scores.get(domain)
        if actual is None:
            continue
        curve = recovery_curves.get(domain)
        if not curve:
            continue
        exp = interpolate_expected(curve, day)
        if exp is None:
            continue
        expected[domain] = round(exp, 2)
        # For pain/breathlessness: lower is better (higher actual = worse)
        # For mobility/mood/appetite: higher is better (lower actual = worse)
        if domain in ("pain", "breathlessness"):
            diff = actual - exp
            worse = diff > 0
        else:
            diff = exp - actual
            worse = diff > 0
        variance[domain] = {
            "expected": round(exp, 2),
            "actual": actual,
            "variance": round(abs(diff), 2),
            "worse": worse,
        }

    status = assess_ftp_status(variance)
    return expected, actual_scores, variance, status
