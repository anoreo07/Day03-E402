import argparse
from typing import List

from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.core.provider_factory import build_provider_from_env
from src.tools.ecommerce_tools import get_ecommerce_tools


AGENT_TEST_CASES: List[str] = [
    "I want to buy 2 Wireless Earbuds with coupon SAVE10 and ship to Hanoi. Is it in stock and what is the total?",
    "Can I buy 3 Gaming Keyboards with coupon WINNER and ship to Ho Chi Minh? Give the final cost breakdown.",
    "Find a backpack product, then price 1 unit with tax and shipping to Da Nang.",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the e-commerce ReAct agent demo.")
    parser.add_argument(
        "--provider",
        choices=["local", "openai", "gemini"],
        default=None,
        help="Override DEFAULT_PROVIDER from .env.",
    )
    parser.add_argument("--model", default=None, help="Override provider model name.")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--quiet", action="store_true", help="Hide step-by-step output.")
    parser.add_argument("question", nargs="*", help="Optional custom question.")
    args = parser.parse_args()

    load_dotenv()
    llm = build_provider_from_env(args.provider, args.model)
    agent = ReActAgent(
        llm=llm,
        tools=get_ecommerce_tools(),
        max_steps=args.max_steps,
        verbose=not args.quiet,
    )

    questions = [" ".join(args.question)] if args.question else AGENT_TEST_CASES
    for index, question in enumerate(questions, start=1):
        print(f"\n=== Agent case {index} ===")
        print(f"User: {question}")
        answer = agent.run(question)
        print(f"Final: {answer}")


if __name__ == "__main__":
    main()
