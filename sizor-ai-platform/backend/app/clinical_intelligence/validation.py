"""Plausibility detectors for clinical extractions.

Non-blocking — returns warnings to be stored alongside the extraction
(condition_specific_flags.validation_warnings) and surfaced in the
clinician dashboard. Does not modify the extraction or block the
pipeline.

Phase 2 implements exactly the two named detectors from PLAN.md Sec 4:

  first_call_all_fours
    First call (no prior history) with 3 or more domains scored 4.
    Likely LLM hallucination or transcript misread — clinicians should
    review before any escalation action triggers on this extraction.

  all_domains_dropped_to_empty
    Most-recent prior call had 2 or more non-zero domain scores, and
    the current call has no scores at all. Likely extraction failure
    masquerading as silence — the clinician should check whether the
    call actually took place and whether the transcript reached the
    extraction pipeline.

Per approved Q3, this module is deliberately TIGHT: no generalisation,
no additional detectors mid-phase. Adding a third detector is a
PLAN-level scope decision.

Signature takes bare list[DomainScore] rather than a wrapping
CallExtraction object — the two detectors only need domain scores, and
a CallExtraction model can be added later (Phase 4 prompt-builder /
coverage work) when other consumers need it. Avoids premature coupling.
"""
from __future__ import annotations

from .models import DomainScore, ValidationWarning


# How many 4-scored domains trigger the first-call warning.
_FIRST_CALL_FOURS_THRESHOLD = 3

# How many non-zero domains in the prior call trigger the drop detector.
_DROPPED_TO_EMPTY_PRIOR_NONZERO_THRESHOLD = 2


def _detect_first_call_all_fours(
    current_scores: list[DomainScore],
    prior_calls_scores: list[list[DomainScore]],
) -> ValidationWarning | None:
    if prior_calls_scores:
        return None
    fours = [s.domain for s in current_scores if s.raw_score == 4]
    if len(fours) < _FIRST_CALL_FOURS_THRESHOLD:
        return None
    return ValidationWarning(
        code="first_call_all_fours",
        severity="warn",
        detail=(
            f"First call with {len(fours)} domains scored 4. This is clinically "
            f"implausible for a first post-discharge call and likely indicates "
            f"LLM hallucination or a transcript misread. Review the extraction "
            f"before any escalation action triggers."
        ),
        affected_domains=fours,
    )


def _detect_all_domains_dropped_to_empty(
    current_scores: list[DomainScore],
    prior_calls_scores: list[list[DomainScore]],
) -> ValidationWarning | None:
    if not prior_calls_scores:
        return None
    if current_scores:
        return None
    prior = prior_calls_scores[-1]
    prior_nonzero = [s.domain for s in prior if s.raw_score > 0]
    if len(prior_nonzero) < _DROPPED_TO_EMPTY_PRIOR_NONZERO_THRESHOLD:
        return None
    return ValidationWarning(
        code="all_domains_dropped_to_empty",
        severity="warn",
        detail=(
            f"Previous call had {len(prior_nonzero)} non-zero domain scores "
            f"but current call has none. Likely extraction failure rather "
            f"than genuine improvement — check that the call transcript "
            f"reached the pipeline and the LLM returned a usable response."
        ),
        affected_domains=prior_nonzero,
    )


def validate_extraction_plausibility(
    current_scores: list[DomainScore],
    prior_calls_scores: list[list[DomainScore]],
) -> list[ValidationWarning]:
    """Run all Phase 2 plausibility detectors against an extraction.

    prior_calls_scores is chronological with the most-recent call last
    (same convention as scoring.score_patient_domain and smoothing.py).

    Returns an empty list when nothing fires.
    """
    warnings: list[ValidationWarning] = []
    for detector in (
        _detect_first_call_all_fours,
        _detect_all_domains_dropped_to_empty,
    ):
        w = detector(current_scores, prior_calls_scores)
        if w is not None:
            warnings.append(w)
    return warnings
