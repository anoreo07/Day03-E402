"""
tests/test_tools.py – Unit tests cho 5 tools (Thành viên C)
============================================================
Kiểm tra từng tool theo đúng signatures của src/tools/:
  - check_stock(product_id, inventory)
  - get_stock_level(product_id, inventory)
  - get_price(product_id, products, currency)
  - get_discount(product_id, base_price, coupons, coupon_code, products, ...)
  - calc_shipping(weight_kg, destination, method)
  - calc_tax(subtotal, region)

Chạy:
    pytest tests/test_tools.py -v
    python tests/test_tools.py
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.check_stock import check_stock, get_stock_level
from src.tools.get_price import get_price
from src.tools.get_discount import get_discount
from src.tools.calc_shipping import calc_shipping
from src.tools.calc_tax import calc_tax

# ─── Fixtures từ products.csv ─────────────────────────────────────────────────
_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "data", "products.csv")


def _load_fixtures():
    products, inventory, coupons = {}, {}, {}
    if not os.path.exists(_CSV_PATH):
        return products, inventory, coupons
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["product_id"].strip()
            products[pid] = {
                "name": row["name"],
                "price": float(row["price_usd"]),
                "price_usd": float(row["price_usd"]),
                "stock": int(row["stock_qty"]),
                "stock_qty": int(row["stock_qty"]),
                "tax_rate": float(row["tax_rate"]),
                "shipping_weight_kg": float(row["shipping_weight_kg"]),
                "coupon_code": row["coupon_code"].strip(),
            }
            inventory[pid] = int(row["stock_qty"])
            code = row["coupon_code"].strip()
            digits = "".join(c for c in code if c.isdigit())
            if digits:
                coupons[code] = {"type": "percent", "value": float(digits)}
    return products, inventory, coupons


PRODUCTS, INVENTORY, COUPONS = _load_fixtures()


# ══════════════════════════════════════════════════════════════════════════════
# TC-01 ~ TC-04 : check_stock / get_stock_level
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckStock:

    def test_TC01_in_stock_returns_available_true(self):
        """TC-01: Sản phẩm còn hàng → available=True và qty chính xác."""
        result = check_stock("P001", INVENTORY)
        assert result["available"] is True
        assert result["quantity"] == 120

    def test_TC01b_zero_stock_returns_available_false(self):
        """TC-01b: Inventory 0 → available=False."""
        inv = {"P001": 0}
        result = check_stock("P001", inv)
        assert result["available"] is False
        assert result["quantity"] == 0

    def test_TC01c_missing_product_returns_false(self):
        """TC-01c: product_id không có trong inventory → available=False."""
        result = check_stock("P999", INVENTORY)
        assert result["available"] is False
        assert result["quantity"] == 0

    def test_TC01d_get_stock_level(self):
        """TC-01d: get_stock_level trả đúng số nguyên."""
        assert get_stock_level("P007", INVENTORY) == 45
        assert get_stock_level("P001", INVENTORY) == 120
        assert get_stock_level("P999", INVENTORY) == 0

    def test_TC01e_dict_stock_shape(self):
        """TC-01e: Inventory dạng dict-of-dict cũng hoạt động."""
        inv = {"P001": {"stock_qty": 50}}
        result = check_stock("P001", inv)
        assert result["available"] is True
        assert result["quantity"] == 50


# ══════════════════════════════════════════════════════════════════════════════
# TC-02 : get_price
# ══════════════════════════════════════════════════════════════════════════════

class TestGetPrice:

    def test_TC02_correct_price_from_products(self):
        """TC-02: Giá trả về khớp với CSV."""
        result = get_price("P001", PRODUCTS)
        assert result["price"] == 49.99
        assert result["currency"] == "USD"

    def test_TC02b_headphones_price(self):
        """TC-02b: Sản phẩm P007 giá $129.90."""
        result = get_price("P007", PRODUCTS)
        assert result["price"] == 129.90

    def test_TC02c_missing_product_returns_zero(self):
        """TC-02c: product_id không tồn tại → price = 0.0."""
        result = get_price("P999", PRODUCTS)
        assert result["price"] == 0.0

    def test_TC02d_simple_dict_price(self):
        """TC-02d: products dạng {id: price_number} cũng hoạt động."""
        result = get_price("A1", {"A1": 99.99})
        assert result["price"] == 99.99

    def test_TC02e_currency_param(self):
        """TC-02e: Tham số currency được truyền đúng."""
        result = get_price("P001", PRODUCTS, currency="EUR")
        assert result["currency"] == "EUR"


# ══════════════════════════════════════════════════════════════════════════════
# TC-03 : get_discount
# ══════════════════════════════════════════════════════════════════════════════

class TestGetDiscount:

    def test_TC03_percent_coupon_applied(self):
        """TC-03: HEAD20 → giảm 20% từ $129.90 = final $103.92."""
        result = get_discount("P007", 129.90, coupons=COUPONS, coupon_code="HEAD20")
        assert result["applied_coupon"] == "HEAD20"
        assert result["discount_amount"] == 25.98
        assert result["final_price"] == 103.92

    def test_TC03b_summer10_coupon(self):
        """TC-03b: SUMMER10 → giảm 10% từ $49.99."""
        result = get_discount("P001", 49.99, coupons=COUPONS, coupon_code="SUMMER10")
        assert result["applied_coupon"] == "SUMMER10"
        assert round(result["discount_amount"], 2) == 5.00
        assert round(result["final_price"], 2) == 44.99

    def test_TC03c_no_coupon_code_no_discount(self):
        """TC-03c: Không có coupon_code, coupons rỗng, csv_path không tồn tại → no discount."""
        result = get_discount(
            "P001", 49.99,
            coupons={}, coupon_code=None,
            products=None,
            products_csv_path="/nonexistent/path.csv",  # chặn fallback CSV
        )
        assert result["discount_amount"] == 0.0
        assert result["final_price"] == 49.99
        assert result["applied_coupon"] is None

    def test_TC03d_auto_resolve_from_products(self):
        """TC-03d: Không truyền coupon_code → tự lấy từ products dict."""
        result = get_discount("P007", 129.90, coupons=COUPONS, products=PRODUCTS)
        # Sẽ tự resolve HEAD20
        assert result["applied_coupon"] == "HEAD20"

    def test_TC03e_fallback_digit_parsing(self):
        """TC-03e: Coupon không có trong coupons dict → fallback digit parsing."""
        result = get_discount("P001", 100.0, coupons={}, coupon_code="MYSTERY15")
        # fallback: 15% off
        assert result["discount_amount"] == 15.0
        assert result["final_price"] == 85.0

    def test_TC03f_final_price_not_below_zero(self):
        """TC-03f: Discount lớn hơn base_price → final_price = 0."""
        result = get_discount("P001", 10.0, coupons={"BIG90": {"type": "percent", "value": 200}}, coupon_code="BIG90")
        assert result["final_price"] >= 0.0


# ══════════════════════════════════════════════════════════════════════════════
# TC-04 : calc_shipping
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcShipping:

    def test_TC04_standard_domestic(self):
        """TC-04: Standard ship trong US, 0.5 kg."""
        result = calc_shipping(0.5, {"country": "US"}, "standard")
        # base=5, per_kg=2 → 5 + 0.5*2 = 6.0
        assert result["cost"] == 6.0
        assert result["currency"] == "USD"
        assert result["estimated_days"] == 5
        assert result["method"] == "standard"

    def test_TC04b_express_method(self):
        """TC-04b: Express nhanh hơn, phí cao hơn."""
        result = calc_shipping(1.0, {"country": "US"}, "express")
        # base=10, per_kg=3.5 → 10 + 1.0*3.5 = 13.5
        assert result["cost"] == 13.5
        assert result["estimated_days"] == 2

    def test_TC04c_overnight_method(self):
        """TC-04c: Overnight - hỏa tốc."""
        result = calc_shipping(0.3, {"country": "US"}, "overnight")
        # base=20, per_kg=5 → 20 + 0.3*5 = 21.5
        assert result["cost"] == 21.5
        assert result["estimated_days"] == 1

    def test_TC04d_international_uplift(self):
        """TC-04d: Quốc tế → phí tăng 1.5x."""
        result_us = calc_shipping(1.0, {"country": "US"})
        result_int = calc_shipping(1.0, {"country": "VN"})
        assert result_int["cost"] > result_us["cost"]
        assert result_int["estimated_days"] > result_us["estimated_days"]

    def test_TC04e_zero_weight(self):
        """TC-04e: Trọng lượng 0 → chỉ còn base fee."""
        result = calc_shipping(0.0, {"country": "US"}, "standard")
        assert result["cost"] == 5.0

    def test_TC04f_product_weight_from_csv(self):
        """TC-04f: P001 (0.05 kg) × 1 = standard ship $5.10."""
        w = PRODUCTS["P001"]["shipping_weight_kg"]  # 0.05
        result = calc_shipping(w, {"country": "US"}, "standard")
        assert result["cost"] == round(5.0 + 0.05 * 2.0, 2)  # 5.10


# ══════════════════════════════════════════════════════════════════════════════
# TC-05 : calc_tax
# ══════════════════════════════════════════════════════════════════════════════

class TestCalcTax:

    def test_TC05_us_default_rate(self):
        """TC-05: Mặc định US → rate=7%, tax và total chính xác."""
        result = calc_tax(100.0, "US")
        assert result["rate"] == 0.07
        assert result["tax"] == 7.0
        assert result["total"] == 107.0

    def test_TC05b_ny_rate(self):
        """TC-05b: New York rate = 8.875%."""
        result = calc_tax(100.0, "NY")
        assert result["rate"] == 0.08875
        assert result["tax"] == 8.88  # round(100*0.08875, 2)

    def test_TC05c_ca_rate(self):
        """TC-05c: Canada rate = 13%."""
        result = calc_tax(200.0, "CA")
        assert result["rate"] == 0.13
        assert result["tax"] == 26.0
        assert result["total"] == 226.0

    def test_TC05d_region_as_dict(self):
        """TC-05d: region truyền dạng dict cũng hoạt động."""
        result = calc_tax(100.0, {"country": "US"})
        assert result["rate"] == 0.07

    def test_TC05e_eu_rate(self):
        """TC-05e: EU rate = 20%."""
        result = calc_tax(50.0, "EU")
        assert result["rate"] == 0.20
        assert result["total"] == 60.0

    def test_TC05f_zero_subtotal(self):
        """TC-05f: subtotal = 0 → tax = 0."""
        result = calc_tax(0.0, "US")
        assert result["tax"] == 0.0
        assert result["total"] == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Runner độc lập
# ══════════════════════════════════════════════════════════════════════════════

def _run_all():
    classes = [TestCheckStock, TestGetPrice, TestGetDiscount, TestCalcShipping, TestCalcTax]
    total = passed = failed = 0
    failures = []

    for cls in classes:
        inst = cls()
        methods = sorted(m for m in dir(inst) if m.startswith("test_"))
        print(f"\n{'─'*55}")
        print(f"  {cls.__name__}")
        print(f"{'─'*55}")
        for m in methods:
            total += 1
            try:
                getattr(inst, m)()
                doc = getattr(getattr(inst, m), "__doc__", "") or ""
                print(f"  ✅ PASS  {m:<45} {doc.strip().split(chr(10))[0]}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌ FAIL  {m}")
                failures.append(f"{cls.__name__}::{m} → AssertionError: {e}")
                failed += 1
            except Exception as e:
                print(f"  💥 ERROR {m}: {e}")
                failures.append(f"{cls.__name__}::{m} → {type(e).__name__}: {e}")
                failed += 1

    print(f"\n{'═'*55}")
    print(f"  KẾT QUẢ: {passed}/{total} PASS  |  {failed} FAIL")
    print(f"{'═'*55}")
    if failures:
        print("\nChi tiết lỗi:")
        for f in failures:
            print(f"  • {f}")
    return failed == 0


if __name__ == "__main__":
    success = _run_all()
    sys.exit(0 if success else 1)
