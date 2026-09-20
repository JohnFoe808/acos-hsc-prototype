from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "ACOS HSC Prototype"
    host: str = os.getenv("ACOS_HOST", "127.0.0.1")
    port: int = int(os.getenv("ACOS_PORT", "8000"))
    data_dir: Path = Path(os.getenv("ACOS_DATA_DIR", "data")).resolve()
    workspace_dir: Path = Path(os.getenv("ACOS_WORKSPACE_DIR", "data/workspace")).resolve()
    skill_promotion_threshold: int = int(os.getenv("ACOS_SKILL_PROMOTION_THRESHOLD", "3"))
    api_token: str | None = os.getenv("ACOS_API_TOKEN") or None
    require_auth: bool = os.getenv("ACOS_REQUIRE_AUTH", "false").lower() == "true"
    model_provider: str = os.getenv("ACOS_MODEL_PROVIDER", "mock")
    model_endpoint: str = os.getenv("ACOS_MODEL_ENDPOINT", "http://127.0.0.1:11434/v1")
    model_name: str = os.getenv("ACOS_MODEL_NAME", "local-model")
    model_api_key: str | None = os.getenv("ACOS_MODEL_API_KEY") or None
    model_timeout: float = float(os.getenv("ACOS_MODEL_TIMEOUT", "8"))
    model_retries: int = int(os.getenv("ACOS_MODEL_RETRIES", "1"))

    @property
    def database_path(self) -> Path:
        return self.data_dir / "acos.sqlite3"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.workspace_dir.mkdir(parents=True, exist_ok=True)
