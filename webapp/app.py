import os
import sys
from flask import Flask, render_template, jsonify, request

# Ensure project root is importable so `from src...` works when running this script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.data import load_products, load_coupons
from decimal import Decimal, ROUND_HALF_UP

app = Flask(__name__, template_folder='templates', static_folder='static')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/products')
def api_products():
    products = load_products()
    return jsonify(products)


@app.route('/api/coupons')
def api_coupons():
    coupons = load_coupons()
    return jsonify(coupons)


def _round(n):
    return float(Decimal(n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


@app.route('/api/price', methods=['POST'])
def api_price():
    data = request.json or {}
    cart = data.get('cart', [])  # list of {product_id, qty}
    coupon_code = data.get('coupon_code')

    products = {p['product_id']: p for p in load_products()}
    coupons = {c['coupon_code']: c for c in load_coupons()}

    subtotal = 0.0
    items = []
    for entry in cart:
        pid = entry.get('product_id')
        qty = int(entry.get('qty', 1))
        p = products.get(pid)
        if not p:
            continue
        line = p['price_usd'] * qty
        subtotal += line
        items.append({'product_id': pid, 'name': p['name'], 'qty': qty, 'unit_price': p['price_usd'], 'line_total': _round(line)})

    shipping = 4.99 if subtotal < 50 else 0.0
    tax = subtotal * 0.08
    discount = 0.0

    applied_coupon = None
    if coupon_code:
        c = coupons.get(coupon_code)
        if c:
            # simple validation
            if subtotal >= c.get('coupon_min_order_usd', 0):
                if c.get('coupon_free_shipping'):
                    shipping = 0.0
                discount = subtotal * (float(c.get('coupon_discount_pct', 0)) / 100.0)
                applied_coupon = c

    total = subtotal + shipping + tax - discount
    response = {
        'items': items,
        'subtotal': _round(subtotal),
        'shipping': _round(shipping),
        'tax': _round(tax),
        'discount': _round(discount),
        'total': _round(total),
        'applied_coupon': applied_coupon
    }
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
