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

    # Twilio — used by the inbound call webhook
    twilio_auth_token: str = ""


settings = Settings()
