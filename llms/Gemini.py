import base64
import io
import asyncio
import os
from PIL import Image
from openai import OpenAI
from llms.BaseModel import BaseVideoModel, BaseLanguageModel

class Gemini(BaseVideoModel, BaseLanguageModel):
    def __init__(self, model_type="gemini-2.5-pro", tp=None, api_key=None, base_url=None):
        self.model_type = model_type
        self.key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.base_url = (
            base_url
            or os.getenv("GEMINI_BASE_URL")
            or "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.max_parallel_requests = int(os.getenv("GEMINI_MAX_PARALLEL_REQUESTS", "2"))
        if not self.key:
            raise ValueError(
                "GEMINI_API_KEY or GOOGLE_API_KEY is not set. Export it or choose a local model."
            )

    def generate_response(self, inputs, max_new_tokens=500, temperature=0.5, **kwargs):
        assert "text" in inputs.keys(), "Please provide a text prompt."
        
        model = OpenAI(
            api_key=self.key,
            base_url=self.base_url,
        )

        messages = [{"role": "system", "content": "You are a helpful assistant."}]

        if "video" in inputs.keys():
            images = [encode_image(image) for image in inputs["video"]]
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": inputs["text"]},
                    *[
                        {"type": "image_url", "image_url": {"url": f'data:image/jpeg;base64,{img}', "detail": "low"}}
                        for img in images
                    ]
                ]
            })
        else:
            messages.append({"role": "user", "content": inputs["text"]})

        response = model.chat.completions.create(
            model=self.model_type,
            messages=messages,
            temperature=temperature,
            max_tokens=max_new_tokens
        )

        return response.choices[0].message.content

    async def generate_response_async(self, inputs, max_new_tokens=500, temperature=0.5, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.generate_response, inputs, max_new_tokens, temperature
        )

    async def _generate_batch_response(self, batch_inputs, max_new_tokens=500, temperature=0.5, **kwargs):
        semaphore = asyncio.Semaphore(max(1, self.max_parallel_requests))

        async def _run_single(inputs):
            async with semaphore:
                return await self.generate_response_async(
                    inputs, max_new_tokens, temperature
                )

        tasks = [_run_single(inputs) for inputs in batch_inputs]
        responses = await asyncio.gather(*tasks)
        return responses

    def batch_generate_response(self, batch_inputs, max_new_tokens=500, temperature=0.5, **kwargs):
        return asyncio.run(
            self._generate_batch_response(batch_inputs, max_new_tokens, temperature)
        )


def encode_image(image):
    if isinstance(image, str):
        with open(image, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    elif isinstance(image, bytes):
        return base64.b64encode(image).decode('utf-8')
    elif isinstance(image, Image.Image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    else:
        raise ValueError("Unsupported image format.")
