import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "PDF Editor API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "High-performance REST API for PDF editing utilities: "
        "Translation (with Bangla Unicode shaping) and Watermarking."
    )
    API_PREFIX: str = "/api"

    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    FONTS_DIR: Path = BASE_DIR / "fonts"
    BANGLA_FONT_PATH: Path = FONTS_DIR / "Kalpurush.ttf"
    NOTO_FONT_PATH: Path = FONTS_DIR / "NotoSansBengali-Regular.ttf"

    # Upload limits (25 MB default)
    MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024

    # Allowed CORS origins
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()
