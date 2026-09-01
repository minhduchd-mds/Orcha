# KimiK3-Lite Desktop Studio v6.8

Local AI workspace dành cho máy cấu hình thấp, chạy local qua Ollama. Studio gồm **Trò chuyện**, **Công việc / Workflow**, **Skills**, **MCP**, **Model Manager**, **UI/UX Design Agent**, **Parallel Agents**, **Agent Team** và từ v6.8 có **Safe Self-Improvement + Performance + Local Backup/Security Audit**.

## Agent runtime

```text
User task
   ↓
Strategy / RAM Guard
   ├─ Single Agent
   ├─ Parallel Agents
   └─ Agent Team DAG
          ↓
Research + Specialist
          ↓
Critic + Verifier
          ↓
Synthesis
          ↓
Write / MCP lane
          ↓
Permission Gate
```

Máy khoảng 4 GB RAM mặc định tối đa 2 worker song song. Read/reasoning/retrieval có thể chạy đồng thời; sửa file, Computer, Figma và AutoCAD vẫn serialize và yêu cầu permission theo policy.

## Safe Self-Improvement v6.8

Kimi lưu outcome và lesson local để chấm điểm chiến lược `single / parallel / team`. Recommendation dựa trên lịch sử cục bộ + RAM Guard.

Safety invariant:

- không tự sửa executable code;
- không tự tăng quyền;
- không tự chạy red tools;
- feedback/lesson chỉ điều chỉnh score và recommendation;
- người dùng vẫn kiểm soát write actions.

Inspector có **Agent Performance**: success rate, latency, strategy score, recent lessons và feedback `Tốt / Chưa tốt`.

## Local maintenance

- Security audit kiểm tra chuỗi giống secret/token trong config quan trọng và presence của Permission/MCP guards.
- Backup ZIP local cho skills, workflows, memory, sessions, knowledge, learning, Agent Team và Design reports.
- Backup nằm trong `KIMIK3_DATA_DIR/backups`.

## Virtual Context

- **Virtual Context**: kho ngữ cảnh local searchable, 500K–1M token tùy profile.
- **Working Set**: evidence thực sự nạp vào model mỗi lượt, giữ nhỏ để tiết kiệm RAM.
- **Native Context**: giới hạn context gốc của model Ollama.

Virtual Context không có nghĩa model attention trực tiếp toàn bộ 1M token cùng lúc.

## Model profiles

| Profile | Base | Dung lượng gần đúng | Working Set | Mục đích |
|---|---|---:|---:|---|
| MAX | `gemma3:270m-it-qat` | ~241 MB | 2K | máy cực yếu |
| Balanced | `qwen3:0.6b-q4_K_M` | ~522 MB | 4K | mặc định RAM thấp |
| Quality | `qwen3:1.7b` | ~1.4 GB | 6K | chất lượng cao hơn |
| UI/UX Vision Lite | `moondream:1.8b-v2-q2_K` | ~1.5 GB | vision observer | screenshot/UI review |

> Đây là runtime/orchestration local nhẹ, không phải bản nén lossless của full Kimi K3 2.78T.

## UI/UX Design Agent

Design Agent hỗ trợ nhiều screenshot, responsive comparison, component inventory, design-token candidates, WCAG visual heuristics, UX flow critique, evidence/confidence, P0/P1/P2, remediation workflow và Figma/MCP handoff. Write action vẫn yêu cầu xác nhận.

## API chính

- `POST /api/chat`
- `GET /api/context?session=<id>`
- `GET /api/agents/parallel/capacity`
- `POST /api/agents/parallel/run`
- `GET /api/agents/team/capacity`
- `POST /api/agents/team/plan`
- `POST /api/agents/team/run`
- `GET /api/learning/dashboard`
- `GET /api/learning/lessons`
- `POST /api/learning/outcome`
- `POST /api/learning/recommend`
- `GET /api/maintenance/security`
- `POST /api/maintenance/security/run`
- `GET /api/maintenance/backups`
- `POST /api/maintenance/backup`
- `POST /api/design/analyze`
- `POST /v1/chat/completions`
- `GET /v1/models`

## Desktop

Windows 10/11 x64 và macOS 12+ cần Python 3.10+ và Ollama. Dữ liệu/model weights ở local; model weights do Ollama quản lý.

Release theo tag `v*` tạo:

- `KimiK3-Lite-vX.Y.Z-Windows-Portable.zip`
- `KimiK3-Lite-vX.Y.Z-macOS.dmg`

Studio mặc định: `http://127.0.0.1:11435`  
Ollama mặc định: `http://127.0.0.1:11434`
