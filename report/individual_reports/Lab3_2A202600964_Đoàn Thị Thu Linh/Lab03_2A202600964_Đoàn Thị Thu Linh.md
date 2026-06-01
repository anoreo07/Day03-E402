# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đoàn Thị Thu Linh
- **Student ID**: 2A202600964
- **Role**: Lead Baseline & Testing
- **Date**: 2026-06-01

---

# I. Technical Contribution (15 Points)

## Overview

Trong dự án Lab 3, tôi đảm nhận vai trò **Trưởng Baseline & Testing**, chịu trách nhiệm xây dựng chatbot baseline không sử dụng ReAct, thiết kế bộ test cases để đánh giá hệ thống và thực hiện benchmark giữa Chatbot và ReAct Agent.

Mục tiêu chính là xây dựng một hệ thống chatbot đơn giản sử dụng cơ chế keyword-dispatch nhằm làm đường cơ sở (baseline) để so sánh với Agent sử dụng kỹ thuật Reasoning + Acting.

## Modules Implemented

### 1. Baseline Chatbot

- Xử lý truy vấn bằng keyword matching.
- Gọi trực tiếp các tools của hệ thống.
- Không sử dụng Thought–Action–Observation loop.
- Hỗ trợ kiểm tra tồn kho, giá, coupon, shipping, tax và tổng đơn hàng.

### 2. Integration Test Suite

Thiết kế 10 test cases:

#### Single-Step Test Cases
1. Kiểm tra tồn kho sản phẩm.
2. Truy vấn giá sản phẩm.
3. Áp dụng coupon giảm giá.
4. Tính phí vận chuyển.
5. Hiển thị danh sách sản phẩm.

#### Multi-Step Test Cases
6. Tính tổng đơn hàng có coupon.
7. Tính tổng đơn hàng không coupon.
8. Xử lý trường hợp hết hàng.
9. Chuỗi Discount → Tax.
10. Shipping theo trọng lượng và số lượng.

### 3. Chatbot vs Agent Benchmark

Thực hiện benchmark giữa Baseline Chatbot và ReAct Agent trên các tình huống:
- Stock Query
- Price Query
- Coupon Query
- Multi-step Order Query
- Ambiguous Recommendation Query

### 4. Automated Test Runner

Xây dựng hệ thống chạy test tự động:
- Chạy toàn bộ test suite.
- Thống kê PASS/FAIL.
- Sinh báo cáo Markdown.
- So sánh Chatbot và Agent.

---

# II. Debugging Case Study (10 Points)

## Problem Description

Chatbot ban đầu phân loại sai các truy vấn chứa nhiều intent.

Ví dụ:

"Tôi muốn mua 1 cái P007 dùng mã HEAD20, tổng hết bao nhiêu?"

Hệ thống chỉ trả về giá sản phẩm thay vì tính tổng đơn hàng.

## Diagnosis

Nguyên nhân là do cơ chế keyword matching ưu tiên intent giá sản phẩm trước intent tính tổng đơn hàng.

## Solution

Điều chỉnh thứ tự ưu tiên:

Full Order → Stock → Price → Discount → Shipping → Tax

Sau khi sửa, chatbot có thể xử lý đúng luồng:

Stock Check → Discount → Tax → Shipping → Grand Total

## Outcome

- TC-M1 PASS
- TC-M2 PASS
- Multi-step workflow hoạt động ổn định hơn.
- Kết quả khớp với dữ liệu từ tool.

---

# III. Personal Insights: Chatbot vs ReAct (10 Points)

## 1. Reasoning

Chatbot:

Question → Intent → Tool → Answer

Agent:

Question → Thought → Action → Observation → Thought → Final Answer

Thought giúp Agent lập kế hoạch và reasoning đa bước tốt hơn.

## 2. Reliability

Chatbot phù hợp với:
- Truy vấn đơn giản.
- FAQ.
- Chi phí thấp.

Agent phù hợp với:
- Tính toán nhiều bước.
- Tool calling.
- Truy vấn phức tạp.

## 3. Observation

Observation giúp Agent:
- Điều chỉnh kế hoạch.
- Tự sửa lỗi.
- Dừng quy trình khi không cần thực hiện bước tiếp theo.

Đây là điểm khác biệt quan trọng giữa Agent và chatbot truyền thống.

---

# IV. Future Improvements (5 Points)

## Scalability

- Asynchronous tool execution.
- Queue-based architecture.
- Hỗ trợ nhiều người dùng đồng thời.

## Safety

- Input validation.
- Coupon validation.
- Rate limiting.
- Supervisor Agent.

## Performance

- Vector Database (FAISS, ChromaDB, Pinecone).
- Dynamic Tool Selection.
- Cache dữ liệu sản phẩm và tồn kho.

---

# Conclusion

Trong Lab 3, tôi đảm nhận vai trò Lead Baseline & Testing, chịu trách nhiệm xây dựng Baseline Chatbot, thiết kế bộ kiểm thử gồm 10 test cases và triển khai benchmark giữa Chatbot và ReAct Agent.

Kết quả cho thấy chatbot hoạt động tốt với các truy vấn đơn giản nhưng gặp hạn chế ở các bài toán reasoning đa bước. ReAct Agent vượt trội nhờ khả năng lập kế hoạch, sử dụng tool và phản hồi dựa trên observation.

Bài lab giúp tôi hiểu rõ hơn về Agentic AI, quy trình kiểm thử hệ thống AI và sự khác biệt giữa chatbot truyền thống với ReAct Agent.
