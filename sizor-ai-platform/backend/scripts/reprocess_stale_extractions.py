"""
Reprocess stale / pending clinical extractions.

Re-derives condition_specific_flags.domain_scores for every
ClinicalExtraction row whose extraction_status is 'stale_pre_calibration'
or 'pending_reprocess', using the categorical 0-10 → 0-4 mapping
(app.clinical.scoring.score_0_10_to_0_4) — replacing whatever was
produced by the pre-calibration linear multiplier.

Also re-threads smoothing (EWMA) and risk_score computation in
patient-chronological order so later calls seed correctly from
earlier ones. On success, extraction_status is flipped to 'extracted'.

Idempotent: rows already at 'extracted' are skipped; re-running is safe.

Modes (flags):
    --dry-run               Default. Print planned changes, commit nothing.
    --commit                Apply changes.
    --patient NHS           Process a single patient by NHS number. Repeatable.
    --all                   Process every eligible row across all patients.
    --validation-cohort     Shortcut for the four Phase 1 test patients
                            (Khegis Khan, Bukayo Saka, Tinu Banks, Tayo Aina).

Exactly one of --patient/--all/--validation-cohort must be supplied.

Usage from backend/:
    PYTHONPATH=. python scripts/reprocess_stale_extractions.py --validation-cohort
    PYTHONPATH=. python scripts/reprocess_stale_extractions.py --validation-cohort --commit
    PYTHONPATH=. python scripts/reprocess_stale_extractions.py --patient '999 888 7001'
    PYTHONPATH=. python scripts/reprocess_stale_extractions.py --all --commit
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from collections import defaultdict

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.clinical_intelligence.risk_score import breakdown_to_dict, compute_risk_score
from app.clinical_intelligence.scoring import score_0_10_to_0_4
from app.clinical_intelligence.smoothing import smooth_extraction, to_persistable_dict
from app.config import settings
from app.models import (
    CallRecord,
    ClinicalExtraction,
    FTPRecord,
    Patient,
    UrgencyFlag,
)

logger = logging.getLogger(__name__)


# Fixed test patients for Phase 1 validation. Dev/staging only — these NHS
# numbers were confirmed present in the dev DB on 2026-04-24. Verbatim from
# the patients table (including the internal spaces in Khegis Khan's number).
VALIDATION_COHORT_NHS: list[str] = [
    "999 888 7001",  # Khegis Khan
    "4829998811",    # Bukayo Saka
    "8982614011",    # Tinu Banks
    "4739292029",    # Tayo Aina
]


# Mirrors the generic → pathway-domain fallback mapping in
# pipeline_tasks.py. Keep in sync with that file (Phase 2 will centralise).
GENERIC_TO_PATHWAY_DOMAINS: dict[str, list[str]] = {
    "pain":           ["pain_management", "chest_pain_monitoring"],
    "mobility":       ["mobility_progress", "mobility_and_rehabilitation"],
    "breathlessness": ["breathlessness_score", "breathlessness"],
    "mood":           ["mood_and_depression", "mood_and_anxiety"],
}


REPROCESSABLE_STATUSES = ("stale_pre_calibration", "pending_reprocess")


def normalize_nhs(n: str) -> str:
    """Strip whitespace and hyphens. Matches api/inbound.py:122 convention."""
    return n.replace(" ", "").replace("-", "")


def synthesize_domain_scores(
    ext: ClinicalExtraction,
    pathway_domains: set[str],
) -> dict[str, int]:
    """Apply categorical mapping to scalar 0-10 columns, emit only
    pathway-domains listed for this patient's active pathway."""
    scalars = {
        "pain":           ext.pain_score,
        "breathlessness": ext.breathlessness_score,
        "mobility":       ext.mobility_score,
        "appetite":       ext.appetite_score,
        "mood":           ext.mood_score,
    }
    out: dict[str, int] = {}
    for generic, val in scalars.items():
        mapped = score_0_10_to_0_4(val)
        if mapped is None:
            continue
        for pd in GENERIC_TO_PATHWAY_DOMAINS.get(generic, []):
            if pd in pathway_domains:
                out[pd] = mapped
    return out


