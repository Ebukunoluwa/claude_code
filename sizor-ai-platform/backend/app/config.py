from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/sizor_ai"
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Internal API key — used by the voice agent to ingest calls without JWT
    internal_api_key: str = "change-me-internal-key"

    # LLM — change this one value to swap providers. All AI calls go through LLMClient.
    llm_model: str = "gpt-4o"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # Twilio — used by the inbound call webhook and probe call outbound dialling
    twilio_auth_token: str = ""
    twilio_account_sid: str = ""
    twilio_phone_number: str = ""   # E.164 format, e.g. +441234567890

    # Public URL of this backend (used to build TwiML callback URLs)
    backend_public_url: str = "http://localhost:8000"

    # LiveKit — used to initiate probe calls via SIP (same credentials as the voice agent)
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    twilio_sip_trunk_id: str = ""       # LiveKit SIP trunk resource ID (ST_xxx)
    livekit_sip_inbound_domain: str = ""  # e.g. xxxxx.pstn.livekit.cloud

    # SMTP — for sending patient summary reports by email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@sizor.ai"
    smtp_use_tls: bool = True

    # Phase 4 — coverage enforcement.
    # When False, pipeline_tasks Task 1b short-circuits (no LLM call, no
    # CallCoverageReport row written). Useful for staged rollout or to
    # disable during incident response if the coverage classifier is
    # behaving badly.
    coverage_enforcement_enabled: bool = True

    # Coverage threshold for dashboard flagging. Calls whose
    # coverage_percentage falls below this value are surfaced to the
    # clinician dashboard as incomplete.
    #
    # CLINICAL_REVIEW_NEEDED: default for v1; clinician to confirm per
    # pathway risk profile; may fork by pathway in Phase 6. 0.80 is a
    # placeholder — high-risk pathways (K60 heart failure, S01 stroke,
    # Z03_MH mental health once unblocked) may warrant 0.95+ while
    # lower-acuity pathways (H01 appendectomy, J18_CHOLE cholecystectomy)
    # may be acceptable at 0.70. Phase 6 will likely replace this scalar
    # with a per-pathway dict.
    coverage_threshold: float = 0.80


settings = Settings()
