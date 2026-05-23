from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Explorer API keys
    etherscan_api_key: str = ""
    bscscan_api_key: str = ""
    polygonscan_api_key: str = ""
    arbiscan_api_key: str = ""

    # AI
    ai_provider: str = "none"  # anthropic | openai | none
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # CORS
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
