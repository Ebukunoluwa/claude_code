"""Tests for smoothing. Run from backend/: PYTHONPATH=. python -m pytest tests/test_smoothing.py -v"""
from app.clinical.smoothing import (
    ewma,
    compute_modifiers,
    smooth_extraction,
    to_persistable_dict,
    AMBER_THRESHOLD,
    MODIFIER_CAP,
)


# --- EWMA primitive ---

def test_ewma_first_call_seeds_with_current():
    assert ewma(6.0, None) == 6.0


def test_ewma_smooths_toward_prior():
    # current=8, prior=2, lam=0.3 → 0.3*8 + 0.7*2 = 3.8
    assert abs(ewma(8.0, 2.0, lam=0.3) - 3.8) < 1e-9


def test_ewma_handles_missing_current():
    # Silent call on this domain — keep prior
    assert ewma(None, 3.5) == 3.5


def test_ewma_handles_both_missing():
    assert ewma(None, None) is None


# --- Modifiers ---

def test_non_critical_missed_dose_small_bump():
    total, detail = compute_modifiers(adherence=False, critical_medication=False)
    assert detail == {"adherence_lapse": 1.0}
    assert total == 1.0


def test_critical_missed_dose_bigger_bump():
    total, detail = compute_modifiers(adherence=False, critical_medication=True)
    assert detail["adherence_lapse"] == 2.0


def test_unknown_adherence_never_penalised():
    total, detail = compute_modifiers(adherence=None)
    assert total == 0.0
    assert detail == {}


def test_modifiers_capped():
    # Force a theoretical scenario over the cap
    total, detail = compute_modifiers(
        adherence=False, critical_medication=True, missed_previous_call=True
    )
    assert total <= MODIFIER_CAP


# --- The 23→82 scenario, translated to 0-10 scale ---

def test_stable_patient_missed_meds_does_not_jump_to_amber_territory():
    """
    Stable patient: all symptom scores ~2-3. Prior smoothed state similar.
    Reports missed one non-critical dose on this call.
    Expectation: max_smoothed stays well below AMBER threshold (6.0).
    """
    prior = {"pain": 2.5, "breathlessness": 2.0, "mobility": 3.0,
             "appetite": 2.5, "mood": 6.5}
    extraction = {
        "pain_score": 3, "breathlessness_score": 2, "mobility_score": 3,
        "appetite_score": 3, "mood_score": 6, "medication_adherence": False,
    }
    result = smooth_extraction(extraction, prior, critical_medication=False)
    assert result.max_smoothed < AMBER_THRESHOLD, (
        f"max_smoothed={result.max_smoothed:.2f} — missed dose on stable patient "
        f"should not push near AMBER"
    )
    assert "adherence_lapse" in result.modifier_detail


def test_sudden_spike_is_dampened_by_ewma():
    """
    Stable patient (prior pain = 2.0) suddenly reports pain = 8 on one call.
    Smoothed pain should be BELOW 8 (dampened by prior history).

    Separately, the raw 8 still triggers the hard RED rule in the pipeline —
    that's unchanged and tested separately. This just proves smoothing works.
    """
    prior = {"pain": 2.0, "breathlessness": 1.5, "mobility": 2.0,
             "appetite": 2.5, "mood": 7.0}
    extraction = {"pain_score": 8, "medication_adherence": True}
    result = smooth_extraction(extraction, prior)
    # Raw was 8, prior smoothed was 2, lam=0.3 → 0.3*8 + 0.7*2 = 3.8
    assert result.pain is not None
    assert 3.0 < result.pain < 5.0


def test_sustained_worsening_accumulates():
    """Three successive calls of pain=7 from a baseline of 2 — smoothed should climb toward 7."""
    state = None
    pain_series = [7, 7, 7, 7, 7]  # five consecutive high-pain calls
    # Seed with a baseline
    state = {"pain": 2.0, "breathlessness": 1.0, "mobility": 2.0,
             "appetite": 2.0, "mood": 6.0}

    smoothed_trajectory = []
    for p in pain_series:
        result = smooth_extraction({"pain_score": p, "medication_adherence": True}, state)
        smoothed_trajectory.append(result.pain)
        state = to_persistable_dict(result)

    # Should be monotonically increasing and approach (but not reach) 7
    assert all(
        smoothed_trajectory[i] < smoothed_trajectory[i + 1]
        for i in range(len(smoothed_trajectory) - 1)
    )
    assert smoothed_trajectory[-1] > smoothed_trajectory[0]
    assert smoothed_trajectory[-1] < 7.0  # asymptotic, never reaches raw value


def test_first_call_no_prior_seeds_cleanly():
    extraction = {"pain_score": 5, "breathlessness_score": 4,
                  "mobility_score": 6, "appetite_score": 5, "mood_score": 6,
                  "medication_adherence": True}
    result = smooth_extraction(extraction, prior_smoothed=None)
    # On first call, smoothed == raw
    assert result.pain == 5.0
    assert result.breathlessness == 4.0
    assert result.max_smoothed == 6.0


def test_persistable_round_trip():
    """Shape we store in JSONB should survive a round trip through ewma."""
    extraction = {"pain_score": 3, "breathlessness_score": 2,
                  "mobility_score": 4, "appetite_score": 3, "mood_score": 7,
                  "medication_adherence": True}
    r1 = smooth_extraction(extraction, prior_smoothed=None)
    persisted = to_persistable_dict(r1)
    # Next call uses the persisted dict as prior
    r2 = smooth_extraction(extraction, prior_smoothed=persisted)
    assert r2.pain is not None
