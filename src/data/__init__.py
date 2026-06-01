from pathlib import Path
import csv
from typing import List, Dict, Any

DATA_DIR = Path(__file__).resolve().parent
PRODUCTS_CSV = DATA_DIR / 'products.csv'


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {'true', '1', 'yes'}


def _parse_optional_list(value: str) -> List[str]:
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() == 'all':
        return ['All']
    return [item.strip() for item in cleaned.split('|') if item.strip()]


def load_products() -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    with PRODUCTS_CSV.open(newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # convert types safely
            row['price_usd'] = float(row.get('price_usd') or 0)
            row['stock_qty'] = int(row.get('stock_qty') or 0)
            row['tax_rate'] = float(row.get('tax_rate') or 0)
            row['shipping_weight_kg'] = float(row.get('shipping_weight_kg') or 0)
            # coupon fields if present
            row['coupon_code'] = row.get('coupon_code')
            row['coupon_discount_pct'] = float(row.get('coupon_discount_pct') or 0)
            row['coupon_min_order_usd'] = float(row.get('coupon_min_order_usd') or 0)
            row['coupon_free_shipping'] = _parse_bool(row.get('coupon_free_shipping', 'False'))
            row['coupon_applicable_categories'] = _parse_optional_list(row.get('coupon_applicable_categories', 'All'))
            row['coupon_expires_at'] = row.get('coupon_expires_at', '')
            products.append(row)
    return products


def load_coupons() -> List[Dict[str, Any]]:
    coupons: List[Dict[str, Any]] = []
    for p in load_products():
        if not p.get('coupon_code'):
            continue
        coupons.append({
            'product_id': p['product_id'],
            'coupon_code': p['coupon_code'],
            'coupon_discount_pct': p['coupon_discount_pct'],
            'coupon_min_order_usd': p['coupon_min_order_usd'],
            'coupon_free_shipping': p['coupon_free_shipping'],
            'coupon_applicable_categories': p['coupon_applicable_categories'],
            'coupon_expires_at': p.get('coupon_expires_at', ''),
        })
    return coupons
