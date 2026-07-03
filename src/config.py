"""Load config.yaml + environment secrets (.env locally, GitHub Secrets in CI)."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def load_config() -> dict:
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Secrets:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    CALLMEBOT_PHONE = os.getenv("CALLMEBOT_PHONE", "")       # e.g. +9198xxxxxxxx
    CALLMEBOT_APIKEY = os.getenv("CALLMEBOT_APIKEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    RESUME_B64 = os.getenv("RESUME_B64", "")                 # optional: base64 resume for public repos
    RESUME_EXT = os.getenv("RESUME_EXT", "pdf")              # extension of RESUME_B64 content

    @classmethod
    def telegram_ready(cls) -> bool:
        return bool(cls.TELEGRAM_BOT_TOKEN and cls.TELEGRAM_CHAT_ID)

    @classmethod
    def whatsapp_ready(cls) -> bool:
        return bool(cls.CALLMEBOT_PHONE and cls.CALLMEBOT_APIKEY)

    @classmethod
    def gemini_ready(cls) -> bool:
        return bool(cls.GEMINI_API_KEY)
