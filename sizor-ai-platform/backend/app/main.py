from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .api import auth, dashboard, patients, calls, decisions, internal, telephony, chat, probe_calls, inbound, reports
from .api import benchmarks as benchmarks_api

app = FastAPI(title="Sizor AI Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(patients.router)
app.include_router(calls.router)
app.include_router(decisions.router)
app.include_router(internal.router)
app.include_router(telephony.router)
app.include_router(chat.router)
app.include_router(probe_calls.router)
app.include_router(inbound.router)
app.include_router(benchmarks_api.router)
app.include_router(reports.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
