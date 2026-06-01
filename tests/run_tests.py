"""
tests/run_tests.py – Test Suite Runner & Report Generator (Thành viên C)
=========================================================================
Chạy toàn bộ test suite và xuất báo cáo pass/fail.

Chạy:
    python tests/run_tests.py
    python tests/run_tests.py --report     # xuất file report/test_report.md
"""

import os
import sys
import time
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Import test classes ──────────────────────────────────────────────────────
from tests.test_tools import (
    TestCheckStock, TestGetPrice, TestGetDiscount,
    TestCalcShipping, TestCalcTax,
    PRODUCTS, INVENTORY, COUPONS,
)
from tests.test_chatbot import (
    TestSingleStep, TestMultiStep, TestChatbotVsAgentComparison,
)


# ─── Runner ───────────────────────────────────────────────────────────────────
def run_suite(classes: list) -> dict:
    results = []
    for cls in classes:
        inst = cls()
        methods = sorted(m for m in dir(inst) if m.startswith("test_"))
        for m in methods:
            start = time.perf_counter()
            try:
                if hasattr(inst, "setup_method"):
                    inst.setup_method()
                getattr(inst, m)()
                elapsed = (time.perf_counter() - start) * 1000
                doc = (getattr(getattr(inst, m), "__doc__", "") or "").strip().split("\n")[0]
                results.append({
                    "class": cls.__name__, "method": m,
                    "status": "PASS", "doc": doc, "ms": elapsed, "error": ""
                })
            except AssertionError as e:
                elapsed = (time.perf_counter() - start) * 1000
                results.append({
                    "class": cls.__name__, "method": m,
                    "status": "FAIL", "doc": "", "ms": elapsed, "error": str(e)
                })
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                results.append({
                    "class": cls.__name__, "method": m,
                    "status": "ERROR", "doc": "", "ms": elapsed,
                    "error": f"{type(e).__name__}: {e}"
                })
    return results


def print_results(results: list):
    current_cls = None
    for r in results:
        if r["class"] != current_cls:
            current_cls = r["class"]
            print(f"\n{'-'*65}")
            print(f"  {current_cls}")
            print(f"{'-'*65}")
        icon = "[PASS]" if r["status"] == "PASS" else ("[FAIL]" if r["status"] == "FAIL" else "[ERR ]")
        doc = f"  {r['doc']}" if r["doc"] else ""
        print(f"  {icon} {r['method']:<50} {r['ms']:5.1f}ms{doc}")
        if r["error"]:
            print(f"         -> {r['error'][:80]}")


def summary(results: list) -> tuple:
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    return total, passed, failed, errors


def generate_report(results: list, output_path: str):
    total, passed, failed, errors = summary(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Test Report – E-Commerce Chatbot & Tools",
        f"",
        f"**Thành viên C – Lead Baseline**  ",
        f"**Ngày chạy:** {now}  ",
        f"",
        f"## Tổng quan",
        f"",
        f"| Chỉ số | Giá trị |",
        f"|--------|---------|",
        f"| Tổng test cases | {total} |",
        f"| ✅ PASS | {passed} |",
        f"| ❌ FAIL | {failed} |",
        f"| 💥 ERROR | {errors} |",
        f"| Tỷ lệ pass | {passed/total*100:.1f}% |",
        f"",
        f"## Chi tiết kết quả",
        f"",
    ]

    current_cls = None
    for r in results:
        if r["class"] != current_cls:
            current_cls = r["class"]
            lines.append(f"### {current_cls}")
            lines.append("")
            lines.append("| Test Case | Trạng thái | Thời gian | Mô tả |")
            lines.append("|-----------|-----------|-----------|-------|")

        icon = "✅ PASS" if r["status"] == "PASS" else ("❌ FAIL" if r["status"] == "FAIL" else "💥 ERROR")
        error_note = f" _{r['error'][:60]}_" if r["error"] else ""
        lines.append(f"| `{r['method']}` | {icon} | {r['ms']:.1f}ms | {r['doc']}{error_note} |")

    lines.append("")
    lines.append("## Phân tích: Chatbot Baseline vs ReAct Agent")
    lines.append("")
    lines.append("| Khả năng | Baseline Chatbot | ReAct Agent |")
    lines.append("|----------|-----------------|-------------|")
    lines.append("| Kiểm tra tồn kho đơn giản | ✅ | ✅ |")
    lines.append("| Áp mã giảm giá | ✅ | ✅ |")
    lines.append("| Tính phí ship + thuế | ✅ | ✅ |")
    lines.append("| Multi-step chuỗi tool | ⚠️ (keyword dispatch) | ✅ (Thought–Action loop) |")
    lines.append("| Xử lý intent mơ hồ | ❌ | ✅ |")
    lines.append("| Self-correct khi tool fail | ❌ | ✅ |")
    lines.append("| Không cần LLM API | ✅ | ❌ |")
    lines.append("")
    lines.append("---")
    lines.append(f"*Báo cáo tự động sinh bởi `tests/run_tests.py`*")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n📄 Báo cáo đã lưu: {output_path}")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Run E-Commerce test suite")
    parser.add_argument("--report", action="store_true", help="Xuất báo cáo Markdown")
    args = parser.parse_args()

    all_classes = [
        TestCheckStock, TestGetPrice, TestGetDiscount, TestCalcShipping, TestCalcTax,
        TestSingleStep, TestMultiStep, TestChatbotVsAgentComparison,
    ]

    print("=" * 65)
    print("  E-Commerce Chatbot & Tools - Test Suite")
    print("  Thanh vien C - Lead Baseline")
    print("=" * 65)

    results = run_suite(all_classes)
    print_results(results)

    total, passed, failed, errors = summary(results)
    print(f"\n{'='*65}")
    print(f"  TONG: {passed}/{total} PASS  |  {failed} FAIL  |  {errors} ERROR")
    rate = passed / total * 100 if total else 0
    print(f"  TY LE PASS: {rate:.1f}%")
    print(f"{'='*65}")

    if args.report:
        report_path = os.path.join(
            os.path.dirname(__file__), "..", "report", "test_report.md"
        )
        generate_report(results, report_path)

    sys.exit(0 if failed == 0 and errors == 0 else 1)


if __name__ == "__main__":
    main()
