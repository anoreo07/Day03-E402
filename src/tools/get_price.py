"""Pricing tools.

Provides `get_price(product_id, products, currency="USD")` which returns the
base price for a product. `products` may be a mapping from product_id to
either a numeric price or a dict containing a `price` field.

The function returns a dict: {"price": float, "currency": str}
"""
from typing import Any, Dict


def get_price(product_id: str, products: Dict[str, Any], currency: str = "USD") -> Dict[str, Any]:
    """Return base price for a product.

    - `products` can be {id: price} or {id: {"price": x}}.
    - If product is missing, a `price` of 0.0 is returned.
    """
    if product_id not in products:
        return {"price": 0.0, "currency": currency}
    val = products[product_id]
    if isinstance(val, (int, float)):
        price = float(val)
    elif isinstance(val, dict):
        if "price" in val:
            price = float(val.get("price", 0.0))
        else:
            price = float(val.get("price_usd", 0.0))
    else:
        price = 0.0
    return {"price": price, "currency": currency}
