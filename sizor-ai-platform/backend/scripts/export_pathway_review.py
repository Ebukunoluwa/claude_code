"""Export a per-pathway clinical review .md from the Python data.

Usage (from backend/):
    PYTHONPATH=. python scripts/export_pathway_review.py R17

Outputs to backend/docs/clinical_review/<opcs>.md. Intended to be handed
to the pathway's nominated reviewer (see PLAN.md §1 for specialty per
pathway). Regenerate after any edit to the source module so the
reviewer always sees current state.

Phase 3: only R17 is populated at the time of first run. Other pathways
will produce an empty-content file until their cluster module lands.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from collections import defaultdict
from pathlib import Path

from app.clinical_intelligence.models import (
    DomainTrajectoryEntry,
    PathwayPlaybook,
    RedFlagProbe,
    RequiredQuestion,
)


# OPCS code -> cluster module under app.clinical_intelligence.pathways.
_OPCS_TO_MODULE = {
    "R17": "obstetric", "R18": "obstetric",
    "W37": "orthopaedic", "W38": "orthopaedic",
    "W40": "orthopaedic", "W43": "orthopaedic",
    "K40": "cardiac", "K40_CABG": "cardiac",
    "K57": "cardiac", "K60": "cardiac",
    "H01": "surgical", "H04": "surgical",
    "J44": "respiratory",
    "S01": "neurological",
    "Z03_MH": "mental_health",
}


# Per-OPCS reviewer specialty (informational header only).
_REVIEWER_SPECIALTY = {
    "R17": "Obstetrician and/or community midwifery lead",
    "R18": "Obstetrician and/or community midwifery lead (+ trauma-aware review)",
    "W37": "Orthopaedic surgeon",
    "W38": "Orthopaedic surgeon / geriatrician (shared care)",
    "W40": "Orthopaedic surgeon",
    "W43": "Orthopaedic surgeon",
    "K40": "Cardiologist",
    "K40_CABG": "Cardiothoracic surgeon",
    "K57": "Cardiologist",
    "K60": "Cardiologist / HF specialist nurse",
    "H01": "General surgeon",
    "H04": "Colorectal surgeon",
    "J44": "Respiratory physician / COPD specialist nurse",
    "S01": "Stroke physician / neurologist",
    "Z03_MH": "Mental health clinician (sign-off required)",
}


def _load_module(opcs: str):
    mod_name = _OPCS_TO_MODULE.get(opcs)
    if mod_name is None:
        raise SystemExit(f"Unknown OPCS code: {opcs!r}")
    return importlib.import_module(
        f"app.clinical_intelligence.pathways.{mod_name}"
    )


def _get(module, name, opcs):
    return getattr(module, name, {}).get(opcs)


def _group_trajectories_by_domain(
    rows: list[DomainTrajectoryEntry],
) -> dict[str, list[DomainTrajectoryEntry]]:
    grouped: dict[str, list[DomainTrajectoryEntry]] = defaultdict(list)
    for r in rows:
        grouped[r.domain].append(r)
    for k in grouped:
        grouped[k].sort(key=lambda r: r.day_range_start)
    return grouped


def _render_trajectory_table(rows: list[DomainTrajectoryEntry]) -> str:
    if not rows:
        return "_(no trajectory rows)_\n"
    lines = [
        "| Day | Expected | Upper bound | Expected state | NICE |",
        "|---:|---:|---:|---|---|",
    ]
    for r in rows:
        day_label = (
            f"{r.day_range_start}"
            if r.day_range_start == r.day_range_end
            else f"{r.day_range_start}-{r.day_range_end}"
        )
        state = (r.expected_state or "").replace("|", "\\|")
        lines.append(
            f"| {day_label} | {r.expected_score} | {r.upper_bound_score} "
            f"| {state} | {r.nice_source} |"
        )
    return "\n".join(lines) + "\n"


def _render_required_questions(
    questions: list[RequiredQuestion],
) -> str:
    if not questions:
        return "_(no required questions)_\n"

    # Group by band. Report each question under each band it belongs to.
    bands = [(1, 3), (4, 7), (8, 14), (15, 28), (29, 42), (43, 60), (61, 90)]
    out = []
    for start, end in bands:
        in_band = [
            q for q in questions
            if any(bs <= start and be >= end for bs, be in q.day_ranges)
        ]
        if not in_band:
            continue
        out.append(f"### Day {start}-{end}\n")
        out.append("| Domain | Question |")
        out.append("|---|---|")
        for q in in_band:
            text = q.question_text.replace("|", "\\|")
            out.append(f"| `{q.domain}` | {text} |")
        out.append("")
    return "\n".join(out) + "\n"


def _render_red_flag_probes(probes: dict[str, RedFlagProbe]) -> str:
    if not probes:
        return "_(no red flag probes)_\n"
    # Group by parent_flag_code for readability. Probes with parent=None
    # are shown under their own flag_code.
    by_parent: dict[str, list[RedFlagProbe]] = defaultdict(list)
    for probe in probes.values():
        key = probe.parent_flag_code or probe.flag_code
        by_parent[key].append(probe)

    out = []
    for parent in sorted(by_parent):
        children = sorted(by_parent[parent], key=lambda p: p.flag_code)
        # Header — parent clinical entity + how many probes split from it.
        split_note = (
            f" (1 probe)"
            if len(children) == 1
            else f" (split into {len(children)} probes)"
        )
        out.append(f"### `{parent}`{split_note}\n")
        for probe in children:
            out.append(
                f"**`{probe.flag_code}`** → "
                f"{probe.category.value} / {probe.follow_up_escalation.value}"
            )
            out.append(f"> {probe.patient_facing_question}")
            out.append("")
            out.append(f"_NICE basis:_ {probe.nice_basis}")
            out.append("")
    return "\n".join(out) + "\n"


def _render_clinical_review_needed_flags(
    opcs: str, module,
) -> str:
    """Scan the source file for CLINICAL_REVIEW_NEEDED comments and
    surface each one here. Keeps the reviewer's open-question list
    visible without them having to grep the Python source.

    Only matches lines that START with '# CLINICAL_REVIEW_NEEDED'
    after stripping whitespace — this excludes module docstring prose
    that mentions the concept. Continuation lines must be contiguous
    non-empty comments."""
    source_path = Path(module.__file__)
    if not source_path.exists():
        return "_(no source file to scan)_\n"

    flags: list[str] = []
    current: list[str] = []

    def _flush():
        if current:
            flags.append(" ".join(current).strip())
            current.clear()

    for line in source_path.read_text().splitlines():
        stripped = line.strip()
        # Start of a new flag block — only if the line begins with
        # '# CLINICAL_REVIEW_NEEDED' (with or without a space after '#').
        if stripped.startswith("# CLINICAL_REVIEW_NEEDED") or \
                stripped.startswith("#CLINICAL_REVIEW_NEEDED"):
            _flush()
            current.append(stripped.lstrip("# ").strip())
        # Continuation line — must be a non-empty comment line that
        # does not itself start a new flag.
        elif current and stripped.startswith("#") and stripped != "#":
            current.append(stripped.lstrip("# ").strip())
        # End of block (blank comment, code line, blank line).
        elif current:
            _flush()
    _flush()

    if not flags:
        return "_(no CLINICAL_REVIEW_NEEDED flags in source)_\n"
    return "\n".join(f"- [ ] {flag}" for flag in flags) + "\n"


def render(opcs: str) -> str:
    module = _load_module(opcs)
    playbook: PathwayPlaybook | None = _get(module, "PATHWAYS", opcs)
    trajectories: list[DomainTrajectoryEntry] = _get(module, "TRAJECTORIES", opcs) or []
    questions: list[RequiredQuestion] = _get(module, "REQUIRED_QUESTIONS", opcs) or []
    probes: dict[str, RedFlagProbe] = _get(module, "RED_FLAG_PROBES", opcs) or {}

    if playbook is None:
        return (
            f"# {opcs} — no content\n\n"
            f"No playbook entry found in "
            f"`app.clinical_intelligence.pathways.{_OPCS_TO_MODULE[opcs]}`. "
            f"This pathway has not yet been ported. See PLAN.md §7 for the "
            f"Phase 3 execution order.\n"
        )

    # Header
    out: list[str] = [
        f"# {opcs} — {playbook.label} — Clinical Review Draft\n",
        "| Field | Value |",
        "|---|---|",
        f"| **Status** | {playbook.validation_status} |",
        f"| **Primary reviewer** | {_REVIEWER_SPECIALTY.get(opcs, 'TBD')} |",
        f"| **Category** | {playbook.category} |",
        f"| **NICE sources** | {', '.join(playbook.nice_ids)} |",
        f"| **Monitoring window** | {playbook.monitoring_window_days} days |",
        f"| **Call days** | {', '.join(str(d) for d in playbook.call_days)} |",
        f"| **Domains** | {', '.join(f'`{d}`' for d in playbook.domains)} |",
        f"| **Upstream red flag codes** | "
        f"{', '.join(f'`{c}`' for c in playbook.red_flag_codes)} |",
        "",
        "## Domain trajectories\n",
    ]

    grouped = _group_trajectories_by_domain(trajectories)
    for domain in playbook.domains:
        rows = grouped.get(domain, [])
        sources = sorted({r.nice_source for r in rows}) if rows else []
        src = " / ".join(sources) if sources else "_no source_"
        out.append(f"### `{domain}` — {src}\n")
        out.append(_render_trajectory_table(rows))
        out.append("")
    # Also emit any domain with trajectories but not in playbook.domains —
    # signals inconsistency the reviewer should see.
    extras = sorted(set(grouped.keys()) - set(playbook.domains))
    if extras:
        out.append("### Trajectories present for domains not in playbook.domains\n")
        for domain in extras:
            out.append(f"**`{domain}`** — unexpected; reviewer to reconcile.\n")

    out.extend([
        "## Required Questions Manifest\n",
        _render_required_questions(questions),
        "## Red Flag Probes\n",
        "One observation per probe. Where a single upstream flag splits into "
        "multiple probes (e.g. `postpartum_haemorrhage` → `_volume` / `_clots` "
        "/ `_haemodynamic`), all children are listed under the same header "
        "with their `parent_flag_code`.\n",
        _render_red_flag_probes(probes),
        "## Reviewer checklist\n",
        "### Trajectory values",
        "- [ ] Expected/upper-bound values clinically reasonable for each day + domain?",
        "- [ ] Day coverage matches the playbook `call_days`?",
        "- [ ] Any values that feel too conservative or too permissive?",
        "",
        "### Required questions",
        "- [ ] Every question clinically necessary?",
        "- [ ] Any critical items missing for this pathway?",
        "- [ ] Day-band placement appropriate?",
        "- [ ] Wording acceptable for a voice agent to read aloud?",
        "- [ ] Multi-part phrasings decompose into independently scoreable parts?",
        "",
        "### Red flag probes",
        "- [ ] Patient-facing wording free of clinical jargon?",
        "- [ ] Escalation tier (999 / same_day / urgent_gp / next_call) appropriate?",
        "- [ ] Every probe asks ONE clinical question (no compound 'or' phrasing)?",
        "- [ ] Split parent codes cover the clinical entity without gaps?",
        "- [ ] Non-judgmental framing for mental-health items?",
        "",
        "### CLINICAL_REVIEW_NEEDED flags\n",
        _render_clinical_review_needed_flags(opcs, module),
        "## Sign-off\n",
        "- Reviewer name:",
        "- Review date:",
        "- Revised `validation_status` (circle): "
        "`clinician_reviewed` / `production_signed_off` / `remains_draft_with_notes`",
        "- Comments:",
        "",
    ])
    return "\n".join(out)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "opcs",
        help="OPCS code to export (e.g. 'R17', 'K40_CABG').",
    )
    p.add_argument(
        "--out-dir",
        default="docs/clinical_review",
        help="Output directory, relative to backend/ (default: %(default)s).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    md = render(args.opcs)
    out_path = Path(args.out_dir) / f"{args.opcs}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"Wrote {out_path} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
