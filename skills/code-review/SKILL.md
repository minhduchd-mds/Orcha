---
id: code-review
name: Code Review
description: Review code correctness, security, performance and maintainability.
version: 1.0.0
triggers: [review code, code review, kiểm tra code, debug, lỗi code, security review]
permissions:
  filesystem.read: auto
  project.search: auto
  filesystem.write: confirm
  shell.execute: confirm
---
# Objective
Phân tích mã nguồn theo bằng chứng trong project, ưu tiên lỗi có khả năng gây hỏng hệ thống và đưa ra thay đổi có thể kiểm chứng.

# Workflow
1. Xác định phạm vi, module và file liên quan.
2. Đọc context, dependency và luồng dữ liệu.
3. Tìm bug, edge case, security, performance và maintainability.
4. Xếp hạng P0, P1, P2 kèm bằng chứng.
5. Đề xuất patch nhỏ nhất an toàn.
6. Đề xuất regression test và tiêu chí PASS.

# Rules
- Không khẳng định đã chạy test nếu chưa có tool result.
- Không sửa file khi chưa được cấp quyền write.
- Ưu tiên structured tool thay vì shell command.
- Dẫn nguồn file/chunk khi có RAG context.

# Verification
- Mỗi lỗi quan trọng phải có file hoặc bằng chứng liên quan.
- Patch phải có cách kiểm tra regression.
- Không để lộ secret hoặc nội dung .env.
