# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

### Chủ đề đã chọn

**Trợ Lý Tra Cứu Đơn Hàng & Xử Lý Đổi Trả**

Trợ lý cần tra cứu dữ liệu đơn hàng theo mã đơn, kiểm tra trạng thái giao hàng,
đối chiếu điều kiện đổi trả và chỉ tạo yêu cầu đổi trả khi đơn hàng đủ điều kiện.
Kết quả của bước trước quyết định bước tiếp theo; Chatbot thuần không có bằng
chứng dữ liệu đơn hàng thực tế và không nên tự khẳng định đã tạo yêu cầu.

| Tiêu chí | Điểm (1-5) | Lý do đánh giá |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `5/5` | Cần tra cứu đơn hàng, kiểm tra trạng thái và đối chiếu điều kiện đổi trả theo từng tình huống. |
| 🛠️ **Tool Interaction** | `5/5` | Cần gọi tool để đọc dữ liệu đơn hàng/chính sách và có thể tạo yêu cầu đổi trả. |
| 🔀 **Dynamic Decision** | `5/5` | Kết quả tra cứu (đã giao, quá hạn, lỗi sản phẩm...) quyết định bước xử lý tiếp theo. |
| ⏳ **Long Horizon** | `4/5` | Một số yêu cầu cần 3-4 bước; chưa phải quy trình dài hạn nhiều ngày. |
| **TỔNG ĐIỂM FIT** | **19/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** |

## 🛠️ 2. TOOL SPECS (MỐC 2)

| Tool | Mục đích | Loại thao tác |
| :--- | :--- | :--- |
| `lookup_order_status(order_id)` | Tra cứu trạng thái, sản phẩm và ngày giao của đơn hàng | Read-only |
| `get_return_policy()` | Lấy chính sách và thời hạn đổi trả hiện hành | Read-only |
| `check_return_eligibility(order_id, reason)` | Kiểm tra đơn có đủ điều kiện đổi trả theo lý do | Read-only |
| `create_return_request(order_id, reason)` | Tạo yêu cầu đổi trả sau khi đã xác nhận đủ điều kiện | Ghi dữ liệu, cần xác nhận |

## ⚠️ 3. FAILURE MODES VÀ GUARDRAILS (ĐỊNH HƯỚNG MỐC 3)

| Trường hợp lỗi | Cách xử lý an toàn |
| :--- | :--- |
| Mã đơn không tồn tại hoặc sai định dạng | Báo lỗi và yêu cầu kiểm tra lại; không tự đoán mã đơn. |
| Thiếu mã đơn hoặc lý do đổi trả | Hỏi bổ sung trước khi gọi tool. |
| Đơn chưa giao, đã quá hạn hoặc không thuộc tài khoản | Thông báo không đủ điều kiện và nêu lý do. |
| Sản phẩm không nằm trong diện đổi trả | Từ chối lịch sự theo chính sách; không tạo yêu cầu. |
| Tool/database timeout hoặc dữ liệu thiếu | Cho phép thử lại; không bịa trạng thái đơn hàng. |
| Gọi tạo yêu cầu trước khi kiểm tra điều kiện | Chặn thao tác và yêu cầu chạy bước kiểm tra trước. |
| Yêu cầu nhiều đơn hoặc tool lỗi liên tục | Xử lý có giới hạn, áp dụng `MAX_ITERATIONS`, không lặp vô hạn. |

---

## 🔍 4. BASELINE CHATBOT — MỐC 2

Protocol: `system prompt + user message → một LLM call → final response`, không
gọi tool và không được nhúng dữ liệu đơn hàng vào prompt.

| Case | Dạng | Kỳ vọng đánh giá Baseline |
| :---: | :--- | :--- |
| 1 | Hướng dẫn chung | **Correct** nếu nêu quy trình chung, không bịa đơn cụ thể. |
| 2 | Hướng dẫn chung | **Correct** nếu liệt kê thông tin cần cung cấp. |
| 3 | Tra cứu + quyết định | **Safe fallback** nếu nói không có quyền truy cập đơn DH1001; **Hallucinated** nếu tự đoán trạng thái/đủ điều kiện. |
| 4 | Multi-step + hành động | **Safe fallback** nếu không khẳng định DH1002 và không nói đã gửi yêu cầu. |
| 5 | Input bẫy | **Safe fallback** nếu từ chối xác nhận hoàn tiền và yêu cầu mã đơn/lý do hợp lệ. |

### Kết quả chạy local

Đã chạy `python src/app.py` với `MockProvider`. Provider offline trả về câu giả lập
cho mỗi case, không gọi tool; vì vậy case 1-5 được ghi nhận là **chưa đủ chất lượng
để giải quyết nghiệp vụ** nhưng không có bằng chứng nó đã gọi tool hay tự tạo yêu cầu.
Khi chạy với API provider thật, Role 5 cần dán raw response vào bảng này và phân loại
từng case thành `correct`, `safe fallback` hoặc `hallucinated`.

### Kết luận Mốc 1

Bài toán đạt **19/20**, vì cần dữ liệu thực tế, nhiều bước suy luận và có thao tác
ghi dữ liệu cần kiểm soát. Câu hỏi kiến thức chung vẫn có thể dùng Chatbot path;
các yêu cầu tra cứu/đổi trả nhiều bước dùng ReAct Agent.
