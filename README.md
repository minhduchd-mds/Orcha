# KimiK3-Lite Desktop Studio v6.6

Local AI workspace dành cho máy cấu hình thấp, chạy local qua Ollama. Studio tập trung vào **Trò chuyện**, **Công việc / Workflow**, **Skills**, **MCP**, **UI/UX Design Agent**, **Model Manager** và từ v6.6 có **Parallel Agent Orchestrator**.

## Parallel Agents v6.6

KimiK3 có thể chia một yêu cầu thành nhiều sub-agent chạy song song nhưng vẫn ưu tiên ổn định RAM thấp.

```text
Coordinator
   ├─ Research Agent      ┐
   ├─ Specialist Agent    ├─ parallel read-only
   ├─ Critic Agent        │
   └─ Verifier Agent      ┘
             ↓
          Synthesis
             ↓
     Write / MCP actions
             ↓
 serialize + Permission Gate
```

- Máy khoảng 4 GB RAM: mặc định tối đa **2 worker**.
- RAM thấp hơn có thể tự hạ xuống 1 worker; máy mạnh hơn có thể tăng nhưng runtime giới hạn tối đa 4.
- Các pha đọc, reasoning, review, retrieval có thể chạy song song.
- Các thao tác sửa file, click/type máy tính, Figma/AutoCAD write không chạy đồng thời; chúng vẫn qua Permission Gate để tránh xung đột.
- Nút **⇉ Song song** trong Chat chạy Parallel Agent mode và Inspector hiển thị capacity + trạng thái từng sub-agent.

## Virtual Context

- **Virtual Context**: kho ngữ cảnh local searchable, 500K–1M token tùy profile.
- **Working Set**: evidence thực sự nạp vào model mỗi lượt, giữ nhỏ để tiết kiệm RAM.
- **Native Context**: giới hạn context gốc của model Ollama.

```text
Virtual Context 1M
   ├─ Skills
   ├─ Project knowledge
   ├─ Memory
   ├─ Conversation
   ├─ MCP tools
   └─ Agents
        ↓
Retrieval / Context Builder
        ↓
Working Set ~4K default
        ↓
Local model
```

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
- `POST /api/agents/parallel/plan`
- `POST /api/agents/parallel/run`
- `GET /api/agents/parallel/runs/<id>`
- `POST /api/design/analyze`
- `POST /v1/chat/completions`
- `GET /v1/models`

## Desktop

Windows 10/11 x64 và macOS 12+ cần Python 3.10+ và Ollama. Dữ liệu/model weights ở local; model weights do Ollama quản lý.

Release theo tag `v*` tạo hai asset versioned:

- `KimiK3-Lite-vX.Y.Z-Windows-Portable.zip`
- `KimiK3-Lite-vX.Y.Z-macOS.dmg`

Studio mặc định: `http://127.0.0.1:11435`  
Ollama mặc định: `http://127.0.0.1:11434`
