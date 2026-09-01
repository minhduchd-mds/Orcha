# Batch 5 — Claude-style Workspace + Skill Library + Workflow UX

Batch 5 giữ hai không gian chính **Trò chuyện** và **Công việc**, nhưng giảm nhiễu thị giác, tăng vùng nội dung và chuyển các khả năng kỹ thuật sang sidebar/inspector hỗ trợ.

## 10 hạng mục

1. Claude-inspired calm three-column workspace (không sao chép UI).
2. Sidebar nhẹ: Trò chuyện, Công việc + Kỹ năng/Knowledge/MCP/Model.
3. Chat composer tối giản, Skill/Agent đặt cạnh input.
4. Inspector Context/KII/Agent/Timeline/MCP/Sources gọn hơn.
5. Skill Library có filter Active/Disabled/Draft.
6. Skill CRUD: create/update/delete/duplicate/enable/disable.
7. Skill version history backend; mỗi lần lưu tạo snapshot trước đó.
8. Skill Editor mở rộng category, rules, verification và permission defaults.
9. Workflow Canvas với step cards, drag/drop reorder, add/delete/duplicate workflow.
10. Workflow templates/runtime view + CI contract cho Windows/macOS.

## Skill storage

User-created skills tiếp tục dùng cấu trúc portable:

```text
skills/<skill-id>/
  SKILL.md
  .skill-meta.json
  .versions/
    v1.md
    v2.md
```

`SKILL.md` vẫn là định dạng thực thi chính. `.skill-meta.json` chỉ giữ metadata UI/status/version.

## Workflow storage

Workflow được lưu local tại `data/workflows.json`. Step có stable `id`, `name`, `type`, `mode`, `instruction`, `enabled`. Reorder chỉ thay đổi thứ tự ID, không sửa nội dung step.

## UX principles

- User intent trước implementation detail.
- Auto là mode mặc định; Fast/Smart/Deep nằm trong dropdown.
- Tool/MCP/Context nằm Inspector thay vì chiếm vùng chat.
- Skill Library là nơi quản trị; Skill Picker trong chat chỉ là shortcut.
- Workflow Builder hiển thị luồng, Runtime tách riêng output.
- Permission Gate không bị loại bỏ khi đơn giản hóa giao diện.
