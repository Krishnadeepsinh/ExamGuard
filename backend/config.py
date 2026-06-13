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
    gemini_api_keys: tuple[str, ...]
    gemini_model: str
    cors_origins: tuple[str, ...]
    cors_origin_regex: str
    demo_access_enabled: bool
    demo_teacher_email: str
    demo_teacher_password: str
    demo_session_secret: str

    @property
    def supabase_enabled(self) -> bool:
        return self.store_backend == "supabase" and bool(
            self.supabase_url 
            and self.supabase_service_role_key 
            and not self.supabase_url.startswith("your-")
        )

    @property
    def redis_enabled(self) -> bool:
        return bool(
            self.upstash_redis_rest_url 
            and self.upstash_redis_rest_token 
            and not self.upstash_redis_rest_url.startswith("your-")
        )


def load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


def load_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    # Backend-local secrets take precedence over repository-level defaults.
    load_env_file(root / "backend" / ".env", override=True)
    load_env_file(root / ".env")
    raw_gemini_keys = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
    gemini_api_keys = tuple(dict.fromkeys(key.strip() for key in raw_gemini_keys.split(",") if key.strip()))
    return Settings(
        supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        upstash_redis_rest_url=os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/"),
        upstash_redis_rest_token=os.getenv("UPSTASH_REDIS_REST_TOKEN", ""),
        store_backend=os.getenv("EXAMGUARD_STORE", "local").lower(),
        gemini_api_keys=gemini_api_keys,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        cors_origins=tuple(origin.strip() for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
        ).split(",") if origin.strip()),
        cors_origin_regex=os.getenv("CORS_ORIGIN_REGEX", "").strip(),
        demo_access_enabled=os.getenv("DEMO_ACCESS_ENABLED", "true").lower() in {"1", "true", "yes"},
        demo_teacher_email=os.getenv("DEMO_TEACHER_EMAIL", "teacher@demo.examguard.ai").strip().lower(),
        demo_teacher_password=os.getenv("DEMO_TEACHER_PASSWORD", "ExamGuard-Demo-2026!"),
        demo_session_secret=os.getenv("DEMO_SESSION_SECRET", ""),
    )


settings = load_settings()
