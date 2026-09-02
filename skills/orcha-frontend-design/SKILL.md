---
name: orcha-frontend-design
description: Thiết kế và review frontend Orcha theo visual baseline hiện hữu; Claude frontend-design chỉ được nâng chất lượng, không được làm lệch style sản phẩm.
version: 1.1.0
category: design
triggers:
  - frontend design
  - nâng cấp ui
  - redesign
  - giao diện
  - ui review
  - code frontend
permissions:
  project.search: auto
  filesystem.read: auto
  filesystem.write: confirm
  figma.write: confirm
---

# Orcha Frontend Design

## Mục tiêu
Tạo và sửa giao diện Orcha mà không làm mất visual identity đã hình thành từ UI Kimi trước đây. Repo không có một tài liệu "Kimi Style Rule" chính thức riêng; vì vậy baseline bắt buộc được rút trực tiếp từ style đang tồn tại trong `studio/styles.css` và được chuẩn hóa thành Orcha UI Contract.

Nguồn tham khảo chất lượng thứ hai là Anthropic Claude Code `frontend-design`. Các nguyên tắc Claude được dùng cho hierarchy, typography, structure, restraint, copy, responsive, accessibility và self-critique; **không được tự đổi palette, radius, density, layout language hoặc icon language của Orcha**.

## Thứ tự ưu tiên bắt buộc
1. Yêu cầu/brief cụ thể của người dùng.
2. **Orcha Visual Baseline (Kimi-derived)** trong `studio/styles.css` và `docs/ORCHA-UI-CONTRACT.md`.
3. Component/pattern hiện hữu của màn hình đang sửa.
4. Claude frontend-design quality rules.
5. Ý tưởng thẩm mỹ mới chỉ được dùng nếu không xung đột 1–4.

Nếu Claude rule hoặc một reference ngoài làm giao diện lệch visual baseline của Orcha, **Orcha baseline thắng**.

## Orcha Visual Baseline — bắt buộc
- Dark warm-neutral canvas/panel/sidebar.
- Accent terracotta hiện hữu; semantic success/warning/danger giữ hệ màu hiện tại.
- Typography mặc định `Inter, Segoe UI, system-ui, -apple-system, sans-serif` trừ khi brief yêu cầu khác.
- Radius nhỏ-vừa, panel/card yên tĩnh; không tự chuyển sang glassmorphism, neon, cream editorial, newspaper hoặc AI-template aesthetic.
- Layout desktop ưu tiên workspace nhiều cột; responsive phải tái bố trí chứ không chỉ scale nhỏ.
- Mọi style extension phải dùng token semantic đã có; không tạo palette thứ hai song song.

## Icon Rule — bắt buộc
- **Outline only** cho icon product UI.
- SVG phải `fill="none"`, `stroke="currentColor"`, stroke mặc định `1.8`, round cap/join.
- Cùng viewBox 24×24 và visual weight nhất quán.
- Không dùng emoji/Unicode glyph làm icon hệ thống mới.
- Icon-only control bắt buộc có `aria-label` và tooltip/title.
- Icon + text chỉ dùng khi label vẫn cần để giảm ambiguity; icon không thay đổi nghĩa action.
- Icon destructive vẫn outline; danger được thể hiện bằng semantic color, không đổi sang filled icon.

## Brand/Copy Rule — bắt buộc
- Product-facing text chỉ dùng tên **Orcha**.
- Không được hiển thị `Kimi`, `KimiK3`, `KimiK3-Lite` trong chat, welcome, permission, dialog, toast, error, title hoặc assistant metadata.
- Tên lịch sử chỉ được tồn tại trong compatibility code, migration variable/model id, changelog/license/release history có ngữ cảnh rõ ràng.
- Copy viết từ phía người dùng, active voice, sentence case; cùng một action phải giữ cùng một tên xuyên suốt flow.

## Quy trình
1. Xác định màn hình, người dùng và công việc chính.
2. Đọc `studio/styles.css`, `studio/ui-foundation.css` và `docs/ORCHA-UI-CONTRACT.md` trước khi tạo style mới.
3. Giữ baseline palette/type/radius/density; chỉ chọn một signature change nếu brief thực sự cần.
4. Kiểm tra hierarchy và structure theo Claude frontend-design nhưng không thay visual language.
5. Dùng outline icon registry; không thêm glyph/emoji rời rạc.
6. Native browser `prompt()`/`alert()` không dùng cho product flow. Dùng dialog có label, validation, error, cancel/confirm rõ ràng.
7. Inspector/panel phụ phải đóng/mở được và nhớ trạng thái nếu phù hợp.
8. Motion có mục đích, ngắn, hỗ trợ reduced-motion.
9. Responsive giữ hierarchy và task priority.
10. Trước khi hoàn tất tự critique: bỏ trang trí thừa, kiểm tra focus-visible, keyboard, empty/error/loading, copy consistency và brand consistency.

## Verification
- Visual token mới không tạo palette song song với baseline.
- Không có emoji/Unicode làm icon UI mới; icon product là outline SVG.
- Mọi icon-only control có accessible name.
- Product-facing chat/UI không còn Kimi/KimiK3/KimiK3-Lite.
- Không còn browser-native prompt trong flow đã sửa.
- Panel phụ có close/reopen path.
- Keyboard focus nhìn thấy được.
- Reduced motion được tôn trọng.
- Không tuyên bố WCAG compliance chỉ dựa trên screenshot.

## Attribution
Quality/design reference: Anthropic Claude Code `plugins/frontend-design/skills/frontend-design` (upstream license terms apply). Orcha rule, wording, token contract and implementation are independently authored. Claude principles are subordinate to the Orcha visual baseline and the user's brief.