async def load_pathway_domains(db, patient_id) -> set[str]:
    """Return the union of domains across the patient's active pathways.
    Empty set if the patient has no pathway row (pre-cutover data integrity
    gap — caller should treat as 'failed' rather than synthesise spurious
    cross-pathway domains)."""
    result = await db.execute(
        text(
            "SELECT domains FROM patient_pathways "
            "WHERE patient_id = :pid AND active = TRUE"
        ),
        {"pid": str(patient_id)},
    )
    domains: set[str] = set()
    for (arr,) in result.all():
        if arr:
            domains.update(arr)
    return domains


async def resolve_patient_ids(db, nhs_numbers: list[str]) -> list:
    """Look up patient UUIDs by NHS number, matching both literal and
    normalised forms (DB may store with or without spaces)."""
    targets = {normalize_nhs(n) for n in nhs_numbers}
    result = await db.execute(select(Patient))
    matches = [
        p for p in result.scalars().all()
        if normalize_nhs(p.nhs_number) in targets
    ]
    found = {normalize_nhs(p.nhs_number) for p in matches}
    missing = targets - found
    if missing:
        logger.warning("No patient found for NHS numbers: %s", sorted(missing))
    return [p.patient_id for p in matches]


async def reprocess(
    *,
    patient_ids: list | None,
    commit: bool,
) -> dict:
    """Main loop. Returns a summary dict for printing."""
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    summary = {
        "eligible": 0,
        "reprocessed": 0,
        "skipped_no_pathway": 0,
        "skipped_no_scalars": 0,
        "errors": 0,
    }

    async with Session() as db:
        q = (
            select(ClinicalExtraction, CallRecord)
            .join(CallRecord, ClinicalExtraction.call_id == CallRecord.call_id)
            .where(ClinicalExtraction.extraction_status.in_(REPROCESSABLE_STATUSES))
            .order_by(ClinicalExtraction.patient_id, CallRecord.started_at)
        )
        if patient_ids is not None:
            q = q.where(ClinicalExtraction.patient_id.in_(patient_ids))
        rows = (await db.execute(q)).all()

    summary["eligible"] = len(rows)
    logger.info("Eligible extractions: %d", len(rows))

    by_patient: dict[str, list] = defaultdict(list)
    for ext, call in rows:
        by_patient[str(ext.patient_id)].append((ext, call))

    async with Session() as db:
        for patient_id, patient_rows in by_patient.items():
            pathway_domains = await load_pathway_domains(db, patient_id)
            if not pathway_domains:
                logger.warning(
                    "patient=%s has no active patient_pathways row; "
                    "skipping %d extraction(s) — would mark as 'failed'",
                    patient_id[:8], len(patient_rows),
                )
                summary["skipped_no_pathway"] += len(patient_rows)
                continue

            prior_smoothed: dict | None = None

            for ext, call in patient_rows:
                try:
                    synthesised = synthesize_domain_scores(ext, pathway_domains)
                    if not synthesised:
                        summary["skipped_no_scalars"] += 1
                        logger.info(
                            "patient=%s call=%s has no usable scalar scores; "
                            "would mark as 'failed'",
                            patient_id[:8], str(ext.call_id)[:8],
                        )
                        continue

                    csf = dict(ext.condition_specific_flags or {})
                    csf["domain_scores"] = synthesised

                    extraction_dict = {
                        "pain_score":           ext.pain_score,
                        "breathlessness_score": ext.breathlessness_score,
                        "mobility_score":       ext.mobility_score,
                        "appetite_score":       ext.appetite_score,
                        "mood_score":           ext.mood_score,
                        "medication_adherence": ext.medication_adherence,
                        "condition_specific_flags": csf,
                    }
                    smoothed = smooth_extraction(
                        extraction_dict, prior_smoothed, critical_medication=False,
                    )
                    smoothed_state = to_persistable_dict(smoothed)

                    ftp_row = (
                        await db.execute(
                            select(FTPRecord)
                            .where(FTPRecord.call_id == ext.call_id)
                            .limit(1)
                        )
                    ).scalar_one_or_none()
                    ftp_status = ftp_row.ftp_status if ftp_row else "unknown"

                    has_red = (
                        await db.execute(
                            select(UrgencyFlag).where(
                                UrgencyFlag.call_id == ext.call_id,
                                UrgencyFlag.severity == "red",
                            ).limit(1)
                        )
                    ).scalar_one_or_none() is not None

                    breakdown = compute_risk_score(
                        smoothed,
                        ftp_status=ftp_status,
                        day_in_recovery=call.day_in_recovery or 0,
                        has_active_red_flag=has_red,
                        raw_pain=ext.pain_score,
                        raw_breathlessness=ext.breathlessness_score,
                    )

                    logger.info(
                        "patient=%s call=%s day=%s  "
                        "domains=%d  score=%.1f  band=%s  driver=%s",
                        patient_id[:8], str(ext.call_id)[:8],
                        call.day_in_recovery, len(synthesised),
                        breakdown.final_score, breakdown.band_if_computed,
                        breakdown.dominant_driver,
                    )

                    if commit:
                        ext.condition_specific_flags = csf
                        ext.smoothed_scores = smoothed_state
                        ext.risk_score = breakdown.final_score
                        ext.risk_score_breakdown = breakdown_to_dict(breakdown)
                        ext.extraction_status = "extracted"
                        ext.extraction_status_reason = (
                            f"Reprocessed from raw scalars by "
                            f"reprocess_stale_extractions.py"
                        )

                    prior_smoothed = smoothed_state
                    summary["reprocessed"] += 1

                except Exception as exc:
                    summary["errors"] += 1
                    logger.exception(
                        "patient=%s call=%s failed: %s",
                        patient_id[:8], str(ext.call_id)[:8], exc,
                    )

        if commit:
            await db.commit()
            logger.info("Committed changes.")
        else:
            logger.info("Dry run — no changes committed.")

    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--patient", action="append", metavar="NHS",
        help="NHS number. Repeatable.",
    )
    mode.add_argument(
        "--all", action="store_true",
        help="Process every eligible row.",
    )
    mode.add_argument(
        "--validation-cohort", action="store_true",
        help="Shortcut: expands to the four Phase 1 test patients.",
    )
    p.add_argument(
        "--commit", action="store_true",
        help="Apply changes. Without this flag the script runs as a dry-run.",
    )
    return p.parse_args(argv)


