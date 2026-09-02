# Orcha v7.4 — Autonomous Work Platform

**Turn goals into completed work.**

Orcha là nền tảng AI agent **local-first nhưng không local-only**. Sản phẩm điều phối Project, Planner, Supervisor, Agent Team, Skills, MCP, Data Hub và nhiều model để biến một mục tiêu thành công việc có kế hoạch, thực thi, kiểm chứng và checkpoint.

> **Ollama runs models. Orcha runs work.**

Orcha không phải một model mới và không phải bản nén của Kimi K3. Ollama, Hugging Face, cloud model APIs hoặc runtime mobile đều có thể nằm ở lớp model/provider phía dưới Orcha.

## Định vị

```text
Hugging Face         → model / dataset / ecosystem
Ollama               → local model runtime
Cloud providers      → remote model runtime
Mobile runtimes      → on-device inference

ORCHA
→ Project + Planner + Supervisor + Agent Teams + Skills + Data + Tools + Verification
```

Category: **Autonomous Work Platform**  
Operating principle: **local-first, hybrid-capable, permission-gated**.

## Kiến trúc v7.4

```text
Goal
 ↓
Project Workspace
 ↓
Autonomous Planner
 ↓
Task DAG
 ↓
Project Supervisor
 ├─ read-only task → auto execute → verify → done
 └─ write task → Approval Inbox → Permission Engine → explicit execution
 ↓
Agent Runtime
 ├─ Single
 ├─ Parallel
 └─ Agent Team
 ↓
Skills / MCP / Computer / Design Agent
 ↓
Model Router
 ├─ Desktop local (Ollama)
 ├─ Mobile on-device
 ├─ Trusted desktop peer
 └─ Private remote provider

Data Hub
 ├─ JSON API
 ├─ RSS
 ├─ Atom
 └─ Text/HTTP source
      ↓ scheduled read-only sync
   local evidence cache
```

## Data Hub — tự cập nhật dữ liệu nhiều nguồn

Orcha v7.4 có Data Hub foundation để tránh giới hạn “chỉ biết dữ liệu local”. Source registry được lưu local và có thể tự đồng bộ theo lịch.

Hỗ trợ foundation hiện tại:

- JSON HTTP API;
- RSS;
- Atom;
- text endpoint;
- chu kỳ sync tối thiểu 15 phút;
- giới hạn 5 MB mỗi lần fetch;
- cache document local;
- trạng thái lần sync gần nhất;
- source enable/pause;
- scheduler nền chỉ thực hiện **network read**.

Credential không lưu trực tiếp trong source JSON. Header bí mật được tham chiếu qua biến môi trường (`headers_env`).

Data Hub **không tự POST/PUT/DELETE ra nguồn ngoài**. Đây là data-ingestion read lane, tách khỏi Permission Engine của write tools.

API:

- `GET /api/data/status`
- `GET /api/data/sources`
- `POST /api/data/sources`
- `POST /api/data/sync`
- `POST /api/data/sources/{id}/enabled`

## Mobile Runtime

Mục tiêu của Orcha Mobile không phải ép desktop Ollama chạy trực tiếp trên iPhone/Android. Mobile Runtime chọn execution path phù hợp thiết bị:

```text
Task trên mobile
 ↓
Device capability
 RAM · storage · pin · thermal · network · privacy
 ↓
Mobile Model Selector
 ├─ on-device model
 ├─ trusted desktop peer
 ├─ private remote provider
 └─ defer nếu privacy strict mà không thể local
```

Foundation v7.4 có model selector cho iOS/iPadOS/Android và cân nhắc:

- RAM;
- storage còn trống;
- battery;
- thermal state;
- task type;
- model đã cài;
- privacy mode.

Runtime mobile dự kiến dùng các backend phù hợp như **llama.cpp / MLC / ExecuTorch**, và có thể có Core ML adapter trên Apple platforms. Ollama tag desktop không được coi là package chạy trực tiếp trên mobile; model phải được quantize/build đúng runtime.

