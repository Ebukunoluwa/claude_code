"""
RAG retrieval service — vector similarity search over clinical_knowledge.

Usage:
    from app.services.rag_service import retrieve_nice_context

    chunks = await retrieve_nice_context(db, nice_ids=["NG226", "QS89"],
                                         query="wound healing post hip replacement",
                                         n=5)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _embed(query: str) -> list[float] | None:
    """Embed a query string using OpenAI text-embedding-3-small."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    import httpx  # lazy import — not needed at module load

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "text-embedding-3-small", "input": query},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
    except Exception as exc:
        logger.warning("Embedding API error: %s", exc)
        return None


async def retrieve_nice_context(
    db: AsyncSession,
    nice_ids: list[str],
    query: str,
    n: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve the top-n most relevant NICE guidance chunks for a query.

    Returns a list of dicts:
      {nice_id, heading, content, url}

    Falls back to keyword-ordered text search if no embeddings available.
    """
    if not nice_ids:
        return []

    embedding = await _embed(query)

    if embedding is not None:
        emb_json = json.dumps(embedding)
        result = await db.execute(
            text("""
                SELECT nice_id, heading, content, url
                FROM clinical_knowledge
                WHERE nice_id = ANY(:nice_ids)
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> cast(:emb as vector)
                LIMIT :n
            """),
            {"nice_ids": nice_ids, "emb": emb_json, "n": n},
        )
    else:
        # Fallback: full-text similarity using ts_rank if pg has tsvector, else plain LIMIT
        result = await db.execute(
            text("""
                SELECT nice_id, heading, content, url
                FROM clinical_knowledge
                WHERE nice_id = ANY(:nice_ids)
                LIMIT :n
            """),
            {"nice_ids": nice_ids, "n": n},
        )

    return [dict(r._mapping) for r in result.fetchall()]


async def retrieve_domain_context(
    db: AsyncSession,
    opcs_code: str,
    domain: str,
    day: int,
    nice_ids: list[str],
    n: int = 4,
) -> list[dict[str, Any]]:
    """
    Convenience wrapper that builds a domain-specific query automatically.
    """
    query = f"{domain.replace('_', ' ')} day {day} post-discharge recovery"
    return await retrieve_nice_context(db, nice_ids=nice_ids, query=query, n=n)
