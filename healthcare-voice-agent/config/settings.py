from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LiveKit ──────────────────────────────────────────────────────────────
    livekit_url: str = Field(..., description="wss://your-project.livekit.cloud")
    livekit_api_key: str = Field(..., description="LiveKit API key")
    livekit_api_secret: str = Field(..., description="LiveKit API secret")

    # ── Deepgram ─────────────────────────────────────────────────────────────
    deepgram_api_key: str = Field(..., description="Deepgram API key")

    # ── Cartesia ─────────────────────────────────────────────────────────────
    cartesia_api_key: str = Field(..., description="Cartesia API key")
    cartesia_voice_id: str = Field(
        default="ee7ea9f8-c0c1-498c-9279-764d6b56d189",
        description="Cartesia voice ID (British English)",
    )

    # ── Groq ─────────────────────────────────────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API key")
    groq_model: str = Field(default="openai/gpt-oss-120b", description="Groq model ID")

    # ── OpenAI (fallback LLM) ────────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API key (fallback LLM)")

    # ── AssemblyAI (fallback STT) ────────────────────────────────────────────
    assemblyai_api_key: str = Field(default="", description="AssemblyAI API key (fallback STT)")

    # ── ElevenLabs (fallback TTS) ────────────────────────────────────────────
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key (fallback TTS)")
    elevenlabs_voice_id: str = Field(
        default="l7kNoIfnJKPg7779LI2t",
        description="ElevenLabs voice ID",
    )

    # ── Twilio ───────────────────────────────────────────────────────────────
    twilio_account_sid: str = Field(..., description="Twilio account SID")
    twilio_auth_token: str = Field(..., description="Twilio auth token")
    twilio_phone_number: str = Field(..., description="Twilio outbound phone number")
    twilio_sip_trunk_id: str = Field(..., description="LiveKit SIP trunk resource ID")

    # ── Storage ──────────────────────────────────────────────────────────────
    sqlite_db_path: str = Field(default="data/healthcare.db")
    chroma_persist_path: str = Field(default="data/chroma")

    # ── Dashboard ────────────────────────────────────────────────────────────
    dashboard_secret_key: str = Field(default="change-me-in-production")
    dashboard_host: str = Field(default="0.0.0.0")
    dashboard_port: int = Field(default=8000)

    # ── Scheduler ────────────────────────────────────────────────────────────
    scheduler_poll_interval_seconds: int = Field(default=60)


# Singleton — import this everywhere
settings = Settings()
