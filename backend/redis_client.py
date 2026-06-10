"""Small Upstash Redis REST client for live exam hot state."""

from __future__ import annotations

import json
from typing import Any
from urllib import request

from backend.config import settings


class RedisHotState:
    def __init__(self) -> None:
        self.enabled = settings.redis_enabled
        self.base_url = settings.upstash_redis_rest_url
        self.token = settings.upstash_redis_rest_token

    def command(self, *parts: str) -> Any:
        if not self.enabled:
            return None
        encoded = "/".join(request.pathname2url(part) for part in parts)
        req = request.Request(
            f"{self.base_url}/{encoded}",
            method="GET",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        with request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("result")

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int = 3600) -> None:
        if not self.enabled:
            return
        self.command("SET", key, json.dumps(value), "EX", str(ttl_seconds))

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self.command("GET", key)
        return json.loads(raw) if raw else None

    def push_event(self, key: str, event: dict[str, Any], ttl_seconds: int = 3600) -> None:
        if not self.enabled:
            return
        self.command("LPUSH", key, json.dumps(event))
        self.command("EXPIRE", key, str(ttl_seconds))

    def list_events(self, key: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.command("LRANGE", key, "0", str(max(limit - 1, 0)))
        if not rows:
            return []
        return [json.loads(row) for row in rows]


redis_hot_state = RedisHotState()
