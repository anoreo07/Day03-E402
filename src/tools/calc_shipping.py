"""Shipping cost estimation tools.

Function: `calc_shipping(weight_kg, destination, method="standard")`

Returns: {"cost": float, "currency": "USD", "estimated_days": int, "method": str}

This is a deterministic stub used for tests and agent tool examples.
"""
from typing import Dict, Any


def calc_shipping(weight_kg: float, destination: Dict[str, Any], method: str = "standard") -> Dict[str, Any]:
    """Estimate shipping cost and delivery days.

    - `weight_kg`: package weight in kilograms
    - `destination`: dict containing at least `country` and optionally `zone` or `postal_code`
    - `method`: one of "standard", "express", "overnight"

    Returned cost is a simple calculation: base + per-kg rate. Rates differ by method.
    """
    country = (destination.get("country") if isinstance(destination, dict) else None) or "UNKNOWN"
    base = 5.0
    per_kg = 2.0
    est_days = 5

    method = method.lower()
    if method == "express":
        base = 10.0
        per_kg = 3.5
        est_days = 2
    elif method == "overnight":
        base = 20.0
        per_kg = 5.0
        est_days = 1

    # simple international uplift
    if country not in ("US", "USA", "United States", "UNKNOWN"):
        base *= 1.5
        per_kg *= 1.5
        est_days += 3

    cost = base + max(0.0, float(weight_kg)) * per_kg
    return {"cost": round(cost, 2), "currency": "USD", "estimated_days": est_days, "method": method}
