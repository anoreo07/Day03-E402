"""Inventory-related tools.

Functions:
- `check_stock(product_id, inventory)` -> dict: whether item is in stock and quantity
- `get_stock_level(product_id, inventory)` -> int: quantity (0 if missing)

`inventory` is expected to be a mapping from product_id to integer quantity,
or a mapping to product dicts that contain a numeric `stock` or `quantity` field.
Implementations are defensive and accept both shapes.

Examples
--------
>>> inventory = {"p1": 3}
>>> check_stock("p1", inventory)
{"available": True, "quantity": 3}

>>> inventory = {"p2": {"stock": 0}}
>>> get_stock_level("p2", inventory)
0
"""
from typing import Any, Dict


def get_stock_level(product_id: str, inventory: Dict[str, Any]) -> int:
    """Return integer stock level for `product_id` from `inventory`.

    inventory may be {product_id: quantity} or {product_id: {"stock": n}}.
    Missing items return 0.
    """
    if product_id not in inventory:
        return 0
    val = inventory[product_id]
    if isinstance(val, int):
        return max(0, val)
    if isinstance(val, dict):
        for k in ("stock", "quantity", "qty", "stock_qty"):
            if k in val and isinstance(val[k], int):
                return max(0, val[k])
    return 0


def check_stock(product_id: str, inventory: Dict[str, Any]) -> Dict[str, Any]:
    """Check availability for `product_id`.

    Returns a serializable dict: {"available": bool, "quantity": int}.
    """
    qty = get_stock_level(product_id, inventory)
    return {"available": qty > 0, "quantity": qty}
