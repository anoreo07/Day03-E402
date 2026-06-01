# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Lê Văn Quang]
- **Student ID**: [2A202600554]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong bài lab này, vai trò chính của tôi là **Lead Env/Data**: thiết lập môi trường chạy dự án, chuẩn bị dữ liệu giả lập cho bài toán E-commerce và hỗ trợ nhóm có nền tảng dữ liệu ổn định để các thành viên khác triển khai chatbot, tools, ReAct agent và telemetry. Ngoài phần môi trường/dữ liệu, tôi cũng bổ sung phần **thiết kế giao diện UI** cho demo "Trợ lý mua hàng E-commerce" để hệ thống không chỉ chạy ở mức backend mà còn có trải nghiệm giống một trợ lý ảo mua hàng thực tế.

- **Modules Implemented / Updated**:
  - `.env.example`: kiểm tra/cập nhật cấu hình mẫu để các thành viên có thể tạo file `.env` và chọn provider phù hợp.
  - `requirements.txt`: hỗ trợ bước cài dependencies bằng `pip install -r requirements.txt` và kiểm tra môi trường sau khi cài đặt.
  - `src/data/products.csv`: chuẩn bị dữ liệu giả lập cho E-commerce gồm khoảng 20 sản phẩm, nhiều danh mục, giá, tồn kho, thuế, trọng lượng giao hàng và mã coupon.
  - `src/data/__init__.py`: bổ sung loader đọc `products.csv`, ép kiểu dữ liệu sản phẩm/coupon để webapp và tool có thể dùng dữ liệu ổn định.
  - `README.md`: hỗ trợ phần hướng dẫn setup nếu cần cập nhật, đặc biệt là luồng tạo `.env`, cài dependencies và chạy demo.
  - `webapp/app.py`, `webapp/templates/index.html`, `webapp/static/style.css`, `webapp/static/app.js`: bổ sung phần thiết kế giao diện "MiniMart AI Shopping Assistant" theo hướng chat-first personal shopper, có chat tư vấn, gợi ý sản phẩm, giỏ hàng, coupon, order summary và đặt hàng giả lập.

- **Code Highlights**:

```python
def check_stock(product_id: str, inventory: Dict[str, Any]) -> Dict[str, Any]:
    qty = get_stock_level(product_id, inventory)
    return {"available": qty > 0, "quantity": qty}
```

Đoạn code trên cho thấy vì sao dữ liệu giả lập cần có schema ổn định: tool chỉ có thể trả về observation đúng nếu dữ liệu tồn kho được chuẩn hóa và có trường rõ ràng.

```python
def get_discount(...):
    if coupon_code and coupons and coupon_code in coupons:
        ...
    elif coupon_code:
        digits = "".join([c for c in str(coupon_code) if c.isdigit()])
        if digits:
            val = float(digits)
            discount = base_price * (val / 100.0)
```

Tool giảm giá có fallback xử lý coupon dạng `SUMMER10`, `HEAD20`, nên khi tôi chuẩn bị dữ liệu sản phẩm/coupon trong CSV, hệ thống có thể demo luồng mua hàng và áp mã giảm giá ngay cả khi chưa có database thật.

```csv
product_id,name,category,price_usd,stock_qty,tax_rate,shipping_weight_kg,coupon_code
P001,Wireless Earbuds,Electronics,49.99,120,0.10,0.05,SUMMER10
P007,Noise-Cancelling Headphones,Electronics,129.90,45,0.10,0.30,HEAD20
```

Đây là ví dụ dữ liệu giả lập tôi chuẩn bị để agent/webapp có thể kiểm tra giá, tồn kho, coupon, thuế và phí vận chuyển trong cùng một workflow.

- **Documentation / Integration with ReAct Loop**:
  - Các tool được thiết kế để phù hợp với chu trình `Thought -> Action -> Observation -> Final Answer`.
  - Ví dụ, khi người dùng hỏi "Tai nghe chống ồn còn hàng không và tổng tiền sau giảm giá là bao nhiêu?", agent có thể:
    1. dùng `check_stock` để kiểm tra tồn kho,
    2. dùng `get_price` để lấy giá,
    3. dùng `get_discount` để áp coupon,
    4. dùng `calc_tax` và `calc_shipping` để tính tổng,
    5. tổng hợp kết quả thành câu trả lời cuối.
  - Giao diện webapp giúp minh họa trực quan chu trình này bằng các phần: chat tư vấn, gợi ý sản phẩm, giỏ hàng, coupon, order summary và đặt hàng giả lập. Phần UI được thiết kế theo hướng **chat-first personal shopper**, để người dùng cảm thấy đang tương tác với một trợ lý mua hàng thật thay vì chỉ nhìn output dạng terminal.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  Trong quá trình chuẩn bị môi trường và dữ liệu, một lỗi điển hình là agent/tool dễ bị sai định dạng dữ liệu khi làm việc với sản phẩm. Dữ liệu sản phẩm trong CSV dùng các trường như `price_usd`, `stock_qty`, `coupon_code`, trong khi một số tool ban đầu thường giả định dữ liệu có trường đơn giản như `price`, `stock` hoặc `quantity`. Nếu không xử lý defensive, agent có thể trả về giá `0.0`, tồn kho `0`, hoặc không áp được coupon dù sản phẩm thật sự tồn tại.

- **Log Source**:
  Hệ thống logging nằm ở `src/telemetry/logger.py`, ghi sự kiện dạng JSON vào thư mục `logs/`:

```python
payload = {
    "timestamp": datetime.utcnow().isoformat(),
    "event": event_type,
    "data": data
}
self.logger.info(json.dumps(payload))
```

Ví dụ trace kỳ vọng khi debug agent:

