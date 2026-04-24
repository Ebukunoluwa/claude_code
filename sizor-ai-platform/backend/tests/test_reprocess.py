"""Pure-function tests for scripts/reprocess_stale_extractions.py.

Covers: arg parsing, cohort expansion, NHS number normalisation, and the
synthesize_domain_scores helper. DB-dependent paths (patient lookup, main
loop, EWMA threading) are verified manually against the dev DB via the
script's --dry-run mode — see PLAN.md §4.3.

Run: PYTHONPATH=. python -m pytest tests/test_reprocess.py -v
"""
from types import SimpleNamespace

import pytest

from scripts.reprocess_stale_extractions import (
    GENERIC_TO_PATHWAY_DOMAINS,
    VALIDATION_COHORT_NHS,
    expand_cohort,
    normalize_nhs,
    parse_args,
    synthesize_domain_scores,
)


class TestArgParsing:
    def test_validation_cohort_flag(self):
        args = parse_args(["--validation-cohort"])
        assert args.validation_cohort is True
        assert args.all is False
        assert args.patient is None
        assert args.commit is False  # dry-run is the default

    def test_all_flag(self):
        args = parse_args(["--all", "--commit"])
        assert args.all is True
        assert args.commit is True

    def test_patient_repeatable(self):
        args = parse_args(["--patient", "1111111111", "--patient", "2222222222"])
        assert args.patient == ["1111111111", "2222222222"]

    def test_mode_flags_are_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            parse_args(["--all", "--validation-cohort"])

    def test_mode_flag_is_required(self):
        with pytest.raises(SystemExit):
            parse_args([])


class TestCohortExpansion:
    def test_validation_cohort_expands_to_four(self):
        args = SimpleNamespace(
            all=False, validation_cohort=True, patient=None,
        )
        cohort = expand_cohort(args)
        assert cohort == VALIDATION_COHORT_NHS
        assert len(cohort) == 4

    def test_validation_cohort_contains_the_four_named_patients(self):
        # Guard against silent edits to the hardcoded list. These NHS numbers
        # were confirmed present in the dev DB on 2026-04-24.
        assert "999 888 7001" in VALIDATION_COHORT_NHS   # Khegis Khan
        assert "4829998811"  in VALIDATION_COHORT_NHS    # Bukayo Saka
        assert "8982614011"  in VALIDATION_COHORT_NHS    # Tinu Banks
        assert "4739292029"  in VALIDATION_COHORT_NHS    # Tayo Aina

    def test_all_returns_none_sentinel(self):
        args = SimpleNamespace(all=True, validation_cohort=False, patient=None)
        assert expand_cohort(args) is None

    def test_explicit_patients_passthrough(self):
        args = SimpleNamespace(
            all=False, validation_cohort=False,
            patient=["1234567890", "0987654321"],
        )
        assert expand_cohort(args) == ["1234567890", "0987654321"]


class TestNhsNormalisation:
    def test_strips_spaces(self):
        assert normalize_nhs("999 888 7001") == "9998887001"

    def test_strips_hyphens(self):
        assert normalize_nhs("123-456-7890") == "1234567890"

    def test_strips_both(self):
        assert normalize_nhs("999-888 7001") == "9998887001"

    def test_no_separators_passthrough(self):
        assert normalize_nhs("4829998811") == "4829998811"

    def test_dev_db_formats_both_normalise_equally(self):
        # Khegis has spaces in the DB, the others don't. Both must resolve.
        assert normalize_nhs("999 888 7001") == normalize_nhs("9998887001")


class _FakeExtraction:
    """Minimal stand-in for ClinicalExtraction used in synthesis tests."""
    def __init__(self, **scalars):
        self.pain_score           = scalars.get("pain")
        self.breathlessness_score = scalars.get("breathlessness")
        self.mobility_score       = scalars.get("mobility")
        self.appetite_score       = scalars.get("appetite")
        self.mood_score           = scalars.get("mood")


class TestSynthesizeDomainScores:
    def test_applies_categorical_mapping(self):
        ext = _FakeExtraction(pain=7)
        # Cast a wide net of pathway domains so the mapping is exercised.
        domains = set(sum(GENERIC_TO_PATHWAY_DOMAINS.values(), []))
        out = synthesize_domain_scores(ext, domains)
        # 7 → 3 (categorical)
        assert out["pain_management"] == 3
        assert out["chest_pain_monitoring"] == 3

    def test_only_emits_pathway_relevant_domains(self):
        ext = _FakeExtraction(pain=7, breathlessness=5)
        # Orthopaedic-style pathway: no cardiac domain.
        domains = {"pain_management", "mobility_progress"}
        out = synthesize_domain_scores(ext, domains)
        assert out == {"pain_management": 3}
        assert "chest_pain_monitoring" not in out
        assert "breathlessness" not in out

    def test_skips_none_scalars(self):
        ext = _FakeExtraction(pain=None, mobility=6)
        domains = {"pain_management", "mobility_progress"}
        out = synthesize_domain_scores(ext, domains)
        assert out == {"mobility_progress": 2}

    def test_empty_when_no_scalars_and_no_domains(self):
        ext = _FakeExtraction()
        assert synthesize_domain_scores(ext, set()) == {}

    def test_empty_when_scalars_present_but_pathway_has_no_matching_domain(self):
        ext = _FakeExtraction(pain=8)
        out = synthesize_domain_scores(ext, {"some_unrelated_domain"})
        assert out == {}

    def test_mild_signal_preserved(self):
        # The brief's key safety case: pain=1 → categorical 1, not linear 0.
        ext = _FakeExtraction(pain=1)
        out = synthesize_domain_scores(ext, {"pain_management"})
        assert out == {"pain_management": 1}
