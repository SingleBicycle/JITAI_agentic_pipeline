import asyncio
import base64
import io
import os
from typing import Any

from PIL import Image
from openai import OpenAI

from llms.BaseModel import BaseLanguageModel, BaseVideoModel


def _encode_image(image: Any) -> str:
    if isinstance(image, str):
        with open(image, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    if isinstance(image, bytes):
        return base64.b64encode(image).decode("utf-8")
    if isinstance(image, Image.Image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    raise ValueError("Unsupported image format.")


class OpenAIChat(BaseVideoModel, BaseLanguageModel):
    def __init__(self, model_type="gpt-4o", tp=None, api_key=None, base_url=None):
        self.model_type = model_type
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.max_parallel_requests = int(os.getenv("OPENAI_MAX_PARALLEL_REQUESTS", "2"))
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Export it or choose a local model such as qwenvl/qwenlm."
            )

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)

    def _build_messages(self, inputs):
        if "video" not in inputs:
            return [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": inputs["text"]},
            ]

        content = []
        for image in inputs["video"]:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{_encode_image(image)}",
                    },
                }
            )
        content.append({"type": "text", "text": inputs["text"]})
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": content},
        ]

    def generate_response(self, inputs, max_new_tokens=512, temperature=0.2, **kwargs):
        assert "text" in inputs.keys(), "Please provide a text prompt."

        response = self.client.chat.completions.create(
            model=self.model_type,
            messages=self._build_messages(inputs),
            temperature=temperature,
            max_tokens=max_new_tokens,
        )
        return response.choices[0].message.content

    async def generate_response_async(self, inputs, max_new_tokens=512, temperature=0.2, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.generate_response, inputs, max_new_tokens, temperature
        )

    async def _generate_batch_response(
        self, batch_inputs, max_new_tokens=512, temperature=0.2, **kwargs
    ):
        semaphore = asyncio.Semaphore(max(1, self.max_parallel_requests))

        async def _run_single(inputs):
            async with semaphore:
                return await self.generate_response_async(
                    inputs, max_new_tokens, temperature
                )

        tasks = [_run_single(inputs) for inputs in batch_inputs]
        return await asyncio.gather(*tasks)

    def batch_generate_response(self, batch_inputs, max_new_tokens=512, temperature=0.2, **kwargs):
        return asyncio.run(
            self._generate_batch_response(batch_inputs, max_new_tokens, temperature)
        )