def expand_cohort(args: argparse.Namespace) -> list[str] | None:
    """Return the NHS number list the caller asked for, or None for --all."""
    if args.all:
        return None
    if args.validation_cohort:
        return list(VALIDATION_COHORT_NHS)
    return list(args.patient or [])


async def _main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    nhs_list = expand_cohort(args)

    patient_ids: list | None
    if nhs_list is None:
        patient_ids = None
    else:
        engine = create_async_engine(settings.database_url)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            patient_ids = await resolve_patient_ids(db, nhs_list)
        if not patient_ids:
            logger.error("No matching patients found. Aborting.")
            return 1

    summary = await reprocess(patient_ids=patient_ids, commit=args.commit)
    logger.info("=" * 60)
    logger.info("REPROCESS SUMMARY")
    logger.info("  eligible          : %d", summary["eligible"])
    logger.info("  reprocessed       : %d", summary["reprocessed"])
    logger.info("  skipped_no_scalars: %d", summary["skipped_no_scalars"])
    logger.info("  errors            : %d", summary["errors"])
    if summary["skipped_no_pathway"] > 0:
        logger.warning(
            "  skipped_no_pathway: %d  <-- DECISION REQUIRED before Phase 5. "
            "These extractions belong to patients with no active "
            "patient_pathways row and are invisible to the risk engine. "
            "See PLAN.md §Phase-2-decisions.",
            summary["skipped_no_pathway"],
        )
    else:
        logger.info("  skipped_no_pathway: 0")
    logger.info("=" * 60)
    return 0 if summary["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
