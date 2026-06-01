"""
chatbot.py – Baseline Chatbot (Thành viên C)
=============================================
Trợ lý mua hàng E-commerce KHÔNG dùng vòng ReAct.
Chatbot gọi tool trực tiếp dựa trên keyword matching từ câu hỏi của user.

Mục đích: So sánh với ReActAgent để thấy hạn chế của pure-dispatch chatbot.
- Không có Thought–Observation loop → không suy luận đa bước
- Phụ thuộc keyword cứng → dễ miss intent phức tạp
- Không tự chuỗi nhiều tool liên tiếp

Chạy:
    python chatbot.py
"""

import csv
import os
import sys
from typing import Any, Dict, Optional

# ─── Load dữ liệu từ CSV ───────────────────────────────────────────────────────
_CSV_PATH = os.path.join(os.path.dirname(__file__), "src", "data", "products.csv")


def _load_csv() -> Dict[str, Dict[str, Any]]:
    products: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(_CSV_PATH):
        return products
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["product_id"].strip()
            products[pid] = {
                "name": row["name"],
                "category": row["category"],
                "price": float(row["price_usd"]),
                "price_usd": float(row["price_usd"]),
                "stock": int(row["stock_qty"]),
                "stock_qty": int(row["stock_qty"]),
                "tax_rate": float(row["tax_rate"]),
                "shipping_weight_kg": float(row["shipping_weight_kg"]),
                "coupon_code": row["coupon_code"].strip(),
            }
    return products


PRODUCTS: Dict[str, Dict[str, Any]] = _load_csv()

# Inventory shape dùng cho check_stock/get_stock_level
INVENTORY: Dict[str, Any] = {pid: p["stock"] for pid, p in PRODUCTS.items()}

# Coupon map mặc định (derived từ CSV)
COUPONS: Dict[str, Any] = {
    p["coupon_code"]: {"type": "percent", "value": float("".join(c for c in p["coupon_code"] if c.isdigit()))}
    for p in PRODUCTS.values()
    if any(c.isdigit() for c in p["coupon_code"])
}


# ─── Import tools ──────────────────────────────────────────────────────────────
from src.tools.check_stock import check_stock, get_stock_level
from src.tools.get_price import get_price
from src.tools.get_discount import get_discount
from src.tools.calc_shipping import calc_shipping
from src.tools.calc_tax import calc_tax


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _find_product_id(text: str) -> Optional[str]:
    """Tìm product_id (P001..P020) trong câu hỏi, hoặc match theo tên."""
    text_upper = text.upper()
    # Tìm mã trực tiếp
    for pid in PRODUCTS:
        if pid.upper() in text_upper:
            return pid
    # Tìm theo tên sản phẩm (partial match)
    text_lower = text.lower()
    for pid, p in PRODUCTS.items():
        if p["name"].lower() in text_lower or any(
            word in text_lower for word in p["name"].lower().split() if len(word) > 3
        ):
            return pid
    return None


def _find_coupon(text: str) -> Optional[str]:
    """Tìm coupon code trong câu hỏi."""
    text_upper = text.upper()
    for code in COUPONS:
        if code.upper() in text_upper:
            return code
    return None


def _find_quantity(text: str) -> int:
    """Tìm số lượng trong câu hỏi."""
    import re
    match = re.search(r"\b(\d+)\s*(?:cái|sp|sản phẩm|chiếc|units?|pcs?|pieces?|items?)\b", text.lower())
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d+)\b", text)
    if match:
        qty = int(match.group(1))
        if 1 <= qty <= 99:
            return qty
    return 1


def _find_region(text: str) -> str:
    """Xác định region cho tính thuế."""
    text_upper = text.upper()
    for code in ("NY", "TX", "CA", "EU"):
        if code in text_upper:
            return code
    return "US"


def _find_shipping_method(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ("express", "nhanh", "gấp")):
        return "express"
    if any(w in text_lower for w in ("overnight", "hỏa tốc", "trong ngày")):
        return "overnight"
    return "standard"


