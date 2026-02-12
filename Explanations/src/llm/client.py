# /src/llm/client.py
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI


@dataclass
class LLMResult:
    text: str
    usage: Dict[str, int]
    latency_s: float
    raw: Any


class client:
    def __init__(
        self,
        base_url_env: str = "LOCAL_OPENAI_BASE_URL",
        api_key_env: str = "LOCAL_OPENAI_API_KEY",
        model_env: str = "LOCAL_OPENAI_MODEL",
    ):
        load_dotenv()
        self.base_url = os.getenv(base_url_env)
        self.api_key = os.getenv(api_key_env, "ollama")
        self.model = os.getenv(model_env)

        if not self.base_url:
            raise RuntimeError(f"Falta {base_url_env} en el .env")
        if not self.model:
            raise RuntimeError(f"Falta {model_env} en el .env")

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = time.time() - t0

        text = resp.choices[0].message.content or ""
        usage_obj = getattr(resp, "usage", None)

        usage = {}
        if usage_obj is not None:
            usage = {
                "prompt_tokens": int(getattr(usage_obj, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage_obj, "completion_tokens", 0) or 0),
                "total_tokens": int(getattr(usage_obj, "total_tokens", 0) or 0),
            }

        return LLMResult(text=text, usage=usage, latency_s=latency, raw=resp)