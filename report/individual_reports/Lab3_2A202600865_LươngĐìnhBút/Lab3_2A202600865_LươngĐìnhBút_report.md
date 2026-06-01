# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Lương Đình Bút
- **Student ID**: 2A2020600865
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

### Các Module Đã Triển Khai

1. **`src/telemetry/logger.py`** — Structured JSON Logger
   - Đã cải tiến file logger thành **Singleton pattern** để đảm bảo không bị duplicate log handlers (tránh lặp dữ liệu) khi instance được gọi ở nhiều nơi.
   - Định dạng log lưu thành **JSONL** (Mỗi line là 1 object JSON) với múi giờ chuẩn UTC (`timezone.utc`), giúp file `logs/YYYY-MM-DD.log` dễ dàng parse tự động.
   - Thêm helper method `log_step()` nhận tham số trực tiếp (step, thought, action, observation, usage) và tự build JSON, giúp code trong `agent.py` sạch sẽ và đồng nhất.

2. **`scripts/evaluate_logs.py`** — Script Phân Tích Metrics
   - Xây dựng script để đọc tự động toàn bộ file JSONL trong thư mục `logs/`.
   - Tính toán và tổng hợp các metrics quan trọng:
     - Tính tổng chi phí (Cost) và Token (Prompt, Completion, Total).
     - Phân tích Latency: Tự build hàm tính P50, P90, P99 Percentile interpolation tay (không dùng numpy) nhằm giảm phụ thuộc thư viện.
     - Thống kê Tool usage và phân tích các dạng Error (Parse Error, Tool Error).
   - Xuất output ở 2 định dạng: text console dễ nhìn và markdown table (lưu thành `evaluation_report.md`).

3. **`src/tools/ecommerce_tools.py`** — Bridge module
   - (Cross-task support) Tạo bridge module với `functools.partial` để nạp sẵn dữ liệu (`inventory`, `product_prices`) từ `products.csv` vào tool stubs, để ReAct Agent gọi hàm mà chỉ cần truyền đúng tham số của User-facing prompt (`product_id`).

4. **`scripts/generate_sample_logs.py`** — Sinh log mẫu
   - Xây dựng script giả lập agent run traces (chuẩn xác format JSON của agent thật) giúp sinh dữ liệu cho test metrics và report trong tình huống API Key OpenAI hoặc Gemini bị giới hạn (Quota Exceeded/Invalid Key).



## II. Debugging Case Study (10 Points)

### Problem 1: API Quota / Balance Exhausted
- **Mô tả lỗi**: Khi chạy Agent thật với API DeepSeek (`openai` provider) và Gemini, agent crash ngay ở bước 1 (`AGENT_START`) hoặc bước 3 (sau khi gọi tool 2 lần).
- **Log Data**: Trace API trả về lỗi `402 - Insufficient Balance` hoặc `429 - RESOURCE_EXHAUSTED`.
- **Phân tích (Root Cause)**: Do ReAct agent liên tục gửi lại toàn bộ prompt lịch sử (lên tới >1000 tokens mỗi lượt) trong một vòng lặp, dẫn tới giới hạn free tier bị cạn kiệt rất nhanh. Các provider ngắt kết nối và raise HTTP error, script không bắt exception này.
- **Giải pháp (Fix)**: Viết thêm script `generate_sample_logs.py` để mock JSON log traces nhằm kiểm chứng tính đúng đắn của pipeline đo lường metrics mà không phải chịu rủi ro mất phí API. Đồng thời đề xuất thêm `try/except` bao bọc hàm `self.llm.generate()` để agent có thể graceful shutdown khi hết quota, thay vì crash văng traceback.

### Problem 2: Duplicate Handler trong Logger
- **Mô tả lỗi**: Mỗi lần gọi `from src.telemetry.logger import logger` trong file khác nhau, log sinh ra trên console và file bị in 2-3 dòng giống hệt nhau.
- **Phân tích (Root Cause)**: Hàm `__init__` của logger add thêm handler mỗi lần class được khởi tạo.
- **Giải pháp (Fix)**: Áp dụng Singleton qua method `__new__` và dùng cờ `_initialised = True` trong `__init__` để đảm bảo code set up handler chỉ chạy đúng một lần duy nhất trong toàn bộ application lifecycle.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Khả năng quan sát (Observability)**
   Hệ thống ReAct sinh ra một lượng dữ liệu lớn qua mỗi lượt Thought-Action-Observation. Việc có một JSONL logger là "sống còn". Chatbot truyền thống chỉ cần log In/Out, nhưng Agent cần log từng step. Qua đó, em thấy được Agent đôi lúc sẽ "hallucinate" (gọi tên sản phẩm thay vì mã ID), và observation rõ ràng (e.g. `{"price": 0.0}`) giúp dễ dàng debug.

2. **Chi phí và Token Usage (Cost)**
   Qua metrics thu thập được, Agent ReAct tiêu tốn số token tăng theo cấp số cộng (lượt sau kèm lịch sử lượt trước). Trung bình mất >1,000 tokens cho một lượt agent. Do vậy ReAct agent mạnh mẽ để giải bài toán khó nhưng hoàn toàn không kinh tế để trả lời các câu hỏi đơn giản nếu không có Router Agent đứng trước.

3. **Tính tin cậy của Parsing**
   Việc ép agent trả về JSON format (`v2-json-actions`) giảm tỷ lệ `PARSE_ERROR` xuống rất nhiều, thuận tiện hơn hẳn cho Regex parsing so với string text thuần.

---

## IV. Future Improvements (5 Points)

1. **Streaming Metrics và Dashboard Realtime**: Gửi trực tiếp cấu trúc JSON payload sang một Time-series DB (ví dụ InfluxDB) và vẽ dashboard Grafana thay vì chạy script tính toán tĩnh.
2. **Alerting System**: Tích hợp cảnh báo khi `PARSE_ERROR` > 30% trong 5 phút, hoặc khi detect các lỗi 429 Rate Limit từ nhà cung cấp LLM để tự fallback (chuyển đổi qua lại giữa OpenAI và Gemini).
3. **Database-backed Logs**: Nâng cấp từ JSONL thành lưu trữ SQLite để truy vấn phức tạp (SQL) dễ dàng hơn cho các thống kê hàng tháng mà script python thường khá vất vả xử lý dữ liệu lớn.

---

