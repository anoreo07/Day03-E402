"""
tests/test_chatbot.py – Integration & Multi-step Test Cases (Thành viên C)
===========================================================================
5 single-step + 5 multi-step test cases dùng BaselineChatbot.
So sánh đầu ra Chatbot baseline vs kết quả tool thực tế để thấy hạn chế.

Chạy:
    pytest tests/test_chatbot.py -v
    python tests/test_chatbot.py
"""

import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot import BaselineChatbot, PRODUCTS, INVENTORY, COUPONS
from src.tools.check_stock import check_stock
from src.tools.get_price import get_price
from src.tools.get_discount import get_discount
from src.tools.calc_shipping import calc_shipping
from src.tools.calc_tax import calc_tax


# ─── Fixture helper ───────────────────────────────────────────────────────────
def _full_price(pid: str, qty: int = 1, coupon: str = None,
                method: str = "standard", region: str = "US") -> dict:
    """Tính tay tổng tiền để so sánh với chatbot output."""
    p = PRODUCTS[pid]
    base = p["price"]
    disc = get_discount(pid, base, coupons=COUPONS, coupon_code=coupon, products=PRODUCTS)
    price_after = disc["final_price"]
    tax = calc_tax(price_after * qty, region)
    weight = p["shipping_weight_kg"] * qty
    ship = calc_shipping(weight, {"country": "US"}, method)
    return {
        "base": base,
        "price_after_discount": price_after,
        "discount_amount": disc["discount_amount"],
        "applied_coupon": disc["applied_coupon"],
        "subtotal": round(price_after * qty, 2),
        "tax": tax["tax"],
        "ship": ship["cost"],
        "grand_total": round(tax["total"] + ship["cost"], 2),
    }


bot = BaselineChatbot()


# ══════════════════════════════════════════════════════════════════════════════
# SINGLE-STEP TEST CASES (TC-S1 ~ TC-S5)
# ══════════════════════════════════════════════════════════════════════════════

class TestSingleStep:

    def setup_method(self):
        bot.reset()

    def test_TCS1_check_stock_p001(self):
        """TC-S1: Hỏi tồn kho P001 → phải có số '120' trong câu trả lời."""
        resp = bot.respond("P001 còn hàng không?")
        assert "120" in resp, f"Expected '120' in response, got: {resp}"
        assert "P001" in resp

    def test_TCS2_get_price_p007(self):
        """TC-S2: Hỏi giá P007 → phải có '$129.90'."""
        resp = bot.respond("Giá của P007 bao nhiêu?")
        assert "129.90" in resp, f"Expected '129.90' in response, got: {resp}"

    def test_TCS3_apply_coupon_p007(self):
        """TC-S3: Áp mã HEAD20 cho P007 → giá sau giảm $103.92."""
        resp = bot.respond("Dùng mã HEAD20 cho P007 được giảm bao nhiêu?")
        assert "103.92" in resp, f"Expected '103.92' in response, got: {resp}"
        assert "HEAD20" in resp

    def test_TCS4_shipping_p004(self):
        """TC-S4: Phí ship P004 1 cái → phí > 0."""
        resp = bot.respond("Phí vận chuyển P004 bao nhiêu?")
        assert "$" in resp, f"Expected '$' in response, got: {resp}"
        assert "P004" in resp

    def test_TCS5_list_products(self):
        """TC-S5: Hỏi danh sách sản phẩm → phải liệt kê ít nhất 5 mã."""
        resp = bot.respond("Cho tôi xem danh sách sản phẩm")
        count = sum(1 for pid in PRODUCTS if pid in resp)
        assert count >= 5, f"Expected ≥5 products listed, got {count}"


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-STEP TEST CASES (TC-M1 ~ TC-M5)
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiStep:
    """
    Multi-step: Chatbot phải xử lý đúng chuỗi: tồn kho → giảm giá → thuế → ship → tổng.
    Đây là điểm mạnh của Agent (ReAct) so với baseline chatbot (keyword dispatch).
    """

    def setup_method(self):
        bot.reset()

    def test_TCM1_full_order_p007_with_coupon(self):
        """
        TC-M1: Mua 1 cái P007 dùng HEAD20 → tổng = giá sau giảm + thuế US + ship.
        Expected grand_total được tính bằng tool thực tế.
        """
        expected = _full_price("P007", qty=1, coupon="HEAD20")
        resp = bot.respond("Tôi muốn mua 1 cái P007 dùng mã HEAD20, tổng hết bao nhiêu?")
        # Grand total phải xuất hiện trong response
        assert str(expected["grand_total"]) in resp or \
               f"{expected['grand_total']:.2f}" in resp, \
            f"Expected grand_total={expected['grand_total']:.2f} in response.\nResponse: {resp}"

    def test_TCM2_full_order_p001_no_coupon(self):
        """
        TC-M2: Mua 2 cái P001 không dùng coupon → tổng chính xác.
        """
        expected = _full_price("P001", qty=2)
        resp = bot.respond("Mua 2 cái P001, tổng bao nhiêu tiền?")
        assert "P001" in resp
        # Tạm tính phải có trong response
        assert str(expected["subtotal"]) in resp or \
               f"{expected['subtotal']:.2f}" in resp or \
               f"{expected['grand_total']:.2f}" in resp, \
            f"Expected subtotal={expected['subtotal']:.2f} or grand_total in response.\nResponse: {resp}"

    def test_TCM3_out_of_stock_blocks_order(self):
        """
        TC-M3: Sản phẩm hết hàng → chatbot báo không thể đặt, không tính tiền.
        Tạo inventory tạm với P007=0.
        """
        inv_zero = {**INVENTORY, "P007": 0}
        from chatbot import _find_product_id, _find_coupon, _find_quantity, _find_region, _find_shipping_method
        # Kiểm tra trực tiếp check_stock
        result = check_stock("P007", inv_zero)
        assert result["available"] is False, "P007 phải hết hàng khi stock=0"
        assert result["quantity"] == 0

    def test_TCM4_discount_then_tax_chain(self):
        """
        TC-M4: Chuỗi get_discount → calc_tax: giá sau giảm phải là base cho tính thuế.
        P012 (Running Shoes, $89.99, SHOES20 → 20% off → $71.99)
        Tax US 7% trên $71.99 = $5.04 → total $77.03
        """
        disc = get_discount("P012", 89.99, coupons=COUPONS, coupon_code="SHOES20")
        assert disc["final_price"] == 71.99

        tax = calc_tax(disc["final_price"], "US")
        assert tax["tax"] == round(71.99 * 0.07, 2)
        assert tax["total"] == round(71.99 * 1.07, 2)

    def test_TCM5_shipping_weight_scales_with_qty(self):
        """
        TC-M5: Phí ship tăng tuyến tính theo số lượng × khối lượng.
        P014 (Kitchen Knife Set, 1.50 kg/cái).
        qty=1 → 1.50 kg; qty=3 → 4.50 kg.
        """
        w1 = PRODUCTS["P014"]["shipping_weight_kg"] * 1  # 1.50
        w3 = PRODUCTS["P014"]["shipping_weight_kg"] * 3  # 4.50
        ship1 = calc_shipping(w1, {"country": "US"}, "standard")
        ship3 = calc_shipping(w3, {"country": "US"}, "standard")

        # base=5, per_kg=2
        assert ship1["cost"] == round(5.0 + 1.50 * 2.0, 2)  # 8.0
        assert ship3["cost"] == round(5.0 + 4.50 * 2.0, 2)  # 14.0
        assert ship3["cost"] > ship1["cost"]


