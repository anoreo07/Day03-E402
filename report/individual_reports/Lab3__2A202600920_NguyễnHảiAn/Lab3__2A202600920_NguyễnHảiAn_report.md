# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Hải An
- **Student ID**: 2A202600920
- **Date**: June 1, 2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- **Modules Implemented**:
  - `src/tools/check_stock.py`
  - `src/tools/get_price.py`
  - `src/tools/get_discount.py`
  - `src/tools/calc_shipping.py`
  - `src/tools/calc_tax.py`
  - `src/tools/__init__.py`
- **Code Highlights**:
  - Thiết kế bộ tool e-commerce cơ bản và chuẩn hóa interface tool cho ReAct agent.
  - Triển khai docstring chi tiết, ví dụ sử dụng và logic trả về định dạng JSON/serializable cho từng tool.
  - Đảm bảo `src/tools/__init__.py` export đúng bộ hàm cần thiết để cả chatbot và agent có thể import chung.
  - Viết các tool theo nguyên tắc defensive programming: chấp nhận nhiều dạng input, trả về giá trị an toàn khi dữ liệu thiếu.
- **Documentation**:
  - Mỗi file tool có docstring mở đầu giải thích đầu vào, đầu ra, và ví dụ sử dụng.
  - `src/tools/__init__.py` ghi chú mục đích chung của package và liệt kê các hàm export.
  - Các công cụ này được sử dụng trong `src/run_agent.py` để xây dựng danh sách tool cho ReAct agent và trong `src/app_chat.py` để hiển thị thông tin tool.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Agent và Chatbot trả về kết quả giảm giá không nhất quán khi input mã coupon như `HEAD20` hoặc `SUMMER10`.
- **Log Source**: `logs/` (nếu có) hoặc kiểm tra trực tiếp qua cấu trúc tool function trong `src/tools/get_discount.py`.
- **Diagnosis**:
  - Vấn đề không nằm ở parser ReAct mà nằm ở cách `get_discount()` xử lý `coupon_code`.
  - Nếu `coupon_code` không nằm trong `coupons` map, hàm fallback sử dụng `digits = ''.join([c for c in str(coupon_code) if c.isdigit()])` và áp dụng phần trăm dựa trên số tìm được.
  - Cách này dễ đúng với các mã kiểu `HEAD20` nhưng không an toàn với các mã phức tạp hoặc token không biểu thị phần trăm.
  - Đồng thời, agent có thể không được cung cấp `coupons` rule rõ ràng khi khởi tạo tool, dẫn đến lệ thuộc vào fallback logic.
- **Solution**:
  - Cập nhật `get_discount()` để ưu tiên nhận `coupons` dictionary từ nơi gọi tool và chỉ dùng fallback khi rõ ràng cần thiết.
  - Thêm tham số `products` và `products_csv_path` để đọc mã coupon mặc định từ `products.csv` khi cần.
  - Đưa docstring hướng dẫn rõ ràng rằng `coupon_code` phải được truyền đúng nếu muốn áp dụng giảm giá chính xác.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1. **Reasoning**: `Thought` block giúp agent tách bước suy nghĩ và tính toán, từ đó dễ kiểm tra hơn từng bước `Action` và `Observation`. Với tool-based ReAct, agent có thể đưa ra các bước trung gian như kiểm tra tồn kho, lấy giá, áp mã giảm giá, tính thuế, thay vì chỉ trả lời một lần.
2. **Reliability**: Agent có thể hoạt động kém hơn khi tool spec không đủ rõ ràng hoặc khi prompt hệ thống không truyền tải đủ bối cảnh dữ liệu. Trong repo hiện tại, Chatbot đôi khi có lợi thế vì hệ thống prompt trực tiếp chứa product catalog, còn agent phải dựa vào hệ thống prompt và công cụ.
3. **Observation**: Môi trường feedback từ tool (`Observation`) giúp agent học được kết quả của mỗi hàm gọi. Nếu `get_discount()` trả về chi tiết rõ ràng, agent có thể dùng quan sát đó để tiếp tục tính toán chính xác.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**:
  - Tách tool execution thành microservice hoặc HTTP API để agent có thể gọi bất kỳ tool nào mà không cần import trực tiếp.
  - Dùng asynchronous queue cho các cuộc gọi tool nặng và caching kết quả giá trị.
- **Safety**:
  - Thêm validation layer cho input tool để ngăn agent gọi tool với các tham số không hợp lệ.
  - Thêm cơ chế `tool guard` để kiểm tra ràng buộc giá trị trả về và tránh kết quả cẩu thả.
- **Performance**:
  - Lưu trữ product catalog vào cache bằng Pandas hoặc database để truy xuất giá nhanh hơn.
  - Áp dụng `vector DB` hoặc `search index` cho các tool trợ giúp tìm sản phẩm lớn hơn.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_2A202600920_NguyễnHảiAn.md` and placing it in this folder.
