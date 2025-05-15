"""
OpenAI and Azure OpenAI client utilities for chat and vision APIs.
"""

from typing import Optional, Dict, Any, List
import openai
import azure.openai

"""
Async-only LLM client utilities for OpenAI and Azure OpenAI chat and vision APIs.
"""

from typing import Dict, Any, List
import openai
import azure.openai

class LLMCompletionClient:
    """
    Async generic wrapper for LLM chat/vision completion endpoints.
    Accepts an async callable (OpenAI or Azure OpenAI completion endpoint) and error type.
    """
    def __init__(self, completion_callable, error_type):
        self.completion_callable = completion_callable
        self.error_type = error_type

    async def completion(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        try:
            response = await self.completion_callable(
                model=model,
                messages=messages,
                **kwargs
            )
            return response.model_dump()
        except self.error_type as e:
            raise RuntimeError(f"LLM API error: {e}")

    async def vision_completion(self, model: str, text: str, images: list, **kwargs) -> Dict[str, Any]:
        """
        Pass text and a list of images (each as a URL or a local file path).
        If the item starts with 'http://' or 'https://', it is sent as a URL.
        Otherwise, it is treated as a local file path and encoded as base64.
        """
        import os
        import mimetypes
        import base64

        def encode_image_to_base64(path: str) -> str:
            mime, _ = mimetypes.guess_type(path)
            mime = mime or 'image/png'
            with open(path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            return f"data:{mime};base64,{encoded}"

        content = [{"type": "text", "text": text}]
        for img in images:
            if not isinstance(img, str):
                raise ValueError(f"Image must be a URL or file path string: {img}")
            if img.startswith('http://') or img.startswith('https://'):
                content.append({"type": "image_url", "image_url": {"url": img}})
            else:
                # treat as local file path
                if not os.path.isfile(img):
                    raise ValueError(f"Image file does not exist: {img}")
                content.append({"type": "image_url", "image_url": {"url": encode_image_to_base64(img)}})
        messages = [{"role": "user", "content": content}]
        return await self.completion(model, messages, **kwargs)

class OpenAIClient(LLMCompletionClient):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.async_client = openai.AsyncClient(api_key=api_key, base_url=base_url)
        super().__init__(self.async_client.chat.completions.create, openai.OpenAIError)

class AzureOpenAIClient(LLMCompletionClient):
    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-02-15-preview"):
        async_client = azure.openai.AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint.rstrip("/"),
            api_version=api_version
        )
        super().__init__(async_client.chat.completions.create, azure.openai.AzureOpenAIError)