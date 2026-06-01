"""Tax calculation tools.

Function: `calc_tax(subtotal, region)`

Returns: {"tax": float, "total": float, "rate": float}

This is a minimal deterministic implementation for testing. Real tax logic
depends on many factors and should be replaced with a proper tax service.
"""
from typing import Dict, Any

# Example simplified tax rates by region code.
_RATES = {
    "CA": 0.13,  # Canada (example HST)
    "US": 0.07,  # default US combined rate
    "NY": 0.08875,
    "TX": 0.0625,
    "EU": 0.20,
}


def calc_tax(subtotal: float, region: Any) -> Dict[str, Any]:
    """Calculate tax for `subtotal` given a `region` key.

    `region` may be a string code ("US", "CA", "NY") or a mapping with a `region`/`state` key.
    """
    if isinstance(region, dict):
        code = region.get("region") or region.get("state") or region.get("country")
    else:
        code = region

    code = (code or "US").upper()
    rate = _RATES.get(code, _RATES.get("US", 0.0))
    tax = round(float(subtotal) * float(rate), 2)
    total = round(float(subtotal) + tax, 2)
    return {"tax": tax, "total": total, "rate": rate}
