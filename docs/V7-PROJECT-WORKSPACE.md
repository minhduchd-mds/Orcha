# v7 Project Agent Workspace

Project Workspace bổ sung lớp dự án bền vững trên Harness v7 hiện có.

## Mục tiêu
- Mỗi project có goal, task queue, progress và history riêng.
- Task có dependency; chỉ task đủ dependency mới trở thành `ready`.
- Write task có Approval Inbox, không tự vượt Permission Gate.
- Checkpoint lưu trạng thái task + approval đang chờ.
- Resume đọc lại project sau khi đóng/mở app; không tự replay side effect.

## API
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/<id>`
- `GET /api/projects/<id>/ready`
- `GET /api/projects/<id>/resume`
- `POST /api/projects/<id>/tasks`
- `POST /api/projects/<id>/tasks/<task_id>`
- `POST /api/projects/<id>/approvals`
- `POST /api/projects/<id>/approvals/<approval_id>`
- `POST /api/projects/<id>/checkpoint`

## Safety invariants
1. Resume không tự thực thi write action cũ.
2. Approval chỉ chuyển task trở lại `todo`; executor/Permission Engine vẫn là authority khi thực thi tool.
3. Project/task ID được sanitize chống path traversal.
4. File JSON dùng atomic replace để giảm nguy cơ hỏng dữ liệu khi app dừng đột ngột.
5. Project data nằm trong `KIMIK3_DATA_DIR/projects-v7`, không ghi vào source tree.

## UI
Menu `Dự án` mở workspace riêng gồm Project list, Task queue, progress, Approval Inbox, Checkpoint và Resume.
