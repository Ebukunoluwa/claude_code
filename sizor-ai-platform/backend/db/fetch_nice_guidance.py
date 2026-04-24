"""
Fetch NICE guidance pages, chunk text, embed with OpenAI, store in clinical_knowledge.

Run once (or to refresh):
  DATABASE_URL="postgresql://postgres:postgres@localhost:5432/sizor_ai" \
  OPENAI_API_KEY="sk-..." \
  python3 db/fetch_nice_guidance.py

Fetches recommendation pages for every NICE ID referenced in OPCS_TO_NICE_MAP.
Stores ~500-char text chunks with 1536-dim embeddings in clinical_knowledge table.
"""
import asyncio
import asyncpg
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.clinical_intelligence.pathway_map import OPCS_TO_NICE_MAP

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/sizor_ai",
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

CHUNK_SIZE = 500          # characters per chunk
CHUNK_OVERLAP = 80        # overlap between chunks
REQUEST_DELAY = 1.5       # seconds between NICE HTTP requests
EMBEDDING_BATCH = 20      # embed N chunks per API call

NICE_URL_TEMPLATES = [
    "https://www.nice.org.uk/guidance/{id}/chapter/Recommendations",
    "https://www.nice.org.uk/guidance/{id}/chapter/1-Guidance",
    "https://www.nice.org.uk/guidance/{id}/chapter/Quality-statements",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SizorAI-ClinicalResearch/1.0; "
        "+https://sizor.ai/clinical-ai)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
}


def _collect_nice_ids() -> dict[str, list[str]]:
    """Return {nice_id: [opcs_codes...]} from pathway map."""
    result: dict[str, list[str]] = {}
    for opcs, data in OPCS_TO_NICE_MAP.items():
        for nid in data.get("nice_ids", []):
            result.setdefault(nid, []).append(opcs)
    return result


