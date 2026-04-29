from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ServiceNow
    servicenow_instance_url: str = Field(..., description="ServiceNow instance base URL")
    servicenow_username: str = Field(..., description="ServiceNow API username")
    servicenow_password: str = Field(..., description="ServiceNow API password")

    # Google Cloud / Vertex AI
    google_cloud_project: str = Field(..., description="GCP project ID")
    google_cloud_location: str = Field(default="global", description="GCP region")
    gemini_model: str = Field(default="gemini-2.0-flash", description="Gemini model name")

    # ChromaDB
    chroma_persist_dir: str = Field(default="./chroma_data", description="ChromaDB persistence directory")

    # App
    polling_interval_seconds: int = Field(default=30, description="Polling interval in seconds")
    auto_assign_threshold: float = Field(default=0.8, description="Confidence threshold for auto-assignment")
    suggest_threshold: float = Field(default=0.5, description="Confidence threshold for suggestions")
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
