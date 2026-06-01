"""Tools package for e-commerce agent.

Expose small utility functions used by the Agent and baseline chatbot.
Each tool is implemented as a pure function that takes explicit inputs and
returns simple serializable outputs (dicts, numbers, booleans).
"""

import csv
import os
from typing import Any, Dict, List, Optional

from .check_stock import check_stock, get_stock_level
from .get_price import get_price
from .get_discount import get_discount
from .calc_shipping import calc_shipping
from .calc_tax import calc_tax

# Load data from the CSV file for pre-binding database arguments
_CSV_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "products.csv")
)

def _load_data() -> tuple:
    products = {}
    inventory = {}
    coupons = {}
    if not os.path.exists(_CSV_PATH):
        return products, inventory, coupons
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["product_id"].strip()
            products[pid] = {
                "name": row["name"],
                "category": row["category"],
                "price": float(row["price_usd"]),
                "price_usd": float(row["price_usd"]),
                "stock": int(row["stock_qty"]),
                "stock_qty": int(row["stock_qty"]),
                "tax_rate": float(row["tax_rate"]),
                "shipping_weight_kg": float(row["shipping_weight_kg"]),
                "coupon_code": row["coupon_code"].strip(),
            }
            inventory[pid] = int(row["stock_qty"])
            code = row["coupon_code"].strip()
            digits = "".join(c for c in code if c.isdigit())
            if digits:
                coupons[code] = {"type": "percent", "value": float(digits)}
    return products, inventory, coupons

PRODUCTS, INVENTORY, COUPONS = _load_data()

# Wrappers to simplify LLM tool calling (binding the database/context arguments)
def check_stock_tool(product_id: str) -> Dict[str, Any]:
    """Check stock availability and quantity for a product ID."""
    return check_stock(product_id, INVENTORY)

def get_price_tool(product_id: str) -> Dict[str, Any]:
    """Get the base price for a product ID."""
    return get_price(product_id, PRODUCTS)

def get_discount_tool(product_id: str, base_price: float, coupon_code: Optional[str] = None) -> Dict[str, Any]:
    """Get discount details for a product ID and base price. If coupon_code is not provided, resolves it from product data."""
    return get_discount(
        product_id=product_id,
        base_price=base_price,
        coupons=COUPONS,
        coupon_code=coupon_code,
        products=PRODUCTS
    )

def search_products(query: str) -> List[Dict[str, Any]]:
    """Search for products by name or category keyword. Useful for finding the product ID of an item."""
    query_lower = query.lower()
    results = []
    for pid, p in PRODUCTS.items():
        if (query_lower in pid.lower() or 
            query_lower in p["name"].lower() or 
            query_lower in p["category"].lower()):
            results.append({
                "product_id": pid,
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "shipping_weight_kg": p["shipping_weight_kg"]
            })
    return results

def get_ecommerce_tools() -> List[Dict[str, Any]]:
    """Return a list of tool definitions for the ReAct Agent."""
    return [
        {
            "name": "check_stock",
            "description": "Check if a product is in stock and get its available quantity.",
            "function": check_stock_tool
        },
        {
            "name": "get_price",
            "description": "Get the base price of a product.",
            "function": get_price_tool
        },
        {
            "name": "get_discount",
            "description": "Get the discount details (final price and discount amount) for a product and its base price using a coupon code.",
            "function": get_discount_tool
        },
        {
            "name": "calc_shipping",
            "description": "Calculate shipping cost and estimated days. Needs weight_kg, destination (dict e.g. {'country': 'US'}), and optional method ('standard', 'express', 'overnight').",
            "function": calc_shipping
        },
        {
            "name": "calc_tax",
            "description": "Calculate tax and total price for a subtotal amount in a region (e.g. 'US', 'NY', 'CA', 'TX', 'EU').",
            "function": calc_tax
        },
        {
            "name": "search_products",
            "description": "Search for products by name or category keyword to get their product ID and weight.",
            "function": search_products
        }
    ]

__all__ = [
    "check_stock",
    "get_stock_level",
    "get_price",
    "get_discount",
    "calc_shipping",
    "calc_tax",
    "get_ecommerce_tools",
    "search_products",
]