def _parse_html(html: str, nice_id: str, url: str) -> list[dict]:
    """Extract recommendation text blocks from NICE HTML page."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove navigation, footer, header, script, style
    for tag in soup.find_all(["nav", "footer", "header", "script", "style",
                               "aside", "form"]):
        tag.decompose()

    chunks = []

    # Walk sections — each h2/h3 heading + following paragraphs
    headings = soup.find_all(["h2", "h3", "h4"])
    if not headings:
        # No headings — just grab all paragraph text
        body_text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
        chunks += _split_text(body_text, None, nice_id, url)
        return chunks

    for heading in headings:
        heading_text = heading.get_text(" ", strip=True)
        # Skip nav-style headings
        if len(heading_text) > 120 or heading_text.lower() in {"contents", "on this page"}:
            continue

        # Collect sibling paragraphs/lists until the next heading
        content_parts = []
        for sib in heading.find_next_siblings():
            if sib.name in ["h2", "h3", "h4"]:
                break
            text = sib.get_text(" ", strip=True)
            if text:
                content_parts.append(text)

        section_text = " ".join(content_parts)
        if len(section_text) < 60:
            continue

        chunks += _split_text(section_text, heading_text, nice_id, url)

    return chunks


def _split_text(text: str, heading: str | None, nice_id: str, url: str) -> list[dict]:
    """Split text into overlapping chunks."""
    # Normalise whitespace
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        chunks.append({
            "nice_id": nice_id,
            "heading": heading,
            "content": chunk,
            "chunk_index": idx,
            "url": url,
        })
        idx += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
        if start >= len(text):
            break

    return chunks


async def _fetch_nice_page(client: httpx.AsyncClient, nice_id: str) -> tuple[str, str] | None:
    """Try URL templates in order; return (html, url) for first success."""
    id_lower = nice_id.lower()
    for template in NICE_URL_TEMPLATES:
        url = template.format(id=id_lower)
        try:
            r = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
            if r.status_code == 200 and len(r.text) > 2000:
                print(f"  OK  {url}")
                return r.text, url
        except Exception as e:
            print(f"  ERR {url}: {e}")
        await asyncio.sleep(0.3)
    print(f"  SKIP {nice_id} — no page found")
    return None


async def _embed_chunks(chunks: list[dict]) -> list[list[float]] | None:
    """Call OpenAI embeddings API; return list of vectors."""
    if not OPENAI_API_KEY:
        print("  WARNING: OPENAI_API_KEY not set — embeddings skipped")
        return None

    texts = [c["content"] for c in chunks]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": "text-embedding-3-small", "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
    return [item["embedding"] for item in data["data"]]


async def _store_chunks(pool: asyncpg.Pool, chunks: list[dict],
                        embeddings: list[list[float]] | None,
                        opcs_codes: list[str]) -> int:
    """Upsert chunks into clinical_knowledge by (nice_id, chunk_index)."""
    rows_inserted = 0
    async with pool.acquire() as conn:
        for i, chunk in enumerate(chunks):
            emb = embeddings[i] if embeddings else None
            emb_json = json.dumps(emb) if emb else None

            await conn.execute("""
                INSERT INTO clinical_knowledge
                    (id, nice_id, opcs_codes, chunk_index, heading, content,
                     embedding, url, fetched_at, token_count)
                VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7::vector,
                    $8, $9, $10
                )
                ON CONFLICT (nice_id, chunk_index) DO UPDATE
                    SET content    = EXCLUDED.content,
                        heading    = EXCLUDED.heading,
                        embedding  = EXCLUDED.embedding,
                        url        = EXCLUDED.url,
                        fetched_at = EXCLUDED.fetched_at,
                        token_count= EXCLUDED.token_count
            """,
                str(uuid.uuid4()),
                chunk["nice_id"],
                opcs_codes,
                chunk["chunk_index"],
                chunk["heading"],
                chunk["content"],
                emb_json,
                chunk["url"],
                datetime.now(timezone.utc),
                len(chunk["content"]) // 4,  # rough token estimate
            )
            rows_inserted += 1
    return rows_inserted


async def _ensure_schema(pool: asyncpg.Pool):
    """Create clinical_knowledge table and unique index if not present."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clinical_knowledge (
                id           UUID PRIMARY KEY,
                nice_id      VARCHAR(20) NOT NULL,
                opcs_codes   TEXT[]      NOT NULL DEFAULT '{}',
                chunk_index  INTEGER     NOT NULL,
                heading      TEXT,
                content      TEXT        NOT NULL,
                embedding    vector(1536),
                url          TEXT,
                fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
                token_count  INTEGER
            )
        """)
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_ck_nice_chunk
            ON clinical_knowledge (nice_id, chunk_index)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ck_nice_id
            ON clinical_knowledge (nice_id)
        """)
        # Enable vector extension (already enabled via docker image, but just in case)
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception:
            pass
        print("Schema OK")


async def main():
    nice_to_opcs = _collect_nice_ids()
    print(f"Found {len(nice_to_opcs)} unique NICE IDs across all pathways")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)
    await _ensure_schema(pool)

    total_chunks = 0
    total_stored = 0

    async with httpx.AsyncClient() as http_client:
        for nice_id, opcs_codes in sorted(nice_to_opcs.items()):
            print(f"\n[{nice_id}] ({', '.join(opcs_codes)})")

            result = await _fetch_nice_page(http_client, nice_id)
            if result is None:
                await asyncio.sleep(REQUEST_DELAY)
                continue

            html, url = result
            chunks = _parse_html(html, nice_id, url)
            print(f"  Parsed {len(chunks)} chunks")

            if not chunks:
                await asyncio.sleep(REQUEST_DELAY)
                continue

            total_chunks += len(chunks)

            # Embed in batches
            all_embeddings = []
            for batch_start in range(0, len(chunks), EMBEDDING_BATCH):
                batch = chunks[batch_start: batch_start + EMBEDDING_BATCH]
                embs = await _embed_chunks(batch)
                if embs:
                    all_embeddings.extend(embs)
                else:
                    all_embeddings.extend([None] * len(batch))
                await asyncio.sleep(0.2)  # rate limit embeddings API

            stored = await _store_chunks(
                pool, chunks,
                all_embeddings if all(e is not None for e in all_embeddings) else None,
                opcs_codes,
            )
            total_stored += stored
            print(f"  Stored {stored} rows")

            await asyncio.sleep(REQUEST_DELAY)

    await pool.close()
    print(f"\nDone. Total chunks: {total_chunks}, stored: {total_stored}")


if __name__ == "__main__":
    asyncio.run(main())
