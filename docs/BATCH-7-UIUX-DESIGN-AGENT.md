# Batch 7 — UI/UX Design Agent v6.5

## Scope
Batch 7 nâng UI/UX từ audit một screenshot thành Design Agent đa màn hình, evidence-first.

## 10 hạng mục
1. Multi-screenshot audit: tối đa 8 ảnh/lần.
2. Responsive comparison: mobile/tablet/desktop coverage matrix.
3. Component detection: inventory component theo evidence từ Vision Lite.
4. Design-token extraction: color/spacing/radius/typography candidates.
5. WCAG heuristic: contrast/focus/label/touch-target risk; không thay thế DOM/CSS audit.
6. UX flow critique: strengths, friction, missing states.
7. Severity + confidence: P0/P1/P2, evidence, confidence, acceptance criteria.
8. Remediation workflow generator: đưa report thành Workflow trong khu Công việc.
9. Figma/MCP handoff contract: read-only mặc định, write cần xác nhận.
10. Design Agent workspace + Windows/macOS CI regression gate.

## Runtime
Screenshot(s) → Moondream Vision Lite từng ảnh → structured observation → Balanced companion + project knowledge → Design QA report → remediation/Figma handoff.

## Safety
- Không gửi screenshot ra cloud khi dùng local Ollama.
- Không tuyên bố WCAG pass/fail chỉ từ ảnh.
- Không write Figma/computer từ handoff nếu chưa qua Permission Gate.
- Ảnh base64 chỉ dùng trong request và không được ghi vào design report; report lưu metadata + finding.

## API
- `POST /api/design/analyze`
- `GET /api/design/reports`
- `GET /api/design/reports/{id}`
- `POST /api/design/remediation-workflow`
- `POST /api/design/figma-handoff`

## Input example
```json
{
  "message": "Review responsive và accessibility",
  "screens": [
    {"name":"Desktop","viewport":"desktop","width":1440,"height":900,"image":"<base64>"},
    {"name":"Mobile","viewport":"mobile","width":430,"height":932,"image":"<base64>"}
  ]
}
```

## Output
Report có: score vận hành, responsive matrix, components, token candidates, WCAG heuristic, flow, issues, remediation workflow và Figma/MCP handoff.
