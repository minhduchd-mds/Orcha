---
id: project-analysis
name: Project Analysis
description: Map architecture, dependencies, risks and implementation priorities.
version: 1.0.0
triggers: [phân tích project, phân tích dự án, kiến trúc dự án, architecture review, project analysis]
permissions:
  filesystem.read: auto
  project.search: auto
  git.read: auto
---
# Objective
Biến project context thành bản đồ kiến trúc, rủi ro và kế hoạch nâng cấp có thứ tự ưu tiên.

# Workflow
1. Xác định mục tiêu sản phẩm và phạm vi kỹ thuật.
2. Lập bản đồ module, dependency, data flow và entry point.
3. Tìm coupling, duplication, bottleneck, security và operational risk.
4. Xếp hạng P0, P1, P2 theo impact và effort.
5. Đề xuất target architecture và migration path.
6. Tạo checklist triển khai và acceptance criteria.

# Rules
- Không giả định framework hoặc service nếu chưa thấy bằng chứng.
- Dùng file path và source context để hỗ trợ nhận định.
- Ưu tiên incremental migration thay vì rewrite toàn bộ.

# Verification
- Có architecture summary.
- Có danh sách rủi ro được xếp hạng.
- Có roadmap thực thi và tiêu chí hoàn thành.
