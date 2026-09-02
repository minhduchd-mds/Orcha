---
name: orcha-frontend-design
description: Thiết kế và review frontend có chủ đích, tránh giao diện template/AI-generic; ưu tiên hierarchy, typography, interaction, accessibility và self-critique.
version: 1.0.0
category: design
triggers:
  - frontend design
  - nâng cấp ui
  - redesign
  - giao diện
  - ui review
permissions:
  project.search: auto
  filesystem.read: auto
  filesystem.write: confirm
  figma.write: confirm
---

# Orcha Frontend Design

## Mục tiêu
Tạo giao diện có bản sắc riêng theo đúng ngữ cảnh sản phẩm thay vì dùng công thức dashboard/AI mặc định. Đây là skill được viết độc lập cho Orcha; nguồn tham khảo kiến trúc thiết kế gồm Anthropic Claude Code `frontend-design` skill, nhưng không sao chép nội dung hay tài sản giao diện.

## Quy trình
1. Xác định đúng đối tượng, công việc chính và trạng thái quan trọng của màn hình.
2. Chốt một hệ token gọn: surface, line, text, accent, semantic status, radius, spacing, type scale.
3. Chọn một signature element duy nhất; phần còn lại giữ kỷ luật và yên tĩnh.
4. Dùng hierarchy thật: heading, section, divider, label phải phản ánh cấu trúc nội dung chứ không chỉ trang trí.
5. Với toolbar dày đặc, ưu tiên icon có `aria-label` + tooltip; text chỉ giữ lại khi ý nghĩa không thể suy ra nhanh bằng icon.
6. Native browser `prompt()`/`alert()` không dùng cho flow sản phẩm. Dùng dialog/popup có label, validation, error state, cancel/confirm rõ ràng.
7. Inspector/panel phụ phải đóng/mở được và nhớ trạng thái nếu phù hợp.
8. Motion có mục đích, ngắn, hỗ trợ reduced-motion; không rải hiệu ứng trang trí.
9. Responsive phải giữ hierarchy, không chỉ co kích thước.
10. Trước khi hoàn tất, tự critique một lượt: bỏ chi tiết thừa, kiểm tra focus-visible, keyboard, empty/error/loading states và contrast heuristic.

## Verification
- Không còn browser-native prompt trong flow đã sửa.
- Mọi icon-only control có accessible name.
- Panel phụ có close/reopen path.
- Keyboard focus nhìn thấy được.
- Reduced motion được tôn trọng.
- Copy dùng từ phía người dùng, không dùng thuật ngữ implementation làm label chính.
- Không tuyên bố WCAG compliance chỉ dựa trên screenshot.

## Attribution
Architecture/design reference: Anthropic `claude-code/plugins/frontend-design` (repository license terms apply to upstream). Orcha implementation and wording in this file are independently authored.
