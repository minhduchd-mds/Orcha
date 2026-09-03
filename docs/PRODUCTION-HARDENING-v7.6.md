# Orcha v7.6 — Production Hardening & Reliability

v7.6 chọn lọc các thay đổi đã được kiểm chứng từ workspace hardening 02/09/2026 và ghép lên nền UI/Product v7.5. Không ghi đè UI Foundation, Data Hub modal, Reference Lab hay `orcha-frontend-design`.

## Runtime & API

- Desktop API chỉ bind loopback.
- POST yêu cầu JSON và `X-Orcha-Token` lấy từ `GET /api/session`.
- Kiểm tra Host/Origin/Fetch-Site, body tối đa 16 MB và response security headers/CSP.
- `studio/api-client.js` là transport same-origin chung cho UI; feature scripts không tự quản token.
- Launcher Windows/macOS dùng `scripts/desktop_control.py` để health/stop theo contract v7.6.

## Permission & execution

- Global permission policy là giới hạn trên; Skill không được hạ policy deny.
- Quyền `once` bind với session/run/action/arguments và được tiêu thụ nguyên tử.
- Agent thực hiện một action, quan sát kết quả thật rồi mới re-plan.
- Tool fail/deny/cancel không được coi là `done`.
- Project Approval không bypass Permission Engine.
- Background Supervisor chỉ tự chạy read-only; write phải explicit execute và từng tool write vẫn qua Permission Engine.

## State, project & recovery

- Một DATA root thống nhất qua `ORCHA_DATA_DIR` với migration fallback `ORCHA_DATA_DIR`.
- Atomic JSON replace + serialized transactions cho read/modify/write quan trọng.
- Runtime lease ngăn hai Orcha process cùng giữ một DATA.
- Project task state do executor quản lý; dependency/DAG được kiểm tra; task đang chạy khi crash trở thành blocked/interrupted thay vì replay side effect.
- Planner materialize graph theo transaction và replay cùng plan không nhân đôi task.
- Harness đặt reservation trước execution để chống request trùng đồng thời.

## MCP, Computer & AutoCAD

- MCP stdio dùng persistent process pool có lock, giới hạn stderr, giữ `isError`, validate input schema và serialize write.
- Side effect không tự retry.
- Computer launch dùng application allowlist và không nhận argument tùy ý.
- AutoCAD rollback gắn với document path/handle, cần xác nhận riêng và chống rollback lặp.

## Context, model & data

- Context/RAG, memory/history và file-read được phân vùng theo project.
- Working Context bị giới hạn bởi native context và inference budget; Virtual Context vẫn là searchable store, không phải native attention.
- Model Router kiểm tra exact tag, installed state, RAM và modality; vision phải dùng model có vision capability.
- Data Hub cache tham gia evidence theo project; credential env dùng prefix `ORCHA_SOURCE_`; credential yêu cầu HTTPS.
- Data Hub có DNS/IP validation, private-network opt-in và bỏ credential khi redirect đổi origin.
- Background Data Hub vẫn là network-read-only.

## UI & accessibility

Giữ nguyên v7.5:

- Inspector close/reopen;
- icon-first composer;
- Data Hub product modal, không browser-native `prompt()`;
- Reference Lab discovery-only;
- `orcha-frontend-design` skill.

Bổ sung v7.6:

- authenticated fetch transport;
- permission dialog đóng/Escape = deny;
- responsive navigation + focus trap;
- visible focus states và hỗ trợ chữ/supporting text dễ đọc hơn;
- project scope được truyền vào các endpoint context/agent/workflow liên quan.

## Backup / restore

- Backup user DATA với manifest SHA-256.
- Không backup permission grants/locks.
- Restore validate path traversal, hash, file count và kích thước; luôn restore vào thư mục mới.
- Sau restore phải khởi động lại với DATA root mới và cấp quyền thao tác lại.

## Verification gate

`scripts/verify.py` là gate chung Windows/macOS:

1. compile toàn bộ Python thuộc app/MCP/scripts/tests;
2. `node --check` toàn bộ Studio JavaScript;
3. module self-tests;
4. full regression suite về permission, concurrency, idempotency, project/DAG, context, model, Data Hub, skills, workflow, backup và HTTP thật trên cổng tạm;
5. persistent MCP read-only capability calls;
6. Bash syntax/whitespace checks.

CI package phải chạy cùng gate này trước khi tạo Windows Portable hoặc macOS DMG.

## Không overclaim

- Self-test/model fixture không đo chất lượng suy luận của trọng số Ollama thật.
- AutoCAD vẫn cần E2E trên Windows với bản vẽ thử nghiệm trước khi dùng dữ liệu thật.
- Mobile Runtime vẫn là selector/adapter foundation; chưa phải native iOS/Android inference app.
- Figma handoff vẫn là payload/handoff contract, chưa phải live Figma execution.
- Screenshot WCAG checks vẫn là heuristic; accessibility nghiệp vụ/contrast cần nghiệm thu thủ công.
- Context chưa benchmark ở quy mô nhiều triệu chunk/vector DB production.
