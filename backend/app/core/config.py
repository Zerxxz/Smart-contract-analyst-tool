from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Explorer API keys
    etherscan_api_key: str = ""
    bscscan_api_key: str = ""
    polygonscan_api_key: str = ""
    arbiscan_api_key: str = ""

    # AI
    ai_provider: str = "none"  # anthropic | openai | minimax | none
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # MiniMax (OpenAI-style chat completions endpoint)
    minimax_api_key: str = ""
    minimax_base_url: str = (
        "https://api.minimax.io/v1/text/chatcompletion_v2"
    )
    minimax_model: str = "MiniMax-M2.7"

    # CORS
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
