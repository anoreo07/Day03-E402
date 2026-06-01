from functools import partial
from typing import List, Dict, Any
import csv
import os

from src.tools.check_stock import check_stock as _check_stock
from src.tools.get_price import get_price as _get_price
from src.tools.get_discount import get_discount as _get_discount
from src.tools.calc_shipping import calc_shipping as _calc_shipping
from src.tools.calc_tax import calc_tax as _calc_tax

def load_csv_data(filepath: str) -> Dict[str, Any]:
    """Helper to load product data from CSV."""
    products = {}
    if not os.path.exists(filepath):
        return products
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row['product_id']
            products[pid] = {
                'name': row['name'],
                'price': float(row['price']),
                'stock': int(row['stock']),
                'category': row['category']
            }
    return products

def get_ecommerce_tools() -> List[Dict[str, Any]]:
    """
    Returns the list of tools bound with data for the agent.
    This fulfills the requirement of bridging tools and agent.
    """
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.csv')
    products = load_csv_data(csv_path)
    
    # Extract inventory and product dicts for the underlying tools
    inventory = {pid: data['stock'] for pid, data in products.items()}
    product_prices = {pid: {"price": data['price'], "name": data['name']} for pid, data in products.items()}
    coupons = {
        "SAVE10": {"type": "percent", "value": 10},
        "MINUS5": {"type": "fixed", "value": 5}
    }

    # Bind data to tool stubs so the agent doesn't need to pass 'inventory', 'products', 'coupons'
    def bound_check_stock(product_id: str) -> Dict[str, Any]:
        return _check_stock(product_id, inventory)

    def bound_get_price(product_id: str) -> Dict[str, Any]:
        return _get_price(product_id, product_prices)

    def bound_get_discount(product_id: str, coupon_code: str) -> Dict[str, Any]:
        # get base price first
        price_info = _get_price(product_id, product_prices)
        base_price = price_info.get("price", 0.0)
        return _get_discount(product_id, base_price, coupons, coupon_code)

    def bound_calc_shipping(weight_kg: float, destination: str, method: str = "standard") -> Dict[str, Any]:
        return _calc_shipping(weight_kg, destination, method)

    def bound_calc_tax(subtotal: float, region: str) -> Dict[str, Any]:
        return _calc_tax(subtotal, region)

    return [
        {
            "name": "check_stock",
            "description": "Kiểm tra tồn kho sản phẩm. Cần truyền product_id.",
            "function": bound_check_stock
        },
        {
            "name": "get_price",
            "description": "Lấy giá gốc của sản phẩm. Cần truyền product_id.",
            "function": bound_get_price
        },
        {
            "name": "get_discount",
            "description": "Áp dụng mã giảm giá cho sản phẩm. Cần truyền product_id và coupon_code.",
            "function": bound_get_discount
        },
        {
            "name": "calc_shipping",
            "description": "Tính phí giao hàng. Cần truyền weight_kg, destination, và method.",
            "function": bound_calc_shipping
        },
        {
            "name": "calc_tax",
            "description": "Tính thuế. Cần truyền subtotal và region.",
            "function": bound_calc_tax
        }
    ]
