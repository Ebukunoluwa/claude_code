"""Seeds domain_benchmarks from clinical_intelligence/benchmarks.py BENCHMARK_DATA."""
import asyncio
import asyncpg
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clinical_intelligence.benchmarks import BENCHMARK_DATA


async def seed(pool):
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE domain_benchmarks")
        rows = []
        for opcs_code, pathway in BENCHMARK_DATA.items():
            call_days = pathway["call_days"]
            for domain, day_map in pathway["domains"].items():
                sorted_days = sorted(day_map.keys())
                for i, day_start in enumerate(sorted_days):
                    day_end = sorted_days[i + 1] - 1 if i + 1 < len(sorted_days) else day_start + 6
                    ideal, upper, state, nice = day_map[day_start]
                    rows.append((opcs_code, domain, day_start, day_end, ideal, upper, state, nice))

        await conn.executemany("""
            INSERT INTO domain_benchmarks
                (opcs_code, domain, day_range_start, day_range_end,
                 expected_score, upper_bound_score, expected_state, nice_source)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            ON CONFLICT (opcs_code, domain, day_range_start) DO UPDATE
                SET expected_score=EXCLUDED.expected_score,
                    upper_bound_score=EXCLUDED.upper_bound_score,
                    expected_state=EXCLUDED.expected_state,
                    nice_source=EXCLUDED.nice_source
        """, rows)
    print(f"Seeded {len(rows)} benchmark rows across {len(BENCHMARK_DATA)} pathways")


if __name__ == "__main__":
    async def main():
        pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
        await seed(pool)
        await pool.close()

    asyncio.run(main())
