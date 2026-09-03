# Orcha

> **Local-first Autonomous AI Work Platform** — biến một mục tiêu thành kế hoạch, agent execution, tool actions, verification và kết quả có thể kiểm soát.

Orcha là nền tảng điều phối AI chạy **local-first, hybrid-capable**. Thay vì chỉ chat với một model, Orcha kết hợp **Planner, Supervisor, Agent Team, Skills, MCP tools, Project Context, RAG/Data Hub, Model Router và Permission Engine** để xử lý công việc nhiều bước trên desktop.

**Ollama runs models. Orcha runs work.**

---

## Công nghệ chính

| Lớp | Công nghệ / vai trò |
|---|---|
| Runtime | **Python 3.10+** |
| Desktop Studio | HTML, CSS, JavaScript, local web runtime |
| Local LLM | **Ollama** |
| Model families | Qwen 3 / Qwen 3.5, Moondream |
| Agent system | Planner, Supervisor, Single / Parallel / Agent Team |
| Tool protocol | **MCP — Model Context Protocol** |
| Knowledge | Local indexing, RAG, Virtual Context, project memory |
| Data ingestion | JSON API, RSS, Atom, text/HTTP sources |
| Safety | Permission gate, approval flow, serialized write lane, verification |
| Packaging | Windows Portable, macOS DMG, GitHub Actions CI/CD |

### Kiến trúc rút gọn

```text
User Goal
   ↓
Project Workspace
   ↓
Planner → Task DAG → Supervisor
   ↓
Single / Parallel / Agent Team
   ↓
Skills + MCP + Local Tools
   ↓
Model Router
   ├─ Local Ollama models
   ├─ Vision model
   └─ Hybrid provider path
   ↓
Verification + Permission Gate
   ↓
Result / Checkpoint / Resume
```

---

## Tính năng nổi bật

- **Autonomous Planner** — phân rã mục tiêu thành task/milestone có dependency.
- **Agent Team** — nhiều agent phối hợp theo mailbox durable/FIFO và có thể resume session.
- **MCP tools** — kết nối tool ngoài qua Model Context Protocol.
- **Local-first RAG** — index project, memory và evidence local trước khi gọi model.
- **Virtual Context** — mở rộng kho tri thức tìm kiếm mà không giả định model có attention 1M token.
- **Model Router** — chọn model theo RAM, loại nhiệm vụ và capability.
- **UI/UX Vision** — phân tích screenshot/layout bằng vision profile riêng.
- **Permission Engine** — write action phải đi qua quyền/approval; read-only và write lane được tách rõ.
- **Data Hub** — đọc JSON/RSS/Atom/text endpoint và cache evidence local.
- **Cross-platform desktop** — Windows Portable và macOS DMG được kiểm tra bằng CI.

---

# Cài đặt

## 1. Cài từ GitHub Releases — khuyến nghị

Mở trang **Releases** của repository và tải bản mới nhất:

`https://github.com/minhduchd-mds/Orcha/releases`

### Windows 10/11 x64

**Yêu cầu**

- Windows 10/11 x64
- Python 3.10+
- Ollama nếu muốn chạy local model
- RAM tối thiểu khoảng 4 GB cho profile mặc định

**Cài đặt**

1. Tải `Orcha-vX.Y.Z-Windows-Portable.zip`.
2. Giải nén vào thư mục mong muốn.
3. Chạy `INSTALL.bat` lần đầu để kiểm tra/cài dependency cần thiết.
4. Double-click `Orcha.vbs`.
5. Orcha mở tại `http://127.0.0.1:11435`.
6. Vào **Model local** → chọn model → **Cài / sửa model**.

Những lần sau chỉ cần chạy `Orcha.vbs`.

### macOS 12+

**Yêu cầu**

- macOS 12 trở lên
- Python 3.10+
- Ollama nếu muốn chạy local model

**Cài đặt**

1. Tải `Orcha-vX.Y.Z-macOS.dmg`.
2. Mở DMG và kéo **Orcha.app** vào **Applications**.
3. Nếu Gatekeeper cảnh báo vì community build chưa ký/notarize, dùng **Control-click → Open** ở lần mở đầu tiên.
4. Orcha chạy tại `http://127.0.0.1:11435`.
5. Vào **Model local** để cài profile phù hợp cấu hình máy.

> DMG/Portable không nhúng model weights. Model được tải riêng qua Ollama khi người dùng chọn cài.

---

## 2. Chạy từ source

```bash
git clone https://github.com/minhduchd-mds/Orcha.git
cd Orcha
python app/studio_server_v77.py --host 127.0.0.1 --port 11435 --profile balanced
```

Sau đó mở:

```text
http://127.0.0.1:11435
```

Nếu sử dụng local model, cài Ollama trước rồi dùng **Model local** trong Orcha để tải/tạo profile.

---

# Model local & chấm điểm

Orcha hiện có các profile built-in sau:

