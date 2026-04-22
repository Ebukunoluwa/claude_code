"""
For each domain_benchmarks row without nice_quote:
  1. Embed a query combining domain + expected_state + opcs_code
  2. Vector-similarity search clinical_knowledge for top-5 relevant chunks
  3. Call LLM to extract a verbatim NICE quote for that domain + state
  4. Update domain_benchmarks.nice_quote

Run after fetch_nice_guidance.py:
  DATABASE_URL="postgresql://postgres:postgres@localhost:5432/sizor_ai" \
  OPENAI_API_KEY="sk-..." \
  LLM_MODEL="gpt-4o" \
  python3 db/populate_nice_quotes.py

Optional flags:
  --overwrite    Re-populate rows that already have a nice_quote
  --opcs W37     Limit to one pathway
"""
import asyncio
import asyncpg
import argparse
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.clinical.pathway_map import OPCS_TO_NICE_MAP

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/sizor_ai",
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

TOP_K = 5          # chunks to retrieve per benchmark row
REQUEST_DELAY = 0.5  # seconds between LLM calls


async def _embed(text: str) -> list[float] | None:
    if not OPENAI_API_KEY:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": "text-embedding-3-small", "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


async def _retrieve_chunks(conn: asyncpg.Connection, embedding: list[float],
                            nice_ids: list[str], top_k: int) -> list[dict]:
    """Vector similarity search on clinical_knowledge filtered by NICE IDs."""
    emb_json = json.dumps(embedding)
    rows = await conn.fetch("""
        SELECT nice_id, heading, content, url
        FROM clinical_knowledge
        WHERE nice_id = ANY($1::text[])
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $2::vector
        LIMIT $3
    """, nice_ids, emb_json, top_k)
    return [dict(r) for r in rows]


async def _extract_quote(chunks: list[dict], domain: str,
                          expected_state: str, nice_ids: list[str]) -> str | None:
    """Call LLM to extract a verbatim NICE quote from retrieved chunks."""
    if not chunks:
        return None

    context = "\n\n---\n\n".join(
        f"[{c['nice_id']}] {c.get('heading') or ''}\n{c['content']}"
        for c in chunks
    )

    system = (
        "You are a clinical knowledge assistant. "
        "Extract a short, verbatim quote (1–2 sentences) from the provided NICE guidance text "
        "that best supports the expected clinical state for the given domain at the stated stage of recovery. "
        "Return ONLY the quote itself — no preamble, no attribution, no brackets. "
        "If no relevant text exists, return an empty string."
    )
    user = f"""Domain: {domain.replace("_", " ")}
Expected state: {expected_state}
NICE guidance IDs: {", ".join(nice_ids)}

Guidance text:
{context}

Extract the single most relevant verbatim sentence or phrase from the guidance above."""

    headers = {"Content-Type": "application/json"}
    if "claude" in LLM_MODEL.lower() and ANTHROPIC_API_KEY:
        headers["x-api-key"] = ANTHROPIC_API_KEY
        headers["anthropic-version"] = "2023-06-01"
        payload = {
            "model": LLM_MODEL,
            "max_tokens": 200,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        url = "https://api.anthropic.com/v1/messages"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
    elif OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
        payload = {
            "model": LLM_MODEL,
            "temperature": 0,
            "max_tokens": 200,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        url = "https://api.openai.com/v1/chat/completions"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-populate rows that already have a nice_quote")
    parser.add_argument("--opcs", default=None,
                        help="Limit to one OPCS code, e.g. W37")
    args = parser.parse_args()

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)

    # Fetch benchmark rows to process
    query_parts = ["SELECT id, opcs_code, domain, day_range_start, expected_state, nice_source FROM domain_benchmarks"]
    conditions = []
    if not args.overwrite:
        conditions.append("nice_quote IS NULL OR nice_quote = ''")
    if args.opcs:
        conditions.append(f"opcs_code = '{args.opcs}'")
    if conditions:
        query_parts.append("WHERE " + " AND ".join(conditions))
    query_parts.append("ORDER BY opcs_code, domain, day_range_start")

    async with pool.acquire() as conn:
        rows = await conn.fetch(" ".join(query_parts))

    print(f"Processing {len(rows)} benchmark rows")

    updated = 0
    skipped = 0

    for row in rows:
        opcs_code = row["opcs_code"]
        domain = row["domain"]
        day = row["day_range_start"]
        expected_state = row["expected_state"] or ""
        row_id = row["id"]

        # Get the NICE IDs for this pathway
        pathway = OPCS_TO_NICE_MAP.get(opcs_code, {})
        nice_ids = pathway.get("nice_ids", [])
        if not nice_ids:
            skipped += 1
            continue

        print(f"  [{opcs_code}] {domain} day {day} — {', '.join(nice_ids)}")

        # Build query for embedding
        query_text = f"{domain.replace('_', ' ')} {expected_state} post-discharge recovery"

        embedding = await _embed(query_text)
        if embedding is None:
            print("    Skipping — no embedding (OPENAI_API_KEY not set?)")
            skipped += 1
            continue

        async with pool.acquire() as conn:
            chunks = await _retrieve_chunks(conn, embedding, nice_ids, TOP_K)

        if not chunks:
            print(f"    No chunks found for {nice_ids}")
            skipped += 1
            continue

        quote = await _extract_quote(chunks, domain, expected_state, nice_ids)
        if not quote:
            skipped += 1
            continue

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE domain_benchmarks SET nice_quote = $1 WHERE id = $2",
                quote, row_id,
            )
        print(f"    → \"{quote[:80]}...\"" if len(quote) > 80 else f"    → \"{quote}\"")
        updated += 1

        await asyncio.sleep(REQUEST_DELAY)

    await pool.close()
    print(f"\nDone. Updated: {updated}, skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
