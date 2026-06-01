"""E-commerce tool registry for the ReAct Agent.

This module loads product data from ``src/data/products.csv`` once and
exposes each tool as a dict understood by :class:`ReActAgent`:

    {"name": str, "description": str, "function": callable, "args_schema": dict}

The heavy data arguments (``inventory``, ``products``, ``coupons``) are
pre-bound via :func:`functools.partial` so the agent only sees the
user-facing parameters (e.g. ``product_id``).

Usage::

    from src.tools.ecommerce_tools import get_ecommerce_tools
    tools = get_ecommerce_tools()
"""

import csv
import os
from functools import partial
from typing import Any, Dict, List, Optional

# ── Internal tool imports ──────────────────────────────────────────────────────
from src.tools.check_stock import check_stock as _check_stock
from src.tools.get_price import get_price as _get_price
from src.tools.get_discount import get_discount as _get_discount
from src.tools.calc_shipping import calc_shipping as _calc_shipping
from src.tools.calc_tax import calc_tax as _calc_tax


# ── Data loaders ───────────────────────────────────────────────────────────────
_CSV_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "products.csv")
)


def _load_products(path: str = _CSV_PATH) -> Dict[str, Dict[str, Any]]:
    """Load products from CSV and normalise numeric fields."""
    products: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(path):
        return products
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
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
    return products


def _build_inventory(products: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    return {pid: p["stock"] for pid, p in products.items()}


def _build_coupons(products: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Derive coupon rules from product data (trailing digits → percent)."""
    coupons: Dict[str, Dict[str, Any]] = {}
    for p in products.values():
        code = p.get("coupon_code", "")
        digits = "".join(c for c in code if c.isdigit())
        if digits:
            coupons[code] = {"type": "percent", "value": float(digits)}
    return coupons


# ── Agent-facing wrapper functions ─────────────────────────────────────────────
# These are thin wrappers so the agent sees clean, minimal signatures.

def _agent_check_stock(product_id: str, *, _inventory: Dict[str, int]) -> Dict[str, Any]:
    """Check whether a product is in stock.

    Args:
        product_id: Product ID, e.g. "P001".
    Returns:
        {"available": bool, "quantity": int}
    """
    return _check_stock(product_id, _inventory)


def _agent_get_price(product_id: str, *, _products: Dict[str, Any]) -> Dict[str, Any]:
    """Get the base price of a product in USD.

    Args:
        product_id: Product ID, e.g. "P001".
    Returns:
        {"price": float, "currency": "USD"}
    """
    return _get_price(product_id, _products)


def _agent_get_discount(
    product_id: str,
    coupon_code: str = "",
    *,
    _products: Dict[str, Any],
    _coupons: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply a coupon/discount to a product.

    Args:
        product_id: Product ID, e.g. "P001".
        coupon_code: Coupon code string, e.g. "SUMMER10". Leave empty to auto-detect.
    Returns:
        {"applied_coupon", "discount_amount", "final_price", "details"}
    """
    base = _products.get(product_id, {}).get("price", 0.0)
    return _get_discount(
        product_id,
        base,
        coupons=_coupons,
        coupon_code=coupon_code or None,
        products=_products,
    )


def _agent_calc_shipping(
    weight_kg: float, destination: str, method: str = "standard"
) -> Dict[str, Any]:
    """Estimate shipping cost.

    Args:
        weight_kg: Total package weight in kg.
        destination: Country or city name, e.g. "US", "Hanoi".
        method: "standard", "express", or "overnight".
    Returns:
        {"cost": float, "currency": "USD", "estimated_days": int, "method": str}
    """
    dest_map = {"country": destination}
    return _calc_shipping(float(weight_kg), dest_map, method)


def _agent_calc_tax(subtotal: float, region: str) -> Dict[str, Any]:
    """Calculate tax for a given subtotal.

    Args:
        subtotal: Pre-tax amount in USD.
        region: Region code, e.g. "US", "CA", "NY", "TX", "EU".
    Returns:
        {"tax": float, "total": float, "rate": float}
    """
    return _calc_tax(float(subtotal), region)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_ecommerce_tools(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a list of tool dicts ready for :class:`ReActAgent`.

    Each dict has keys: ``name``, ``description``, ``function``, ``args_schema``.
    Data from ``products.csv`` is pre-loaded and bound into each function.
    """
    products = _load_products(csv_path or _CSV_PATH)
    inventory = _build_inventory(products)
    coupons = _build_coupons(products)

    return [
        {
            "name": "check_stock",
            "description": (
                "Check whether a product is in stock. "
                "Returns {available: bool, quantity: int}."
            ),
            "function": partial(_agent_check_stock, _inventory=inventory),
            "args_schema": {"product_id": "str — Product ID e.g. 'P001'"},
        },
        {
            "name": "get_price",
            "description": (
                "Get the base price of a product in USD. "
                "Returns {price: float, currency: str}."
            ),
            "function": partial(_agent_get_price, _products=products),
            "args_schema": {"product_id": "str — Product ID e.g. 'P001'"},
        },
        {
            "name": "get_discount",
            "description": (
                "Apply a coupon or discount code to a product. "
                "Returns {applied_coupon, discount_amount, final_price, details}. "
                "If coupon_code is empty, auto-detects from product data."
            ),
            "function": partial(_agent_get_discount, _products=products, _coupons=coupons),
            "args_schema": {
                "product_id": "str — Product ID e.g. 'P001'",
                "coupon_code": "str — Coupon code e.g. 'SUMMER10' (optional)",
            },
        },
        {
            "name": "calc_shipping",
            "description": (
                "Estimate shipping cost based on weight, destination, and method. "
                "Returns {cost: float, currency: str, estimated_days: int, method: str}."
            ),
            "function": _agent_calc_shipping,
            "args_schema": {
                "weight_kg": "float — Package weight in kg",
                "destination": "str — Country or city name e.g. 'US', 'Hanoi'",
                "method": "str — 'standard', 'express', or 'overnight' (default: standard)",
            },
        },
        {
            "name": "calc_tax",
            "description": (
                "Calculate tax for a subtotal amount. "
                "Returns {tax: float, total: float, rate: float}."
            ),
            "function": _agent_calc_tax,
            "args_schema": {
                "subtotal": "float — Pre-tax amount in USD",
                "region": "str — Region code: 'US', 'CA', 'NY', 'TX', 'EU'",
            },
        },
    ]
