"""
Ollama LLM Integration

Local LLM support using Ollama for cost-free inference.
Supports multiple models: qwen2.5, llama3, mistral, etc.
"""

import json
import logging
import os
from typing import Any

import httpx

from utils.logging import SessionLogger

_log = SessionLogger("ollama")
logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama local LLM API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        """Send chat completion request to Ollama."""
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }

        try:
            response = await self._client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPError as exc:
            _log.error("ollama_request_failed", error=str(exc), model=self._model)
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        """Simple generate endpoint."""
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            **kwargs,
        }

        try:
            response = await self._client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPError as exc:
            _log.error("ollama_generate_failed", error=str(exc))
            raise

    async def list_models(self) -> list[dict]:
        """List available models."""
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except httpx.HTTPError as exc:
            _log.error("ollama_list_models_failed", error=str(exc))
            return []

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self._client.get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False


_ollama_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    """Get or create Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        _ollama_client = OllamaClient(base_url=base_url, model=model)
    return _ollama_client
