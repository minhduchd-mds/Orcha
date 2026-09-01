# Changelog

## v6.9.0 — Hermes Foundation + Chat Reliability

- Thêm `hermes_runtime.py` — control plane local lấy cảm hứng kiến trúc từ NousResearch Hermes Agent `v2026.8.31`, triển khai lại độc lập cho runtime ít RAM.
- Conversation-first router: câu hỏi thông tin đi direct chat; matched skill hoặc yêu cầu có side effect mới vào Agent Executor.
- Thêm durable Hermes transcript theo session + `request_id` idempotency để tránh append/trả response trùng khi client retry.
- Thêm local agent roster General / Research / Builder / Verifier và peer-message bus local-only.
- Thêm steer/cancel control registry để làm nền cho điều khiển sub-agent/team khi đang chạy.
- Thêm protected-instruction path policy cho AGENTS.md, skills, memory và Hermes config; Permission Engine hiện tại vẫn là authority chính cho write tools.
- Sửa lỗi text-only khi người dùng đang chọn `UI/UX Vision Lite`: composite vision profile tự dùng companion Balanced thay vì gửi text vào Moondream.
- Mở rộng classifier nhận biết `thiết kế/design` là UI/UX intent và giữ metadata model đã chọn + runtime model thực tế.
- Studio có Hermes status nhỏ trong Inspector; client tự gắn `request_id` cho `/api/chat`.
- Windows/macOS launcher kiểm tra đúng runtime 6.9, tự shutdown server cũ chiếm port rồi chạy `studio_server_v69.py`; CI thêm regression cho Hermes + composite route + launcher/package.

## v6.8.0 — Final Intelligence & Hardening

- Thêm `self_improvement.py`: lưu outcome, lesson local và performance score theo chiến lược `single / parallel / team`.
- Strategy recommendation dựa trên lịch sử cục bộ + RAM Guard; không tự sửa executable code.
- Agent Performance Inspector hiển thị success rate, latency, strategy score và lesson gần nhất.
- Người dùng có feedback `Tốt / Chưa tốt` để điều chỉnh score an toàn.
- Safety guard cố định: không self-modify code, không tự tăng permission, không auto-run red tools.
- Thêm `maintenance.py` với security audit cho secret/config và kiểm tra presence của Permission/MCP guard.
- Thêm backup local dạng ZIP cho skills, workflows, memory, sessions, knowledge, learning, agent-team và design reports.
- Thêm API learning dashboard/outcome/recommend/lessons và maintenance security/backup.
- Windows/macOS launcher và native package chuyển sang server `studio_server_v68.py`, bundle version 6.8.0.
- CI cuối kiểm tra safe-learning, security contract, Team/Parallel/MCP regression, JS UI và desktop packaging.

## v6.7.0 — Agent Team + Dependency Graph

- Thêm `agent_team.py` để điều phối đội agent theo DAG thay vì chỉ chạy sub-agent độc lập.
- Task graph mặc định: Research + Specialist → Critic + Verifier → Synthesis.
- Các node độc lập chạy song song theo RAM Guard; node phụ thuộc chỉ chạy khi dependency hoàn tất.
- Shared Team Memory truyền output agent trước cho agent sau mà không ghi vào global memory.
- Conflict Resolver phát hiện bất đồng cơ bản và ưu tiên Verifier + evidence khi tổng hợp.
- Budget Manager giới hạn worker, token/agent và tổng team budget theo capacity máy.
- Dependency failure làm downstream node chuyển `blocked` thay vì chạy với context lỗi.
- Giữ policy `parallel-read-serial-write`: mọi write/Figma/Computer/AutoCAD vẫn đi lane tuần tự + Permission Gate.
- Thêm API `/api/agents/team/capacity`, `/plan`, `/run`, `/runs/<id>`.
- Studio có nút `Đội agent`, Task Graph và trạng thái từng node trong Inspector; Windows/macOS launcher dùng server v6.7.

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
