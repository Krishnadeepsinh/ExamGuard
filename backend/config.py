"""Backend configuration loaded only from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str
    store_backend: str

    @property
    def supabase_enabled(self) -> bool:
        return self.store_backend == "supabase" and bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def redis_enabled(self) -> bool:
        return bool(self.upstash_redis_rest_url and self.upstash_redis_rest_token)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    load_env_file(root / ".env")
    load_env_file(root / "backend" / ".env")
    return Settings(
        supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        upstash_redis_rest_url=os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/"),
        upstash_redis_rest_token=os.getenv("UPSTASH_REDIS_REST_TOKEN", ""),
        store_backend=os.getenv("EXAMGUARD_STORE", "local").lower(),
    )


settings = load_settings()
