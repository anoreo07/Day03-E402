import time
import json
from typing import Dict, Any, Optional, Generator, List
import requests
from src.core.llm_provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, model_name: str = "gemma3:4b", base_url: str = "http://localhost:11434"):
        super().__init__(model_name=model_name, api_key=None)
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model_name, "messages": messages, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        content = data.get("message", {}).get("content", "")
        usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "ollama",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        with requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model_name, "messages": messages, "stream": True},
            stream=True,
            timeout=120,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                chunk = line.decode("utf-8")
                data = json.loads(chunk)
                token = data.get("message", {}).get("content")
                if token:
                    yield token