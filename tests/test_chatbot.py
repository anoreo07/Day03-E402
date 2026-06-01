from typing import Dict, Any, Optional, Generator
from src.chatbot import Chatbot
from src.core.llm_provider import LLMProvider


class DummyProvider(LLMProvider):
    def __init__(self, content: str):
        super().__init__(model_name="dummy")
        self.content = content

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        return {
            "content": self.content,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "latency_ms": 1,
            "provider": "dummy",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.content


def test_chatbot_returns_response(monkeypatch):
    dummy = DummyProvider("ok")
    monkeypatch.setattr("src.chatbot.build_provider", lambda provider=None, model=None: dummy)
    bot = Chatbot(provider="dummy")
    assert bot.ask("hello") == "ok"