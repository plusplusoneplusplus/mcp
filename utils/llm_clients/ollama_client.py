"""Async Ollama LLM client using httpx."""

from typing import Dict, Any, List
import httpx


class OllamaClient:
    """Async client for the Ollama `/api/chat` endpoint."""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str | None = None):
        self.async_client = httpx.AsyncClient(base_url=base_url)
        self.default_model = default_model

    async def completion(
        self, messages: List[Dict[str, Any]], model: str | None = None, **kwargs
    ) -> Dict[str, Any]:
        """Run a chat completion via the Ollama API."""
        model_to_use = model or self.default_model
        if not model_to_use:
            raise ValueError("No model specified and no default_model set.")
        payload = {"model": model_to_use, "messages": messages, **kwargs}
        try:
            response = await self.async_client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"LLM API error: {e}") from e

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.async_client.aclose()