| Model | Backbone | Dung lượng gần đúng | RAM tối thiểu | Chat | Tiếng Việt | Code | Reasoning | Tools | Vision/UIUX | Orcha Score |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Orcha MAX** | `qwen3.5:2b` | ~2.7 GB | 6 GB | 87 | 89 | 84 | 86 | 84 | — | **8.6/10** |
| **Orcha Balanced** | `qwen3:0.6b-q4_K_M` | ~522 MB | 4 GB | 72 | 74 | 66 | 64 | 64 | — | **6.8/10** |
| **Orcha Logic 0.8B** | `qwen3.5:0.8b` | ~1.0 GB | 4 GB | 78 | 80 | 72 | 76 | 74 | — | **7.6/10** |
| **Orcha Quality** | `qwen3:1.7b` | ~1.4 GB | 6 GB | 82 | 82 | 78 | 78 | 74 | — | **7.9/10** |
| **UI/UX Vision Lite** | `moondream:1.8b-v2-q2_K` | ~1.5 GB | 4 GB | 58 | 45 | 28 | 44 | 40 | Vision 82 / UIUX 86 | **8.4/10*** |

### Cách tính điểm

- Với model text: **Orcha Score = trung bình Chat + Vietnamese + Code + Reasoning + Tools**.
- Với **UI/UX Vision Lite**: điểm `8.4/10` là **điểm chuyên môn UI/UX**, tính từ Vision + UIUX capability; không dùng để so trực tiếp với model text tổng quát.
- Đây là **capability metadata phục vụ routing trong Orcha**, không phải benchmark học thuật hay tuyên bố IQ của model.

### Nên chọn model nào?

| Nhu cầu | Khuyến nghị |
|---|---|
| Mạnh nhất mặc định / code, reasoning, planning, tools | **Orcha MAX** |
| Chat, RAG, tool cơ bản, RAM thấp | **Orcha Balanced** |
| Logic/agent/tool tốt hơn nhưng vẫn nhẹ | **Orcha Logic 0.8B** |
| Code, planning, reasoning sâu hơn | **Orcha Quality** |
| Screenshot, layout, UI/UX review | **UI/UX Vision Lite** |

### Orcha MAX

`Orcha MAX` dùng **Qwen3.5 2B** làm backbone, ưu tiên khả năng tổng quát mạnh hơn cho code, reasoning, planning và tool-oriented work. Profile chạy working context 8K mặc định để cân bằng chất lượng và RAM, trong khi native context của backbone lớn hơn nhiều.

### Orcha Logic 0.8B

`Orcha Logic 0.8B` dùng Qwen3.5-0.8B làm backbone và một behavior recipe do Orcha tự xây dựng cho:

```text
Intent
  ↓
Direct / Reason / Tool
  ↓
Minimum sufficient execution
  ↓
Self-check / Verify
  ↓
Concise final result
```

Profile này tập trung vào adaptive reasoning, tool discipline, self-check và permission awareness. Nó **không chứa proprietary weights hoặc private chain-of-thought của nhà cung cấp khác**.

---

## Context model

Orcha phân biệt ba lớp context:

- **Virtual Context** — kho searchable/RAG lớn trên local storage.
- **Working Set** — evidence thực sự được đưa vào model ở lượt hiện tại.
- **Native Context** — context window gốc của model.

Vì vậy `Virtual Context 1M` không có nghĩa model đang attention trực tiếp trên 1 triệu token.

---

## Safety model

Orcha sử dụng nguyên tắc **local-first + permission-gated**:

```text
Read / Search / Reason
        ↓
     Execute
        ↓
Write / Side effect
        ↓
Permission / Approval
        ↓
Verification
        ↓
Checkpoint
```

- Supervisor không tự bypass Permission Engine.
- Write task không tự replay sau restart.
- Retry tự động ưu tiên read-only operation.
- Agent chỉ được coi là hoàn thành sau verification gate phù hợp.
- Data Hub scheduler chỉ dùng cho network read/data ingestion.

---

## Project structure

```text
Orcha/
├── app/            # Runtime, agents, router, supervisor, storage
├── studio/         # Desktop web UI
├── config/         # Model/profile configuration
├── mcp_servers/    # MCP integrations
├── skills/         # Orcha skills
├── knowledge/      # Local knowledge assets
├── scripts/        # Verification / desktop tooling
├── tests/          # Regression tests
├── docs/           # Architecture and release documentation
└── Modelfile.*     # Local model behavior profiles
```

---

## Environment

```text
ORCHA_DATA_DIR
ORCHA_PORT
```

Mặc định desktop:

- Orcha Studio: `127.0.0.1:11435`
- Ollama: `127.0.0.1:11434`

---

## Build & verification

GitHub Actions kiểm tra Windows và macOS trước khi đóng gói.

Kiểm tra nhanh local:

```bash
python scripts/check_brand.py
python scripts/verify.py --fast
```

Kiểm tra runtime đầy đủ:

```bash
python scripts/verify.py
```

---

## Trạng thái dự án

Orcha đang phát triển theo hướng **Autonomous Work Platform** thay vì chỉ là chatbot/local model launcher. Các lớp Agent Runtime, Project/Supervisor, MCP, Model Router, Data Hub, persistence và desktop packaging đang được phát triển song song.

Các capability score có thể thay đổi khi benchmark/runtime được cải thiện.

---

## License

Source code tuân theo license của repository. Model weights không được redistribute bởi Orcha; người dùng cần tuân thủ license của từng model/provider được sử dụng.

Orcha không tuyên bố liên kết chính thức với Qwen, Google/Gemma, Moondream, Ollama hoặc các nhà cung cấp/model khác được hỗ trợ.
