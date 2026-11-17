"""Minimal Telegram Bot API client. Dry-run mode performs no network calls."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)
API_BASE = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4000


@dataclass
class SendResult:
    ok: bool
    dry_run: bool = False
    error: str | None = None
    retry_after: int | None = None


class TelegramClient:
    def __init__(self, token: str | None, *, dry_run: bool, timeout: float = 15.0) -> None:
        self._token = token
        self.dry_run = dry_run or not token
        self._client = httpx.Client(timeout=timeout) if not self.dry_run else None

    def _sanitize(self, message: str) -> str:
        return message.replace(self._token, "***") if self._token else message

    def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        assert self._client is not None
        resp = self._client.post(f"{API_BASE}/bot{self._token}/{method}", json=payload)
        try:
            return resp.json()
        except ValueError:
            return {"ok": False, "description": f"HTTP {resp.status_code}"}

    def send_message(self, chat_id: str, text: str) -> SendResult:
        if self.dry_run:
            logger.info("Telegram dry-run: message to chat %s suppressed (%d chars)", chat_id, len(text))
            return SendResult(ok=True, dry_run=True)
        try:
            data = self._call(
                "sendMessage",
                {"chat_id": chat_id, "text": text[:MAX_MESSAGE_LENGTH], "parse_mode": "HTML", "disable_web_page_preview": True},
            )
        except httpx.HTTPError as exc:
            return SendResult(ok=False, error=self._sanitize(f"Network error: {type(exc).__name__}"))
        if data.get("ok"):
            return SendResult(ok=True)
        params = data.get("parameters") or {}
        return SendResult(ok=False, error=self._sanitize(str(data.get("description", "Telegram error")))[:500],
                          retry_after=params.get("retry_after"))

    def get_updates(self, offset: int) -> list[dict[str, Any]]:
        if self.dry_run:
            return []
        try:
            data = self._call("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message"]})
        except httpx.HTTPError as exc:
            logger.warning("Telegram getUpdates failed: %s", self._sanitize(type(exc).__name__))
            return []
        return data.get("result", []) if data.get("ok") else []

    def close(self) -> None:
        if self._client:
            self._client.close()
