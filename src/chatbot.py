import argparse
import os
import sys
from typing import Optional
 
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)
from dotenv import load_dotenv
from src.core.provider_factory import build_provider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class Chatbot:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.llm = build_provider(provider=provider, model=model)

    def ask(self, user_input: str, system_prompt: Optional[str] = None) -> str:
        result = self.llm.generate(user_input, system_prompt=system_prompt)
        tracker.track_request(
            provider=result.get("provider", "unknown"),
            model=self.llm.model_name,
            usage=result.get("usage", {}),
            latency_ms=result.get("latency_ms", 0),
        )
        logger.log_event(
            "CHATBOT_TURN",
            {"input": user_input, "output": result.get("content", "")},
        )
        return result.get("content", "")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the baseline chatbot.")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--system", default="You are a helpful shopping assistant.")
    parser.add_argument("prompt", nargs="*", help="User prompt text")
    args = parser.parse_args()

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        prompt = input("User: ")

    chatbot = Chatbot(provider=args.provider, model=args.model)
    answer = chatbot.ask(prompt, system_prompt=args.system)
    print(answer)


if __name__ == "__main__":
    main()