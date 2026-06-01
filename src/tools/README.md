Tools for Agent
================

This folder contains lightweight, deterministic tool stubs used by the Agent
and baseline chatbot for the lab. Each tool is implemented as a pure
function that accepts explicit inputs and returns serializable outputs.

Available tools
---------------
- `check_stock(product_id, inventory)` -> {"available": bool, "quantity": int}
- `get_stock_level(product_id, inventory)` -> int
- `get_price(product_id, products, currency="USD")` -> {"price": float, "currency": str}
- `get_discount(product_id, base_price, coupons=None, coupon_code=None, products=None, products_csv_path=None)` -> {"applied_coupon","discount_amount","final_price","details"}
- `calc_shipping(weight_kg, destination, method="standard")` -> {"cost","currency","estimated_days","method"}
- `calc_tax(subtotal, region)` -> {"tax","total","rate"}

Inputs are intentionally permissive (product maps may store prices or dicts)
so these tools can be used with simple fixtures or the real product data the
instructor will provide later (e.g., `coupon_code` field). If `coupon_code`
is not provided, `get_discount` tries to resolve it from `products` or from
`src/data/products.csv`.

Examples
--------
```python
from src.tools import get_price, get_discount, check_stock

products = {"p1": {"price": 19.99, "name": "Socks"}}
inventory = {"p1": 5}

print(get_price("p1", products))
print(check_stock("p1", inventory))
print(get_discount("p1", 19.99, coupons={"SUMMER": {"type":"percent","value":10}}, coupon_code="SUMMER"))
```

Replace these stubs with project-specific logic when integrating with a real
backend or dataset.
