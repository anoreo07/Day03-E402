from typing import Dict, Any, Optional, Generator, List
from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider


class DummyProvider(LLMProvider):
    def __init__(self, responses: List[str]):
        super().__init__(model_name="dummy")
        self.responses = responses
        self.index = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        content = self.responses[self.index]
        self.index += 1
        return {
            "content": content,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "latency_ms": 1,
            "provider": "dummy",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        yield self.generate(prompt, system_prompt)["content"]


def test_react_agent_runs_tool_and_finishes():
    responses = [
        "Thought: use tool\nAction: echo({\"text\": \"hello\"})",
        "Thought: done\nFinal Answer: hello",
    ]
    provider = DummyProvider(responses)
    tools = [
        {"name": "echo", "description": "echo(text)", "func": lambda text: text},
    ]
    agent = ReActAgent(llm=provider, tools=tools, max_steps=3)
    answer = agent.run("Say hello")
    assert answer == "hello"