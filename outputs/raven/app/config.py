from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://raven:raven@db:5432/raven"
    openai_api_key: str = ""
    ai_provider: str = "ollama"
    ollama_url: str = "http://ollama:11434"
    searxng_url: str = "http://searxng:8080"
    local_voice_url: str = "http://voice:8090"
    raven_admin_password: str
    raven_jwt_secret: str
    raven_require_login: bool = False
    raven_model: str = "qwen3:8b"
    raven_voice_model: str = "qwen3:8b"
    raven_embedding_model: str = "nomic-embed-text"
    raven_realtime_model: str = "gpt-realtime-mini"
    raven_realtime_voice: str = "marin"
    raven_max_context_chunks: int = 6
    raven_max_context_chars: int = 12_000
    raven_public_origin: str = "http://localhost:8080"
    hermes_url: str = ""
    hermes_token: str = ""
    forge_enabled: bool = True
    content_text_provider: str = "active"
    content_text_model: str = "qwen3:8b"
    openai_fallback_model: str = "gpt-4.1-mini"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    nvidia_api_key: str = ""
    nvidia_research_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    raven_research_provider: str = "auto"
    raven_research_model: str = "gpt-5.6-terra"
    raven_research_budget_usd: float = 0.25
    comfyui_url: str = ""
    comfyui_workflow_path: str = "/config/comfyui-workflow.json"
    comfyui_prompt_node_id: str = "6"
    comfyui_prompt_input: str = "text"
    comfyui_image_workflow_path: str = "/config/comfyui-image-workflow.json"
    comfyui_image_prompt_node_id: str = "6"
    comfyui_video_workflow_path: str = "/config/comfyui-video-workflow.json"
    comfyui_video_prompt_node_id: str = "6"
    instagram_api_base: str = "https://graph.instagram.com"
    instagram_api_version: str = "v24.0"
    instagram_user_id: str = ""
    instagram_access_token: str = ""
    instagram_publish_enabled: bool = False
    x_access_token: str = ""
    x_publish_enabled: bool = False
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""
    youtube_publish_enabled: bool = False
    career_apply_url: str = ""
    career_apply_token: str = ""
    career_apply_enabled: bool = False
    desktop_bridge_url: str = "http://host.docker.internal:8765"
    desktop_bridge_token: str = ""
    desktop_bridge_enabled: bool = False
    discord_channels_json: str = "{}"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_refresh_token: str = ""
    spotify_playback_enabled: bool = False
    spotify_market: str = "US"
    raven_timezone: str = "America/New_York"
    raven_owner_name: str = "Noah"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings=Settings()  # type: ignore[call-arg]
    if settings.openrouter_model=='openrouter/free':settings.openrouter_model='nvidia/nemotron-3-super-120b-a12b:free'
    return settings
