from dataclasses import dataclass
from pathlib import Path
import os
import logging
from dotenv import load_dotenv

# Automatically load .env from project root or current working dir
load_dotenv()

logger = logging.getLogger("cms")


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured, clean console logging for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )


@dataclass(frozen=True)
class Settings:
    # ------------------------------------------------------------------
    # Groq Settings
    # ------------------------------------------------------------------

    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_chat_model: str = os.getenv(
        "GROQ_CHAT_MODEL",
        "openai/gpt-oss-120b",
    )
    groq_whisper_model: str = os.getenv(
        "GROQ_WHISPER_MODEL",
        "whisper-large-v3",
    )
    groq_timeout: float = float(
        os.getenv("GROQ_TIMEOUT", "600.0")
    )

    # ------------------------------------------------------------------
    # Google Gemini Settings
    # ------------------------------------------------------------------

    google_api_key: str = os.getenv(
        "GOOGLE_API_KEY",
        "",
    )

    google_translation_model: str = os.getenv(
        "GOOGLE_TRANSLATION_MODEL",
        "gemini-2.5-flash",
    )

    # ------------------------------------------------------------------
    # Cloudflare Settings
    # ------------------------------------------------------------------

    cloudflare_account_id: str = os.getenv(
        "CLOUDFLARE_ACCOUNT_ID",
        "",
    )

    cloudflare_api_token: str = os.getenv(
        "CLOUDFLARE_API_TOKEN",
        "",
    )

    # ------------------------------------------------------------------
    # Meta / Facebook / Instagram Settings
    # ------------------------------------------------------------------

    meta_api_version: str = os.getenv(
        "META_API_VERSION",
        "v22.0",
    )

    fb_page_id: str = os.getenv(
        "PAGE_ID",
        "",
    )

    fb_page_access_token: str = os.getenv(
        "PAGE_ACCESS_TOKEN",
        "",
    )

    ig_account_id: str = os.getenv(
        "INSTAGRAM_ACCOUNT_ID",
        "",
    )

    ig_access_token: str = os.getenv(
        "ACCESS_TOKEN",
        "",
    )

    # ------------------------------------------------------------------
    # YouTube Settings
    # ------------------------------------------------------------------

    youtube_client_secrets_file: str = os.getenv(
        "YOUTUBE_CLIENT_SECRETS_FILE",
        "client_secret.json",
    )

    youtube_token_file: str = os.getenv(
        "YOUTUBE_TOKEN_FILE",
        "token_upload.json",
    )

    # ------------------------------------------------------------------
    # Project Directories
    # ------------------------------------------------------------------

    default_output_dir: Path = Path("output")


settings = Settings()