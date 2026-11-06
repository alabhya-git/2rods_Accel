"""Runtime settings. Every value can be set by environment variable (prefix-free)."""
from __future__ import annotations

import base64
import os
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Accel Business · Udyam Digital"
    environment: str = "dev"  # dev | prod
    data_dir: Path = ROOT / "data"
    storage_dir: Path = ROOT / "var" / "storage"
    web_dist: Path = ROOT / "web" / "dist"

    database_url: str = f"sqlite:///{ROOT / 'var' / 'udyam.db'}"
    redis_url: str | None = None  # enables the cross-instance event bus

    # 32-byte key, base64. Generated for dev if missing; must be set in prod (KMS in production).
    master_key_b64: str | None = None

    # LLM: provider = none | anthropic | gemini | openai
    llm_provider: str = "none"
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None  # for OpenAI-compatible providers (Groq, OpenRouter, Azure, vLLM)
    llm_timeout_s: float = 20.0

    # WhatsApp Cloud API (optional)
    whatsapp_token: str | None = None
    whatsapp_phone_id: str | None = None
    whatsapp_verify_token: str = "accel-verify"

    whatsapp_app_secret: str | None = None  # verifies X-Hub-Signature-256 on webhooks

    backoffice_passcode: str = "accel-demo"  # demo partner desk only (judge mode); production uses STAFF_ACCOUNTS
    staff_accounts: str | None = None  # JSON {"user": {"secret", "role", "name", "partner_id"}}
    judge_mode: bool = True
    mock_adapters_allowed: bool = True  # registries, DigiLocker, e-sign, telco, billing run as mocks

    # Speech (optional): Sarvam for Indian-language speech; browser speech is the fallback
    sarvam_api_key: str | None = None

    # The dataset's reference "today" for date checks (README: use 2026-07-15).
    reference_date: date = date(2026, 7, 15)
    address_proof_max_age_days: int = 90
    document_retention_days: int = 30
    abandoned_session_days: int = 30

    cors_origins: str = "*"
    public_url: str = "http://localhost:8000"  # absolute links in WhatsApp messages

    def master_key(self) -> bytes:
        if self.master_key_b64:
            key = base64.b64decode(self.master_key_b64)
            if len(key) != 32:
                raise ValueError("MASTER_KEY_B64 must decode to 32 bytes")
            return key
        if self.environment == "prod":
            raise RuntimeError("MASTER_KEY_B64 is required in prod")
        keyfile = ROOT / "var" / "dev_master.key"
        keyfile.parent.mkdir(parents=True, exist_ok=True)
        if not keyfile.exists():
            keyfile.write_bytes(os.urandom(32))
        return keyfile.read_bytes()


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    for prefix in ("postgres://", "postgresql://"):
        if s.database_url.startswith(prefix):  # managed Postgres URLs -> psycopg 3 driver
            s.database_url = "postgresql+psycopg://" + s.database_url[len(prefix):]
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    if s.database_url.startswith("sqlite:///"):
        Path(s.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return s