# ─── Baseline Chatbot ──────────────────────────────────────────────────────────
class BaselineChatbot:
    """
    Pure tool-dispatch chatbot. Không có ReAct loop.
    Phân tích intent bằng keyword matching, gọi tool phù hợp, trả lời.
    """

    def __init__(self):
        self.history: list = []

    def respond(self, query: str) -> str:
        """Phân tích query → dispatch đến tool → trả lời dạng text."""
        q = query.lower().strip()
        pid = _find_product_id(query)

        # ── Intent: Tổng giá cuối (multi-step) ─────────────────────────────────
        if any(kw in q for kw in ("tổng", "total", "cuối", "final", "bao nhiêu tiền", "hết bao nhiêu")):
            return self._handle_full_price(query, pid)

        # ── Intent: Kiểm tra tồn kho ────────────────────────────────────────────
        if any(kw in q for kw in ("tồn kho", "còn hàng", "stock", "còn không", "số lượng", "hàng")):
            return self._handle_stock(pid)

        # ── Intent: Giá sản phẩm ────────────────────────────────────────────────
        if any(kw in q for kw in ("giá", "price", "cost", "bao nhiêu", "tiền")):
            coupon = _find_coupon(query)
            if coupon:
                return self._handle_discount(pid, coupon)
            return self._handle_price(pid)

        # ── Intent: Giảm giá / coupon ───────────────────────────────────────────
        if any(kw in q for kw in ("mã", "coupon", "giảm giá", "discount", "code", "khuyến mãi")):
            coupon = _find_coupon(query)
            return self._handle_discount(pid, coupon)

        # ── Intent: Phí vận chuyển ──────────────────────────────────────────────
        if any(kw in q for kw in ("ship", "vận chuyển", "giao hàng", "phí", "shipping")):
            return self._handle_shipping(query, pid)

        # ── Intent: Thuế ────────────────────────────────────────────────────────
        if any(kw in q for kw in ("thuế", "tax", "vat")):
            return self._handle_tax(query, pid)

        # ── Intent: Danh sách sản phẩm / tư vấn ────────────────────────────────
        if any(kw in q for kw in ("danh sách", "list", "tư vấn", "gợi ý", "recommend", "có những")):
            return self._handle_list()

        # ── Fallback ─────────────────────────────────────────────────────────────
        return (
            "Xin chào! Tôi có thể giúp bạn:\n"
            "• Kiểm tra tồn kho: 'P001 còn hàng không?'\n"
            "• Xem giá: 'Giá của P007 là bao nhiêu?'\n"
            "• Áp coupon: 'Dùng mã HEAD20 cho P007'\n"
            "• Phí ship: 'Phí vận chuyển P004 2 cái'\n"
            "• Tính thuế: 'Thuế P001'\n"
            "• Tổng tiền: 'Mua 2 cái P007 dùng mã HEAD20, tổng bao nhiêu?'"
        )

    # ── Handlers ────────────────────────────────────────────────────────────────

    def _handle_stock(self, pid: Optional[str]) -> str:
        if not pid:
            return "Vui lòng cho biết mã sản phẩm (ví dụ: P001) hoặc tên sản phẩm."
        result = check_stock(pid, INVENTORY)
        p = PRODUCTS.get(pid, {})
        name = p.get("name", pid)
        if result["available"]:
            qty = result["quantity"]
            status = "SẮP HẾT" if qty <= 50 else "CÒN HÀNG (ÍT)" if qty <= 100 else "CÒN HÀNG"
            return f"[{pid}] {name}: Còn {qty} sản phẩm – Trạng thái: {status}"
        return f"[{pid}] {name}: HẾT HÀNG – Hiện không thể đặt mua."

    def _handle_price(self, pid: Optional[str]) -> str:
        if not pid:
            return "Vui lòng cho biết mã hoặc tên sản phẩm muốn xem giá."
        result = get_price(pid, PRODUCTS)
        name = PRODUCTS.get(pid, {}).get("name", pid)
        return f"[{pid}] {name}: Giá gốc ${result['price']:.2f} {result['currency']}"

    def _handle_discount(self, pid: Optional[str], coupon: Optional[str]) -> str:
        if not pid:
            return "Vui lòng cho biết mã sản phẩm muốn áp giảm giá."
        price_result = get_price(pid, PRODUCTS)
        base = price_result["price"]
        name = PRODUCTS.get(pid, {}).get("name", pid)

        # Nếu không tìm được coupon trong query, dùng coupon mặc định của SP
        effective_coupon = coupon or PRODUCTS.get(pid, {}).get("coupon_code")
        result = get_discount(pid, base, coupons=COUPONS, coupon_code=effective_coupon, products=PRODUCTS)

        if result["applied_coupon"]:
            return (
                f"[{pid}] {name}\n"
                f"  Giá gốc     : ${base:.2f}\n"
                f"  Mã giảm giá : {result['applied_coupon']} ({result['details']})\n"
                f"  Giảm        : -${result['discount_amount']:.2f}\n"
                f"  Giá sau giảm: ${result['final_price']:.2f}"
            )
        return (
            f"[{pid}] {name}: Giá gốc ${base:.2f} – "
            f"Không áp được mã giảm giá ({result['details']})"
        )

    def _handle_shipping(self, query: str, pid: Optional[str]) -> str:
        if not pid:
            return "Vui lòng cho biết mã sản phẩm để tính phí vận chuyển."
        qty = _find_quantity(query)
        method = _find_shipping_method(query)
        weight = PRODUCTS.get(pid, {}).get("shipping_weight_kg", 0.5) * qty
        name = PRODUCTS.get(pid, {}).get("name", pid)
        dest = {"country": "US"}
        result = calc_shipping(weight, dest, method)
        return (
            f"[{pid}] {name} × {qty}\n"
            f"  Khối lượng  : {weight:.2f} kg\n"
            f"  Phương thức : {result['method']}\n"
            f"  Phí ship    : ${result['cost']:.2f}\n"
            f"  Thời gian   : {result['estimated_days']} ngày"
        )

    def _handle_tax(self, query: str, pid: Optional[str]) -> str:
        if not pid:
            return "Vui lòng cho biết mã sản phẩm để tính thuế."
        region = _find_region(query)
        base = PRODUCTS.get(pid, {}).get("price", 0.0)
        name = PRODUCTS.get(pid, {}).get("name", pid)
        result = calc_tax(base, region)
        return (
            f"[{pid}] {name}\n"
            f"  Giá trước thuế: ${base:.2f}\n"
            f"  Thuế suất     : {result['rate']*100:.1f}% ({region})\n"
            f"  Tiền thuế     : ${result['tax']:.2f}\n"
            f"  Tổng sau thuế : ${result['total']:.2f}"
        )

    def _handle_full_price(self, query: str, pid: Optional[str]) -> str:
        """Multi-step: giảm giá → thuế → ship → tổng cuối."""
        if not pid:
            return "Vui lòng cho biết mã sản phẩm để tính tổng tiền."

        # Bước 1: Kiểm tra tồn kho
        stock_result = check_stock(pid, INVENTORY)
        if not stock_result["available"]:
            name = PRODUCTS.get(pid, {}).get("name", pid)
            return f"[{pid}] {name} hiện HẾT HÀNG, không thể đặt mua."

        qty = _find_quantity(query)
        p = PRODUCTS.get(pid, {})
        name = p.get("name", pid)
        base = p.get("price", 0.0)
        method = _find_shipping_method(query)
        region = _find_region(query)

        # Bước 2: Áp giảm giá
        coupon = _find_coupon(query) or p.get("coupon_code")
        disc = get_discount(pid, base, coupons=COUPONS, coupon_code=coupon, products=PRODUCTS)
        price_after_discount = disc["final_price"]

        # Bước 3: Tính thuế
        tax_result = calc_tax(price_after_discount * qty, region)

        # Bước 4: Tính phí vận chuyển
        weight_total = p.get("shipping_weight_kg", 0.5) * qty
        ship_result = calc_shipping(weight_total, {"country": "US"}, method)

        # Bước 5: Tổng cuối
        grand_total = tax_result["total"] + ship_result["cost"]
        coupon_line = (
            f"  Mã giảm giá     : {disc['applied_coupon']} (-${disc['discount_amount']:.2f}/sp)\n"
            if disc["applied_coupon"]
            else "  Mã giảm giá     : Không có\n"
        )

        return (
            f"{'='*45}\n"
            f"  ĐƠN HÀNG: [{pid}] {name}\n"
            f"{'='*45}\n"
            f"  Số lượng        : {qty}\n"
            f"  Giá gốc/sp      : ${base:.2f}\n"
            + coupon_line +
            f"  Giá sau giảm/sp : ${price_after_discount:.2f}\n"
            f"  Tạm tính        : ${price_after_discount * qty:.2f}\n"
            f"  Thuế ({region} {tax_result['rate']*100:.1f}%): ${tax_result['tax']:.2f}\n"
            f"  Phí ship ({method}): ${ship_result['cost']:.2f} ({ship_result['estimated_days']} ngày)\n"
            f"{'─'*45}\n"
            f"  TỔNG CỘNG       : ${grand_total:.2f}\n"
            f"{'='*45}"
        )

    def _handle_list(self) -> str:
        lines = ["Danh sách sản phẩm hiện có:\n"]
        for pid, p in PRODUCTS.items():
            avail = "✅" if p["stock"] > 0 else "❌"
            lines.append(f"  {avail} [{pid}] {p['name']} – ${p['price']:.2f} ({p['category']})")
        return "\n".join(lines)

    def reset(self):
        self.history.clear()


# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
    bot = BaselineChatbot()
    print("=" * 55)
    print("  Baseline Chatbot – E-Commerce Shopping Assistant")
    print("  (gõ 'exit' để thoát)")
    print("=" * 55)
    while True:
        try:
            user_input = input("\nBạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            break
        if user_input.lower() in ("exit", "quit", "thoát", "q"):
            print("Tạm biệt!")
            break
        if not user_input:
            continue
        print(f"\nBot: {bot.respond(user_input)}")


if __name__ == "__main__":
    main()