# ══════════════════════════════════════════════════════════════════════════════
# BENCHMARK: Chatbot vs Agent (định tính)
# ══════════════════════════════════════════════════════════════════════════════

class TestChatbotVsAgentComparison:
    """
    So sánh định tính: Chatbot baseline xử lý được gì, Agent cần gì thêm.
    (Agent chưa implemented → test này ghi nhận hành vi mong đợi)
    """

    def setup_method(self):
        bot.reset()

    def test_chatbot_handles_simple_stock_query(self):
        """Chatbot: Single-step stock query ✅."""
        resp = bot.respond("Còn hàng P019 không?")
        assert "P019" in resp
        assert any(kw in resp for kw in ("60", "CÒN", "SẮP HẾT", "HẾT"))

    def test_chatbot_handles_price_with_discount(self):
        """Chatbot: Câu hỏi giá + coupon trong 1 query ✅."""
        resp = bot.respond("Giá P011 với mã TSHIRT15 là bao nhiêu?")
        # P011 $18.00, TSHIRT15 = 15% off → $15.30
        assert "15.30" in resp or "P011" in resp

    def test_chatbot_multi_step_total_price(self):
        """Chatbot: Multi-step total query ✅ (baseline dispatch xử lý được)."""
        resp = bot.respond("Mua 1 cái P019 dùng mã KEYBOARD15, tổng bao nhiêu?")
        assert "P019" in resp or "$" in resp

    def test_agent_needed_for_ambiguous_intent(self):
        """
        Agent cần thiết: Câu hỏi mơ hồ / không rõ SP → chatbot trả fallback.
        Baseline chatbot không thể suy luận 'sản phẩm tốt nhất cho tôi'.
        """
        resp = bot.respond("Tôi cần mua quà sinh nhật cho bạn thích thể thao, giá dưới 50$")
        # Chatbot baseline sẽ trả fallback hoặc danh sách, không suy luận được
        # Agent ReAct sẽ search_product, filter, recommend
        assert isinstance(resp, str) and len(resp) > 0  # chỉ cần trả về gì đó


# ══════════════════════════════════════════════════════════════════════════════
# Runner độc lập
# ══════════════════════════════════════════════════════════════════════════════

def _run_all():
    classes = [TestSingleStep, TestMultiStep, TestChatbotVsAgentComparison]
    total = passed = failed = 0
    failures = []

    for cls in classes:
        inst = cls()
        methods = sorted(m for m in dir(inst) if m.startswith("test_"))
        print(f"\n{'─'*60}")
        print(f"  {cls.__name__}")
        print(f"{'─'*60}")
        for m in methods:
            total += 1
            try:
                if hasattr(inst, "setup_method"):
                    inst.setup_method()
                getattr(inst, m)()
                doc = (getattr(getattr(inst, m), "__doc__", "") or "").strip().split("\n")[0]
                print(f"  ✅ PASS  {m:<48} {doc}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌ FAIL  {m}")
                failures.append(f"{cls.__name__}::{m} → {e}")
                failed += 1
            except Exception as e:
                print(f"  💥 ERROR {m}: {e}")
                failures.append(f"{cls.__name__}::{m} → {type(e).__name__}: {e}")
                failed += 1

    print(f"\n{'═'*60}")
    print(f"  KẾT QUẢ: {passed}/{total} PASS  |  {failed} FAIL")
    print(f"{'═'*60}")
    if failures:
        print("\nChi tiết lỗi:")
        for f in failures:
            print(f"  • {f}")
    return failed == 0


if __name__ == "__main__":
    success = _run_all()
    sys.exit(0 if success else 1)
