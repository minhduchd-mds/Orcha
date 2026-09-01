---
id: computer-control
name: Computer Control
description: Plan and execute local desktop actions through permission-gated MCP tools.
version: 1.0.0
triggers: [điều khiển máy tính, mở ứng dụng, thao tác desktop, computer control, click, nhập liệu]
permissions:
  computer.read: auto
  computer.focus: auto
  computer.input: confirm
  computer.launch: confirm
  filesystem.write: confirm
  shell.execute: deny
---
# Objective
Điều khiển máy tính theo structured tools, ưu tiên UI Automation/accessibility tree và API ứng dụng trước tọa độ màn hình.

# Workflow
1. Đọc trạng thái desktop và cửa sổ đang mở.
2. Lập kế hoạch hành động nhỏ, có thể kiểm tra từng bước.
3. Dùng read-only tool để xác nhận target.
4. Xin quyền trước hành động nhập liệu, launch hoặc thay đổi dữ liệu.
5. Thực thi từng action và đọc observation sau mỗi bước.
6. Dừng khi kết quả không khớp kỳ vọng và báo lỗi thay vì click mù.

# Rules
- Không dùng shell.execute trong skill này.
- Không tự động gửi form, email, thanh toán hoặc xóa dữ liệu.
- Không nhập secret hoặc password nếu người dùng chưa trực tiếp yêu cầu tại thời điểm thao tác.
- Ưu tiên element id/name/role; tọa độ chỉ là fallback.

# Verification
- Cửa sổ/element đích đúng trước khi action.
- Mỗi write action phải có permission decision.
- Có observation sau action và trạng thái cuối.
