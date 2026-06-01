"""
tests/test_tools.py – Unit Tests cho 5 Tools (Thành viên B)
============================================================
Thành viên C – Test Suite

Chạy:
    pytest tests/test_tools.py -v
    python tests/test_tools.py       (chạy không cần pytest)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.check_stock import check_stock
from src.tools.get_price import get_price
from src.tools.get_discount import get_discount
from src.tools.calc_shipping import calc_shipping
from src.tools.calc_tax import calc_tax


# ══════════════════════════════════════════════════════════
# TEST: check_stock
# ══════════════════════════════════════════════════════════

class TestCheckStock:

    def test_valid_product_has_stock(self):
        result = check_stock("P001")
        assert "P001" in result
        assert "Wireless Earbuds" in result
        assert "120" in result
        assert "CÒN HÀNG" in result

    def test_valid_product_low_stock(self):
        # P007 stock=45 → SẮP HẾT HÀNG
        result = check_stock("P007")
        assert "P007" in result
        assert "SẮP HẾT HÀNG" in result or "45" in result

    def test_case_insensitive(self):
        result_upper = check_stock("P001")
        result_lower = check_stock("p001")
        assert result_upper == result_lower

    def test_invalid_product(self):
        result = check_stock("P999")
        assert "Không tìm thấy" in result
        assert "P999" in result

    def test_whitespace_stripped(self):
        result = check_stock("  P001  ")
        assert "Wireless Earbuds" in result


# ══════════════════════════════════════════════════════════
# TEST: get_price
# ══════════════════════════════════════════════════════════

class TestGetPrice:

    def test_valid_price(self):
        result = get_price("P001")
        assert "$49.99" in result
        assert "Wireless Earbuds" in result

    def test_headphones_price(self):
        result = get_price("P007")
        assert "$129.90" in result

    def test_invalid_product(self):
        result = get_price("P000")
        assert "Không tìm thấy" in result

    def test_case_insensitive(self):
        assert get_price("p003") == get_price("P003")


# ══════════════════════════════════════════════════════════
# TEST: get_discount
# ══════════════════════════════════════════════════════════

class TestGetDiscount:

    def test_valid_coupon(self):
        # P007 + HEAD20 → 20% off $129.90 = $103.92
        result = get_discount("P007,HEAD20")
        assert "103.92" in result
        assert "20%" in result
        assert "25.98" in result

    def test_wrong_product_coupon(self):
        # HEAD20 không áp dụng cho P001
        result = get_discount("P001,HEAD20")
        assert "không áp dụng" in result
        assert "SUMMER10" in result  # gợi ý mã đúng

    def test_nonexistent_coupon(self):
        result = get_discount("P001,FAKE99")
        assert "không tồn tại" in result

    def test_invalid_format(self):
        result = get_discount("P001")
        assert "Định dạng" in result or "không hợp lệ" in result

    def test_case_insensitive_coupon(self):
        result_upper = get_discount("P007,HEAD20")
        result_lower = get_discount("P007,head20")
        # Cả hai đều phải tính đúng
        assert "103.92" in result_upper
        assert "103.92" in result_lower

    def test_five_percent_coupon(self):
        # P001 + SUMMER10 → 10% off $49.99 = $44.99
        result = get_discount("P001,SUMMER10")
        assert "44.99" in result
        assert "10%" in result


# ══════════════════════════════════════════════════════════
# TEST: calc_shipping
# ══════════════════════════════════════════════════════════

class TestCalcShipping:

    def test_single_unit_earbuds(self):
        # P001: 0.05 kg → fee = 2.00 + 0.05*4.50 = 2.225 → min $2.50
        result = calc_shipping("P001")
        assert "$2.50" in result
        assert "0.05" in result

    def test_multi_unit_backpack(self):
        # P004: 0.75 kg × 2 = 1.5 kg → 2.00 + 1.5*4.50 = 8.75
        result = calc_shipping("P004,2")
        assert "$8.75" in result
        assert "1.50" in result

    def test_single_unit_knife_set(self):
        # P014: 1.50 kg → 2.00 + 1.50*4.50 = 8.75
        result = calc_shipping("P014")
        assert "$8.75" in result

    def test_invalid_product(self):
        result = calc_shipping("P999,1")
        assert "Không tìm thấy" in result

    def test_default_quantity_one(self):
        result_explicit = calc_shipping("P001,1")
        result_implicit = calc_shipping("P001")
        assert result_explicit == result_implicit


# ══════════════════════════════════════════════════════════
# TEST: calc_tax
# ══════════════════════════════════════════════════════════

class TestCalcTax:

    def test_tax_on_original_price(self):
        # P001: $49.99 × 10% = $5.00 → total $54.99
        result = calc_tax("P001")
        assert "10%" in result
        assert "5.00" in result
        assert "54.99" in result

    def test_tax_on_discounted_price(self):
        # P007 after 20% off = $103.92 × 10% = $10.39 → $114.31
        result = calc_tax("P007,103.92")
        assert "10%" in result
        assert "10.39" in result
        assert "114.31" in result

    def test_eight_percent_tax(self):
        # P005 (Water Bottle): $22.00 × 8% = $1.76 → $23.76
        result = calc_tax("P005")
        assert "8%" in result
        assert "1.76" in result
        assert "23.76" in result

    def test_twelve_percent_tax(self):
        # P011 (Cotton T-Shirt): $18.00 × 12% = $2.16 → $20.16
        result = calc_tax("P011")
        assert "12%" in result
        assert "2.16" in result

    def test_invalid_product(self):
        result = calc_tax("P999")
        assert "Không tìm thấy" in result


# ══════════════════════════════════════════════════════════
# Runner độc lập (không cần pytest)
# ══════════════════════════════════════════════════════════

def _run_all():
    test_classes = [
        TestCheckStock,
        TestGetPrice,
        TestGetDiscount,
        TestCalcShipping,
        TestCalcTax,
    ]

    total = passed = failed = 0
    failures = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        print(f"\n{'─'*50}")
        print(f"  {cls.__name__}")
        print(f"{'─'*50}")

        for method in methods:
            total += 1
            try:
                getattr(instance, method)()
                print(f"  ✅ PASS  {method}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌ FAIL  {method}")
                failures.append(f"{cls.__name__}::{method} → {e}")
                failed += 1
            except Exception as e:
                print(f"  💥 ERROR {method}: {e}")
                failures.append(f"{cls.__name__}::{method} → ERROR: {e}")
                failed += 1

    print(f"\n{'═'*50}")
    print(f"  KẾT QUẢ: {passed}/{total} PASS  |  {failed} FAIL")
    print(f"{'═'*50}")

    if failures:
        print("\nChi tiết lỗi:")
        for f in failures:
            print(f"  • {f}")

    return failed == 0


if __name__ == "__main__":
    success = _run_all()
    sys.exit(0 if success else 1)