```json
{"event":"AGENT_START","data":{"input":"Check stock and price for P007","model":"local"}}
{"event":"TOOL_CALL","data":{"tool":"check_stock","args":{"product_id":"P007"}}}
{"event":"OBSERVATION","data":{"available":true,"quantity":45}}
{"event":"TOOL_CALL","data":{"tool":"get_price","args":{"product_id":"P007"}}}
{"event":"OBSERVATION","data":{"price":129.9,"currency":"USD"}}
```

- **Diagnosis**:
  Nguyên nhân chính không phải do LLM "không biết" câu trả lời, mà do contract giữa dữ liệu, tool và prompt chưa đủ chặt. Agent chỉ có thể suy luận đúng nếu `Observation` phản ánh đúng trạng thái môi trường. Khi tool trả về sai vì lệch schema, LLM sẽ tiếp tục lập luận trên thông tin sai và tạo câu trả lời cuối không đáng tin.

- **Solution**:
  Tôi xử lý theo hướng chuẩn hóa dữ liệu và làm tool robust hơn:
  - Chuẩn bị `products.csv` có các trường cần thiết cho toàn bộ bài toán E-commerce: mã sản phẩm, tên, danh mục, giá, tồn kho, thuế, trọng lượng giao hàng và coupon.
  - `get_price` chấp nhận cả `price` và `price_usd`.
  - `check_stock` chấp nhận nhiều tên trường tồn kho: `stock`, `quantity`, `qty`, `stock_qty`.
  - `get_discount` có fallback đọc coupon từ CSV và suy luận phần trăm từ mã coupon có số.
  - `src/data/__init__.py` ép kiểu dữ liệu ngay khi load CSV để giảm lỗi kiểu dữ liệu ở các bước sau.
  - Kiểm tra môi trường bằng cách cài dependencies và chạy các lệnh kiểm tra cơ bản để đảm bảo các thành viên khác có thể tiếp tục implement chatbot/tools/agent mà không bị lỗi setup ban đầu.

Kết quả là tool trả về observation ổn định hơn, giúp agent có cơ sở tốt hơn để tiếp tục chu trình ReAct.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: `Thought` block giúp agent tách quá trình giải bài toán thành nhiều bước nhỏ thay vì trả lời ngay. Với bài toán mua hàng, chatbot thường đưa ra câu trả lời chung chung như "sản phẩm này còn hàng" hoặc "bạn có thể dùng coupon", nhưng không thật sự kiểm chứng. ReAct Agent có thể nghĩ: cần kiểm tra tồn kho trước, sau đó lấy giá, áp mã giảm giá, tính thuế/phí ship, rồi mới trả lời. Điều này làm câu trả lời có căn cứ hơn.

2. **Reliability**: Agent không phải lúc nào cũng tốt hơn chatbot. Với câu hỏi đơn giản như "Trợ lý này làm gì?", chatbot trực tiếp nhanh và ít rủi ro hơn. Agent có thể perform tệ hơn khi prompt/tool spec không rõ, khi parser đọc sai `Action`, hoặc khi model gọi tool với argument không đúng định dạng. Ngoài ra, agent tốn nhiều bước hơn nên latency và chi phí cao hơn.

3. **Observation**: `Observation` là điểm khác biệt quan trọng nhất. Nó biến câu trả lời từ suy đoán thành phản hồi dựa trên môi trường. Ví dụ, nếu `check_stock(P007)` trả về `{"available": true, "quantity": 45}`, agent có thể tự tin tư vấn tai nghe còn hàng. Nếu observation báo hết hàng, agent có thể chuyển sang gợi ý sản phẩm thay thế. Như vậy, feedback từ môi trường điều khiển bước tiếp theo của agent.

Nhìn chung, chatbot phù hợp với câu hỏi ngắn, ít trạng thái và không cần hành động. ReAct Agent phù hợp hơn với workflow nhiều bước như E-commerce: tư vấn, kiểm tra dữ liệu, tính toán, ra quyết định và mô phỏng đặt hàng.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Tách tool execution thành service riêng hoặc job queue bất đồng bộ để nhiều người dùng có thể chat và đặt hàng giả lập cùng lúc.
  - Chuẩn hóa schema tool bằng Pydantic hoặc JSON Schema để LLM biết chính xác input/output của từng tool.
  - Khi số lượng tool tăng, dùng tool router hoặc retrieval-based tool selection để agent chỉ thấy các tool liên quan.

- **Safety**:
  - Thêm guardrails cho số vòng lặp tối đa, timeout tool call và validate argument trước khi thực thi.
  - Với checkout thật, cần bước xác nhận của người dùng trước khi tạo đơn hàng hoặc thanh toán.
  - Ghi audit log cho các hành động quan trọng như áp coupon, thay đổi số lượng và checkout.

- **Performance**:
  - Cache dữ liệu sản phẩm/coupon để giảm đọc CSV nhiều lần.
  - Dùng streaming response cho chat để người dùng thấy phản hồi nhanh hơn.
  - Tách phần tính giá deterministic khỏi LLM để giảm token và tránh hallucination.

- **Production Direction**:
  - Nâng cấp từ prototype sang workflow graph như LangGraph: node tư vấn, node tìm sản phẩm, node tính giá, node xác nhận đặt hàng.
  - Kết hợp RAG trên catalog sản phẩm thật để trợ lý có thể trả lời sâu hơn về mô tả, review và chính sách đổi trả.
  - Thêm monitoring dashboard cho latency, tool success rate, invalid action rate và cost per conversation.

---

> [!NOTE]
> Trước khi nộp, đổi tên file thành `REPORT_LE_VAN_QUANG.md` hoặc theo đúng quy định đặt tên của giảng viên.
