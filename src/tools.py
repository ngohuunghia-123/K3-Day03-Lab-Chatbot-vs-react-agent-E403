"""Các tool deterministic cho trợ lý đơn hàng và đổi trả.

Mốc 2 tập trung vào tool contract: input rõ ràng, output có cấu trúc và lỗi
nghiệp vụ được trả về như dữ liệu để Agent xử lý, không làm crash chương trình.
"""

from datetime import date


# Dữ liệu giả lập deterministic cho lab; Mốc 3 có thể thay bằng database/API.
ORDERS = {
    "DH1001": {
        "status": "Đã giao",
        "product": "Tai nghe Bluetooth X1",
        "delivered_on": "2026-07-20",
        "returnable": True,
    },
    "DH1002": {
        "status": "Đang giao",
        "product": "Bàn phím cơ K2",
        "delivered_on": None,
        "returnable": False,
    },
    "DH1003": {
        "status": "Đã giao",
        "product": "Áo khoác mùa đông",
        "delivered_on": "2026-05-01",
        "returnable": True,
    },
    "DH1004": {
        "status": "Đã giao",
        "product": "Mỹ phẩm dưỡng da",
        "delivered_on": "2026-07-24",
        "returnable": False,
    },
}

RETURN_WINDOW_DAYS = 30
# Mốc ngày cố định giúp kết quả lab không thay đổi theo ngày chạy thực tế.
LAB_TODAY = date(2026, 7, 28)


def _normalize_order_id(order_id: str) -> str:
    """Chuẩn hóa mã đơn và báo lỗi input dưới dạng ValueError nội bộ."""
    if not isinstance(order_id, str) or not order_id.strip():
        raise ValueError("Mã đơn hàng không được để trống.")
    normalized = order_id.strip().upper()
    if not normalized.startswith("DH") or not normalized[2:].isdigit():
        raise ValueError("Mã đơn hàng phải có dạng DH + chữ số, ví dụ DH1001.")
    return normalized


def lookup_order_status(order_id: str) -> str:
    """Tra cứu trạng thái đơn hàng.

    Args:
        order_id: Mã đơn dạng ``DH1001``.
    Returns:
        Chuỗi kết quả thành công hoặc bắt đầu bằng ``LỖI:`` khi input/dữ liệu
        không hợp lệ. Tool chỉ đọc dữ liệu và không có side effect.
    """
    try:
        normalized = _normalize_order_id(order_id)
        order = ORDERS.get(normalized)
        if order is None:
            return f"LỖI: Không tìm thấy đơn hàng '{normalized}'."
        delivered = order["delivered_on"] or "chưa giao"
        return (
            f"Đơn {normalized}: trạng thái={order['status']}; "
            f"sản phẩm={order['product']}; ngày giao={delivered}."
        )
    except (TypeError, ValueError) as exc:
        return f"LỖI: {exc}"


def get_return_policy() -> str:
    """Lấy chính sách đổi trả hiện hành; tool chỉ đọc dữ liệu."""
    return (
        "Chính sách đổi trả: sản phẩm được đổi trả trong vòng 30 ngày kể từ ngày "
        "giao, phải còn thuộc diện hỗ trợ và cần nêu rõ lý do. Đơn chưa giao hoặc "
        "sản phẩm không thuộc diện hỗ trợ không được tạo yêu cầu."
    )


def check_return_eligibility(order_id: str, reason: str) -> str:
    """Kiểm tra một đơn có đủ điều kiện đổi trả không.

    Args:
        order_id: Mã đơn dạng ``DH1001``.
        reason: Lý do đổi trả, ví dụ ``sản phẩm bị lỗi``.
    Returns:
        Kết quả đủ/không đủ điều kiện hoặc chuỗi ``LỖI:``; không tạo yêu cầu.
    """
    try:
        normalized = _normalize_order_id(order_id)
        if not isinstance(reason, str) or not reason.strip():
            return "LỖI: Vui lòng cung cấp lý do đổi trả."
        order = ORDERS.get(normalized)
        if order is None:
            return f"LỖI: Không tìm thấy đơn hàng '{normalized}'."
        if order["status"] != "Đã giao":
            return f"KHÔNG ĐỦ ĐIỀU KIỆN: Đơn {normalized} chưa được giao."
        if not order["returnable"]:
            return f"KHÔNG ĐỦ ĐIỀU KIỆN: Sản phẩm '{order['product']}' không thuộc diện đổi trả."
        delivered_on = date.fromisoformat(order["delivered_on"])
        days_since_delivery = (LAB_TODAY - delivered_on).days
        if days_since_delivery > RETURN_WINDOW_DAYS:
            return (
                f"KHÔNG ĐỦ ĐIỀU KIỆN: Đơn {normalized} đã quá thời hạn "
                f"{RETURN_WINDOW_DAYS} ngày ({days_since_delivery} ngày)."
            )
        return (
            f"ĐỦ ĐIỀU KIỆN: Đơn {normalized} có thể đổi trả với lý do "
            f"'{reason.strip()}'."
        )
    except (TypeError, ValueError) as exc:
        return f"LỖI: {exc}"


def create_return_request(order_id: str, reason: str) -> str:
    """Tạo yêu cầu đổi trả sau khi đã kiểm tra điều kiện.

    Tool này mô phỏng thao tác ghi dữ liệu. Trong ứng dụng thật cần xác nhận
    cuối cùng của người dùng trước khi gọi và cần idempotency để tránh tạo trùng.
    """
    eligibility = check_return_eligibility(order_id, reason)
    if not eligibility.startswith("ĐỦ ĐIỀU KIỆN:"):
        return f"LỖI: Chưa thể tạo yêu cầu. {eligibility}"
    normalized = _normalize_order_id(order_id)
    return f"Đã tạo yêu cầu đổi trả RR-{normalized} cho đơn {normalized}."


AVAILABLE_TOOLS = {
    "lookup_order_status": lookup_order_status,
    "get_return_policy": get_return_policy,
    "check_return_eligibility": check_return_eligibility,
    "create_return_request": create_return_request,
}