API:

- `GET /api/mobile/models`
- `POST /api/mobile/recommend`

Ví dụ policy:

- máy 3–4 GB: ưu tiên model ~270M–600M;
- máy 6 GB+: có thể dùng lớp ~1.5B Q4 nếu storage/thermal cho phép;
- screenshot/vision nếu thiết bị yếu → trusted desktop peer hoặc private provider;
- `privacy=strict` → không tự đẩy dữ liệu ra remote, có thể `defer`.

## Project + Supervisor

Project lưu goal, task queue, dependency, approval, checkpoint và resume. Planner tự tạo milestone/task, gắn Skill/Model/Agent strategy và budget. Supervisor chỉ tự chạy task read-only.

Safety invariant:

- background Supervisor không tự chạy write side-effect;
- Project Approval không bypass Permission Engine;
- retry tự động chỉ dành cho read-only task;
- task chỉ `done` sau verification gate;
- restart không tự replay side effect.

## Parallel / Agent Team

Máy khoảng 4 GB RAM mặc định tối đa 2 worker song song. Read/reasoning/retrieval có thể chạy đồng thời; write lane vẫn serialize.

```text
Coordinator
 ├─ Research
 ├─ Specialist
 ├─ Critic
 └─ Verifier
      ↓
   Synthesis
      ↓
 serial write lane
```

## Safe learning

Orcha lưu outcome/lesson local để chấm điểm chiến lược `single / parallel / team`. Learning chỉ điều chỉnh recommendation/score; không tự sửa executable code, không tự tăng permission và không tự bật red tools.

## Context

- **Virtual Context**: kho searchable/RAG local, có thể rất lớn.
- **Working Set**: evidence thực sự đưa vào model mỗi lượt.
- **Native Context**: context gốc của model.

Virtual Context 1M không có nghĩa model attention trực tiếp 1M token.

## Desktop local models

| Profile | Model hiện tại | Gần đúng | Mục đích |
|---|---|---:|---|
| MAX | `gemma3:270m-it-qat` | ~241 MB | máy rất yếu |
| Balanced | `qwen3:0.6b-q4_K_M` | ~522 MB | mặc định RAM thấp |
| Quality | `qwen3:1.7b` | ~1.4 GB | reasoning/code cao hơn |
| UI/UX Vision Lite | `moondream:1.8b-v2-q2_K` | ~1.5 GB | screenshot observer |

Capability metadata là routing metadata; benchmark runtime được tách riêng. KII là operational heuristic, không phải IQ.

## Environment

Biến mới:

```text
ORCHA_DATA_DIR
```

Để tương thích dữ liệu cũ, runtime vẫn đọc fallback `KIMIK3_DATA_DIR` trong giai đoạn migration.

Desktop mặc định:

- Orcha: `http://127.0.0.1:11435`
- Ollama: `http://127.0.0.1:11434`

## Release naming từ v7.4

- `Orcha-vX.Y.Z-Windows-Portable.zip`
- `Orcha-vX.Y.Z-macOS.dmg`

Legacy launchers/data path được giữ compatibility trong giai đoạn chuyển brand; product-facing UI/docs/package mới dùng **Orcha**.

## Product roadmap

1. Data Hub adapters: Web/RSS/API → GitHub/Drive/Notion/Slack/Calendar connectors.
2. Dedup + incremental sync + provenance + freshness score.
3. Hybrid retrieval: local evidence first, fresh remote evidence when needed.
4. Mobile companion app: project/task/approval + on-device chat.
5. Mobile model package manager + download/evict model theo storage.
6. Trusted desktop peer: mobile gửi task nặng về máy cá nhân trong LAN/VPN.
7. Private remote provider fallback có policy theo project.
8. Cross-device encrypted project sync.

## License

Source code của Orcha trong repository tuân theo license của repository. Model weights không được redistribute. Người dùng phải tuân thủ license của từng model/provider/source dữ liệu được cấu hình.
