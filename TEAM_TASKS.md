# Kế Hoạch Phân Công Nhóm (5 thành viên)

Tài liệu này phân chia công việc rõ ràng cho đội 5 người dựa trên các yêu cầu trong dự án (README, SCORING, INSTRUCTOR_GUIDE, EVALUATION).

## Tổng quan ngắn
- Chủ đề: Bán lẻ - Trợ lý mua hàng E‑commerce (dữ liệu giả lập)
- Mục tiêu: Triển khai chatbot baseline và Agent ReAct (v1 → v2), có telemetry (logs JSON), chạy test cases, và nộp báo cáo nhóm + cá nhân.

## Danh sách thành viên
- Thành viên A: [Tên A]
- Thành viên B: [Tên B]
- Thành viên C: [Tên C]
- Thành viên D: [Tên D]
- Thành viên E: [Tên E]

---

## Phân công nhiệm vụ (chi tiết)

1) Thành viên A — Thiết lập môi trường & data giả lập (Lead Env/Data)
- Nhiệm vụ:
  - Sao chép và cấu hình file môi trường (`.env`) và hướng dẫn thiết lập.
  - Cài đặt dependencies: `pip install -r requirements.txt` và kiểm tra test môi trường.
  - Tạo dữ liệu giả lập trong `src/data.py` hoặc `data/products.csv` (~20 sản phẩm, vài coupon).
- Deliverables:
  - `src/data.py` hoặc `data/products.csv` với sample entries.
  - Hướng dẫn ngắn trong `README.md` nếu cần cập nhật.
  - Thời gian ước tính: 0.5–1 giờ.

2) Thành viên B — Tools (Lead Tools)
- Nhiệm vụ:
  - Viết các tool stubs trong `src/tools/` theo spec: `check_stock`, `get_price`, `get_discount`, `calc_shipping`, `calc_tax`.
  - Viết doc ngắn cho mỗi tool (input format, output format, ví dụ).
- Deliverables:
  - Folder `src/tools/` với các file tool và file `__init__.py`.
  - Tài liệu tool specs (README hoặc docstring).
  - Thời gian ước tính: 2 giờ.

3) Thành viên C — Chatbot baseline & tests (Lead Baseline)
- Nhiệm vụ:
  - Implement hoặc kiểm tra `chatbot.py` (baseline) để chạy các test case đa bước.
  - Viết 5–10 test cases đơn giản/multi-step (scripts hoặc pytest) để so sánh với Agent.
  - Tạo script chạy test suite cơ bản.
- Deliverables:
  - `chatbot.py` (hoặc cập nhật có sẵn), `tests/` test cases.
  - Test report (pass/fail) để ghi vào báo cáo nhóm.
  - Thời gian ước tính: 1–2 giờ.

4) Thành viên D — Agent ReAct v1 & provider switching (Lead Agent)
- Nhiệm vụ:
  - Implement vòng `Thought → Action → Observation` trong `src/agent/agent.py`.
  - Tích hợp `LLMProvider` để hoán đổi giữa OpenAI / Gemini / local provider.
  - Thiết lập `max_steps`, parsing của Action/Observation, và guardrails (final answer detection).
- Deliverables:
  - `src/agent/agent.py` hoạt động với ít nhất 2 tools.
  - Demo script chạy agent trên test cases.
  - Thời gian ước tính: 3–4 giờ.

5) Thành viên E — Telemetry, evaluation, báo cáo (Lead Telemetry & Reporting)
- Nhiệm vụ:
  - Thiết lập logging JSON cho mỗi bước agent vào `logs/` (fields: timestamp, thought, action, observation, tokens, duration).
  - Viết script phân tích metrics: token usage, latency, loop count (dựa vào `logs/`).
  - Tập hợp `GROUP_REPORT_[TEAM_NAME].md` và hỗ trợ từng thành viên hoàn thành `REPORT_[YOUR_NAME].md` theo template trong `report/`.
  - Chuẩn bị vật chứng để nộp (snippets log, P50/P99 latency, token counts).
- Deliverables:
  - `logs/` chứa JSON traces.
  - Script tính metrics (ví dụ `scripts/evaluate_logs.py`).
  - File báo cáo nhóm và hướng dẫn để cá nhân điền báo cáo.
  - Thời gian ước tính: 1.5–2.5 giờ.

---

## Quy trình phối hợp & timeline đề xuất (1 ngày hoặc lab 4 giờ chia nhỏ)
- Sprint 0 (30–60 phút): Thành viên A chuẩn env + data; Thành viên B khởi tạo stubs tools.
- Sprint 1 (1.5–2 giờ): Thành viên C implement chatbot baseline + tests; thành viên B hoàn thiện tools.
- Sprint 2 (2–3 giờ): Thành viên D implement agent ReAct; thành viên E bắt đầu telemetry.
- Sprint 3 (1 giờ): Chạy test, thu failure traces, chỉnh sửa nhanh, hoàn thiện report.

## Checklist nhanh (bấm để tick khi xong)
- [ ] `.env` được cấu hình và dependencies cài đặt
- [ ] `src/data.py` hoặc `data/products.csv` có dữ liệu mẫu
- [ ] `src/tools/` hoàn chỉnh với specs
- [ ] `chatbot.py` chạy được với test cases
- [ ] `src/agent/agent.py` ReAct hoạt động (max 5 loops)
- [x] `logs/` có JSON traces
- [ ] `GROUP_REPORT_[TEAM_NAME].md` và `REPORT_[NAME].md` đã hoàn tất

## Tài liệu tham khảo
- Template báo cáo nhóm: [report/group_report/TEMPLATE_GROUP_REPORT.md](report/group_report/TEMPLATE_GROUP_REPORT.md)
- Template báo cáo cá nhân: [report/individual_reports/TEMPLATE_INDIVIDUAL_REPORT.md](report/individual_reports/TEMPLATE_INDIVIDUAL_REPORT.md)
- README dự án: [README.md](README.md)

---

Nếu bạn muốn, tôi có thể: (A) tự tạo `src/data.py` với dữ liệu giả lập, (B) scaffold các tool stubs trong `src/tools/`, hoặc (C) tạo mẫu `GROUP_REPORT` đã điền sơ bộ. Chọn 1 hoặc nhiều tuỳ chọn.
