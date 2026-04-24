from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from ..database import get_db
from ..clinical_intelligence.pathway_map import OPCS_TO_NICE_MAP
from .auth import get_current_clinician

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/{opcs_code}")
async def get_benchmarks(
    opcs_code: str,
    db: AsyncSession = Depends(get_db),
    clinician=Depends(get_current_clinician),
):
    result = await db.execute(text("""
        SELECT domain, day_range_start, day_range_end, expected_score, upper_bound_score,
               expected_state, nice_source, nice_quote, urgency
        FROM domain_benchmarks
        WHERE opcs_code = :opcs_code
        ORDER BY domain, day_range_start
    """), {"opcs_code": opcs_code})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/pathways/search")
async def search_pathways(
    q: str = "",
    clinician=Depends(get_current_clinician),
):
    """Search OPCS_TO_NICE_MAP by label or OPCS code."""
    q_lower = q.lower()
    results = []
    for code, data in OPCS_TO_NICE_MAP.items():
        label = data["label"].lower()
        if not q or q_lower in label or code.lower().startswith(q_lower):
            results.append({
                "opcs_code": code,
                "label": data["label"],
                "category": data["category"],
                "nice_ids": data["nice_ids"],
                "pathway_slug": data["pathway_slug"],
                "monitoring_window_days": data["monitoring_window_days"],
                "call_count": len(data["call_days"]),
                "domain_count": len(data["monitoring_domains"]),
                "monitoring_domains": data["monitoring_domains"],
            })
    # Sort: exact matches first, then by category
    results.sort(key=lambda r: (0 if q_lower in r["label"].lower() else 1, r["category"], r["label"]))
    return results


@router.get("/pathways/all")
async def get_all_pathways(clinician=Depends(get_current_clinician)):
    return await search_pathways(q="", clinician=clinician)
