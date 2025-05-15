"""
Async-only LLM client utilities for OpenAI and Azure OpenAI chat and vision APIs.
"""

from typing import Dict, Any, List
import openai


class LLMCompletionClient:
    """
    Async generic wrapper for LLM chat/vision completion endpoints.
    Accepts an async callable (OpenAI or Azure OpenAI completion endpoint), error type, and an optional default_model.
    If model is not specified in completion/vision_completion, self.default_model is used.
    """

    def __init__(self, completion_callable, error_type, default_model: str = None):
        self.completion_callable = completion_callable
        self.error_type = error_type
        self.default_model = default_model

    async def completion(
        self, messages: List[Dict[str, Any]], model: str = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Run a chat/vision completion. If model is not provided, uses self.default_model.
        """
        model_to_use = model or self.default_model
        if not model_to_use:
            raise ValueError("No model specified and no default_model set.")
        try:
            response = await self.completion_callable(
                model=model_to_use, messages=messages, **kwargs
            )
            return response.model_dump()
        except self.error_type as e:
            raise RuntimeError(f"LLM API error: {e}")

    async def vision_completion(
        self, text: str, images: list, model: str = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Pass text and a list of images (each as a URL or a local file path).
        If the item starts with 'http://' or 'https://', it is sent as a URL.
        Otherwise, it is treated as a local file path and encoded as base64.
        If model is not provided, uses self.default_model.
        """
        import os
        import mimetypes
        import base64

        def encode_image_to_base64(path: str) -> str:
            mime, _ = mimetypes.guess_type(path)
            mime = mime or "image/png"
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{encoded}"

        content = [{"type": "text", "text": text}]
        for img in images:
            if not isinstance(img, str):
                raise ValueError(f"Image must be a URL or file path string: {img}")
            if img.startswith("http://") or img.startswith("https://"):
                content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                # treat as local file path
                if not os.path.isfile(img):
                    raise ValueError(f"Image file does not exist: {img}")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": encode_image_to_base64(img)},
                    }
                )
        messages = [{"role": "user", "content": content}]
        return await self.completion(messages, model=model, **kwargs)


class OpenAIClient(LLMCompletionClient):
    """
    Async OpenAI client for chat and vision completion APIs.
    Optionally set a default_model for all completions.
    The base_url parameter can be set to an Azure OpenAI resource endpoint for Azure usage.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = None,
    ):
        self.async_client = openai.AsyncClient(api_key=api_key, base_url=base_url)
        super().__init__(
            self.async_client.chat.completions.create,
            openai.OpenAIError,
            default_model=default_model,
        )
