import argparse
import csv
import os
import sys
from typing import Dict, Any, List
 
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)
from dotenv import load_dotenv
from src.agent.agent import ReActAgent
from src.core.provider_factory import build_provider
from src.tools import check_stock, get_price, get_discount, calc_shipping, calc_tax


def load_products(path: str) -> Dict[str, Dict[str, Any]]:
    products: Dict[str, Dict[str, Any]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("product_id")
            if pid:
                products[pid] = row
    return products


def build_tools(products: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "name": "check_stock",
            "description": "check_stock(product_id, inventory) -> {available, quantity}",
            "func": lambda product_id, inventory=products: check_stock(product_id, inventory),
        },
        {
            "name": "get_price",
            "description": "get_price(product_id, products) -> {price, currency}",
            "func": lambda product_id, products=products: get_price(product_id, products),
        },
        {
            "name": "get_discount",
            "description": "get_discount(product_id, base_price, coupons=None, coupon_code=None)",
            "func": lambda product_id, base_price, coupon_code=None: get_discount(
                product_id, base_price, coupon_code=coupon_code, products=products
            ),
        },
        {
            "name": "calc_shipping",
            "description": "calc_shipping(weight_kg, destination, method='standard')",
            "func": calc_shipping,
        },
        {
            "name": "calc_tax",
            "description": "calc_tax(subtotal, region)",
            "func": calc_tax,
        },
    ]


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run ReAct agent with product tools.")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--products", default="src/data/products.csv")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("prompt", nargs="*", help="User prompt text")
    args = parser.parse_args()

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        prompt = input("User: ")

    products = load_products(args.products)
    tools = build_tools(products)
    llm = build_provider(provider=args.provider, model=args.model)
    agent = ReActAgent(llm=llm, tools=tools, max_steps=args.max_steps)
    answer = agent.run(prompt)
    print(answer)


if __name__ == "__main__":
    main()