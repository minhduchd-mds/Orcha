# Changelog

## v6.6.0 — Parallel Agent Orchestrator

- Thêm `parallel_agent.py` với RAM-aware concurrency; máy 4 GB mặc định tối đa 2 worker song song.
- Coordinator tách nhiệm vụ thành Research, Specialist, Critic và Verifier sub-agent.
- Các sub-agent chạy song song ở pha read-only/phân tích; thao tác có side effect vẫn serialize qua Permission Gate.
- Thêm chiến lược `parallel-read-serial-write` để tránh hai agent cùng sửa file, máy tính, Figma hoặc AutoCAD.
- Thêm synthesis pass tổng hợp evidence và bất đồng giữa các sub-agent.
- Thêm API `/api/agents/parallel/capacity`, `/plan`, `/run` và `/runs/<id>`.
- Studio có nút `Song song`, RAM/worker capacity và trạng thái từng sub-agent trong Inspector.
- Server v6.6 inject UI Parallel Agents mà không làm phình layout chính.
- Windows/macOS launcher chuyển sang `studio_server_v66.py`.
- CI kiểm tra Python/JS, RAM guard, parallel policy, desktop package và versioned Release assets.

## v6.0.0 — Virtual Context + Intelligence Inspector

- Redesign Desktop Studio theo layout 3 cột: Navigation → Workspace → Inspector.
- Thêm Context Inspector kiểu Claude với used / limit / % và breakdown theo Skills, Project knowledge, Memory, Conversation, MCP tools, Custom agents và Free space.
- Thêm Virtual Context 500K cho MAX và 1M cho Balanced/Quality.
- Tách rõ Virtual Context, Working Set và Native Context để không đánh đồng kho dữ liệu với context thực sự nạp vào model.
- Thêm `context_engine.py` để đo token xấp xỉ, quản lý session history và inventory context local.
- Chat lưu history theo session và đưa phần lịch sử gần nhất vào Working Set.
- Retrieval tìm trên toàn index rồi giới hạn evidence theo Working Set để giữ RAM thấp.
- Ollama API nhận `num_ctx` theo Working Set profile.
- Thêm `GET /api/context?session=<id>`.
- `POST /api/chat` trả thêm `context` và `intelligence`.
- Thêm KII Operational theo retrieval, grounding, self-check, adaptive depth, passes và sources; không coi đây là IQ/benchmark học thuật.
- Windows build và macOS DMG tiếp tục được kiểm tra tự động trên GitHub Actions.

## v5.1.0 — Windows + macOS distribution

- Thêm macOS launcher và native folder picker qua AppleScript.
- Thêm portable Windows artifact và macOS `.dmg` artifact trong GitHub Actions.
- Dữ liệu macOS tách khỏi app bundle qua `KIMIK3_DATA_DIR`.
- Bổ sung tìm Ollama CLI trong `/Applications/Ollama.app`, Homebrew Intel/Apple Silicon.
- Sửa setup worker cập nhật trạng thái `done` sau khi `ollama create` thành công.
- Release theo tag `v*` tự đính kèm Windows ZIP và macOS DMG.

## v5.0.0 — Desktop Studio

- Desktop launcher chạy backend ẩn, không cần CMD/PowerShell.
- Edge/Chrome App Mode.
- First-run Setup UI.
- Cài/sửa MAX, Balanced, Quality từ giao diện.
- Windows folder picker cho RAG indexing.
- Chat + Công việc/Workflow + Adaptive Intelligence + Memory + Hybrid RAG.
