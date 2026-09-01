# KimiK3-Lite Desktop Studio v6

Local AI workspace dành cho máy cấu hình thấp. Bản v6 có giao diện Desktop Studio với hai khu vực chính **Trò chuyện** và **Công việc / Workflow**, chạy local qua Ollama.

## Điểm mới v6

- UI 3 cột rõ hơn: Navigation → Workspace → Context/Intelligence Inspector.
- **Virtual Context 500K–1M tokens** cho project knowledge, memory, conversation, skills, MCP tools và custom agents.
- Phân biệt rõ:
  - **Virtual Context**: kho ngữ cảnh local có thể tìm kiếm.
  - **Working Set**: phần evidence thực sự đưa vào model trong một lượt.
  - **Native Context**: giới hạn context gốc của base model.
- Hierarchical retrieval: tìm trên toàn Virtual Context rồi chỉ nạp phần liên quan nhất vào Working Set.
- Lưu conversation history local theo session và tái sử dụng trong các lượt sau.
- Context Inspector kiểu Claude: used / limit / % + breakdown theo từng nguồn.
- KII Operational: chỉ số vận hành theo retrieval, grounding, self-check, adaptive depth, passes và sources. Đây **không phải IQ hay benchmark học thuật**.

## Context architecture

Balanced dùng `qwen3:0.6b-q4_K_M`. Base model có native context lớn hơn Working Set, nhưng KimiK3-Lite giữ Working Set thấp theo mặc định để phù hợp máy RAM 4 GB.

```text
Virtual Context (disk/index)       1,000,000 tokens
        │
        ├─ Skills
        ├─ Project knowledge
        ├─ Memory
        ├─ Conversation history
        ├─ MCP tools
        └─ Custom agents
        │
        ▼
Hierarchical Retrieval
        │
        ▼
Working Set (RAM/model prompt)     4K default on Balanced
        │
        ▼
Qwen3 0.6B native context         40,960 tokens
```

Virtual Context không có nghĩa là model nhìn đồng thời toàn bộ 1M token. Nó là kho searchable local; mỗi lượt chỉ evidence liên quan nhất được chọn để tránh làm RAM tăng mạnh.

## Hai khu vực chính

### Trò chuyện
- Adaptive Intelligence: Auto / Nhanh / Cân bằng / Suy luận sâu.
- Local Memory.
- Hybrid RAG đọc tài liệu và source code.
- Conversation history theo session.
- Hiển thị source file/chunk vừa dùng.
- Context + Intelligence Inspector theo thời gian thực.

### Công việc
- Workflow AI tuần tự, tối ưu RAM thấp.
- Workflow mẫu: phân tích dự án, review code, review UI/UX, lập kế hoạch.
- Tự tạo workflow tối đa 12 bước.
- Lưu lịch sử và kết quả local.

## Profile model

| Profile | Base | Dung lượng gần đúng | Virtual Context | Working Set mặc định | Mục đích |
|---|---|---:|---:|---:|---|
| MAX | `gemma3:270m-it-qat` | ~241 MB | 500K | 2K | máy cực yếu |
| **Balanced** | `qwen3:0.6b-q4_K_M` | **~522 MB** | **1M** | **4K** | mặc định cho RAM 4 GB |
| Quality | `qwen3:1.7b` | ~1.4 GB | 1M | 6K | chất lượng cao hơn |

> Đây là runtime/orchestration local nhẹ, không phải bản nén lossless của full Kimi K3 2.78T.

## Windows

Yêu cầu Windows 10/11 x64, Ollama và Python 3.10+.

1. Tải `KimiK3-Lite-v5-Windows-Portable.zip` từ GitHub Actions/Release.
2. Giải nén.
3. Double-click `INSTALL.bat` lần đầu.
4. Sau đó mở `KimiK3 Studio.vbs`.
5. Chọn profile Balanced trong màn hình Setup và cài model.

Chi tiết: `WINDOWS-QUICKSTART-V5.md`.

## macOS

Yêu cầu macOS 12+, Ollama và Python 3.10+.

1. Tải `KimiK3-Lite-v5-macOS.dmg`.
2. Kéo **KimiK3 Lite Studio.app** vào Applications.
3. Mở app và cài profile model trong giao diện.

Dữ liệu local nằm tại `~/Library/Application Support/KimiK3-Lite Studio`.

Chi tiết: `MACOS-QUICKSTART-V5.md`.

## Local-first

- Studio: `http://127.0.0.1:11435`
- Ollama: `http://127.0.0.1:11434`
- Model weights không nằm trong repo; Ollama tải khi người dùng chọn profile.
- Context index, memory và session history nằm local.

## API

- `POST /api/chat`
- `GET /api/context?session=<id>`
- `POST /v1/chat/completions`
- `GET /v1/models`

`POST /api/chat` trả thêm `context` và `intelligence` để UI hoặc ứng dụng khác hiển thị chỉ số.

## Build desktop packages

Workflow `.github/workflows/build-desktop.yml` tạo:

- `KimiK3-Lite-v5-Windows-Portable.zip`
- `KimiK3-Lite-v5-macOS.dmg`

Push lên `main` sẽ build artifact. Tag dạng `v*` sẽ tạo GitHub Release và đính kèm cả hai package.
