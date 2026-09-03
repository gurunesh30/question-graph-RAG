"""OpenRouter LLM client.

Encapsulates HTTP transport, auth header construction, JSON-mode prompts,
and retry logic.  Pipelines should not import ``requests`` directly.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import requests
from requests.exceptions import ConnectionError as ReqConnError, Timeout

from kaqg.clients.retry import retry
from kaqg.config import Settings, get_settings
from kaqg.errors import AuthenticationError, ConnectionError, GenerationError

LOGGER = logging.getLogger("kaqg.openrouter")

DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    """Thin OpenRouter chat-completions client with JSON-mode support."""

    def __init__(self, settings: Settings | None = None,
                 session: requests.Session | None = None) -> None:
        self._settings = settings or get_settings()
        self._session = session or requests.Session()

    @property
    def model(self) -> str:
        return self._settings.openrouter_model

    def _headers(self) -> dict[str, str]:
        if not self._settings.openrouter_api_key:
            raise AuthenticationError("OPENROUTER_API_KEY missing from environment")
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

    @retry()
    def complete_json(self, prompt: str, *,
                      model: str | None = None,
                      timeout: float | None = None) -> dict[str, Any]:
        """Send a single chat-completion request and return the parsed JSON.

        The caller is responsible for the prompt content; this method only
        wraps transport, error mapping, and JSON parsing.
        """
        body = {
            "model": model or self.model,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        }
        url = DEFAULT_URL
        try:
            resp = self._session.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=timeout or self._settings.request_timeout,
            )
        except (ReqConnError, Timeout) as exc:
            raise ConnectionError(f"OpenRouter request failed: {exc}") from exc
        if resp.status_code == 401:
            raise AuthenticationError("OpenRouter rejected the API key")
        if resp.status_code >= 500:
            raise ConnectionError(f"OpenRouter {resp.status_code}: {resp.text[:200]}")
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise GenerationError(
                f"OpenRouter returned {resp.status_code}: {resp.text[:200]}"
            ) from exc

        try:
            payload = resp.json()
            content = payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise GenerationError(
                f"Could not parse OpenRouter response: {exc}"
            ) from exc

    def close(self) -> None:
        self._session.close()
