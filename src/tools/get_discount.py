"""Discount calculation tools.

Function: `get_discount(product_id, base_price, coupons=None, coupon_code=None, products=None, products_csv_path=None)`

`coupons` is an optional mapping of coupon_code -> {"type": "percent"|"fixed", "value": number, "min_total": optional}

If `coupon_code` is not provided, the function tries to read it from `products`
or from the default `src/data/products.csv`.

Returns a dict with keys:
- `applied_coupon`: coupon code or None
- `discount_amount`: numeric amount subtracted from base_price
- `final_price`: base_price - discount_amount (not below 0)
- `details`: explanatory text
"""
import csv
import os
from typing import Any, Dict, Optional


_DEFAULT_PRODUCTS_CSV = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "products.csv")
)


def _load_products_csv(path: str) -> Dict[str, Dict[str, Any]]:
    products: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(path):
        return products
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("product_id")
            if pid:
                products[pid] = row
    return products


def _resolve_coupon_code(product_id: str, products: Optional[Dict[str, Any]], products_csv_path: Optional[str]) -> Optional[str]:
    if products and product_id in products:
        val = products[product_id]
        if isinstance(val, dict):
            code = val.get("coupon_code") or val.get("coupon")
            if code:
                return str(code)
    csv_path = products_csv_path or _DEFAULT_PRODUCTS_CSV
    csv_products = _load_products_csv(csv_path)
    if product_id in csv_products:
        return csv_products[product_id].get("coupon_code")
    return None


def get_discount(
    product_id: str,
    base_price: float,
    coupons: Optional[Dict[str, Any]] = None,
    coupon_code: Optional[str] = None,
    products: Optional[Dict[str, Any]] = None,
    products_csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute discount for a single product price.

    This is a small, deterministic stub suitable for offline testing.
    If `coupon_code` is provided and `coupons` contains a rule, apply it.
    Supported coupon types: "percent" (value as 0-100) and "fixed" (absolute amount).
    """
    applied = None
    discount = 0.0
    details = []

    if not coupon_code:
        coupon_code = _resolve_coupon_code(product_id, products, products_csv_path)

    if coupon_code and coupons and coupon_code in coupons:
        rule = coupons[coupon_code]
        ctype = rule.get("type")
        val = float(rule.get("value", 0))
        if ctype == "percent":
            discount = base_price * (val / 100.0)
            details.append(f"{val}% off")
        elif ctype == "fixed":
            discount = val
            details.append(f"{val} off")
        else:
            details.append("unknown coupon type")
        applied = coupon_code
    elif coupon_code:
        # Fallback: interpret trailing digits as percent (e.g., SUMMER10 -> 10%)
        digits = "".join([c for c in str(coupon_code) if c.isdigit()])
        if digits:
            val = float(digits)
            discount = base_price * (val / 100.0)
            details.append(f"{val}% off (derived)")
            applied = coupon_code

    # ensure we don't go below zero
    final = max(0.0, float(base_price) - float(discount))
    return {
        "applied_coupon": applied,
        "discount_amount": round(float(discount), 2),
        "final_price": round(final, 2),
        "details": ", ".join(details) if details else "no discount",
    }
