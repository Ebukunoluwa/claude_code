import asyncio
from sqlalchemy import text
from app.database import engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT email FROM clinicians"))
        rows = result.fetchall()
        print("Clinicians:", rows)

asyncio.run(check())
