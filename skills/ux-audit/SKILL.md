---
id: ux-audit
name: UX Audit
description: Audit user flow, hierarchy, consistency, feedback and accessibility.
version: 1.0.0
triggers: [review ui, review ux, ux audit, đánh giá giao diện, kiểm tra giao diện, accessibility]
permissions:
  filesystem.read: auto
  project.search: auto
  browser.read: auto
  browser.write: confirm
---
# Objective
Đánh giá UI/UX dựa trên mục tiêu người dùng, luồng tác vụ và bằng chứng từ thiết kế/source thay vì chỉ nhận xét thẩm mỹ.

# Workflow
1. Xác định persona, nhiệm vụ chính và điểm vào luồng.
2. Lập bản đồ user flow và trạng thái chính.
3. Audit hierarchy, consistency, affordance, feedback và error prevention.
4. Audit responsive và accessibility nếu có dữ liệu.
5. Xếp hạng vấn đề theo P0, P1, P2 và effort S, M, L.
6. Viết acceptance criteria cho từng đề xuất quan trọng.

# Rules
- Không bịa user research hoặc số liệu conversion.
- Phân biệt lỗi usability với preference thẩm mỹ.
- Ưu tiên vấn đề cản trở task completion.

# Verification
- Mỗi P0/P1 phải nêu tác động người dùng.
- Đề xuất phải có trạng thái trước/sau hoặc acceptance criteria.
- Nếu thiếu dữ liệu phải ghi rõ giả định.
