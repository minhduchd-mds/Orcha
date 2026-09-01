# KimiK3-Lite v6.9 — Hermes-inspired Foundation

## Nguồn tham khảo

Kiến trúc v6.9 học các **ý tưởng kiến trúc** từ `NousResearch/hermes-agent` release `v2026.8.31` (Hermes Agent v0.21.0): durable agent conversations, peer messaging, steer/cancel control, MCP command-center thinking và protected agent instructions.

Hermes Agent phát hành theo MIT License. KimiK3-Lite **không copy source Hermes** trong batch này; phần `hermes_runtime.py`, Studio endpoints và UI được viết lại độc lập để phù hợp runtime local ít RAM. Nếu về sau copy hoặc port đoạn code cụ thể từ Hermes, phải giữ attribution/license tương ứng.

## Root cause lỗi chat nhìn thấy ở v6.8

Trên Studio, người dùng có thể chọn `UI/UX Vision Lite` rồi gửi **text-only prompt**. Model này là composite profile gồm:

- Vision: `moondream:1.8b-v2-q2_K`
- Companion reasoning: `balanced` → `qwen3:0.6b-q4_K_M`

Trước v6.9, `/api/chat` chỉ dùng composite pipeline khi có `images`. Nếu không có ảnh nhưng UI đang khóa vào `UI/UX Vision Lite`, server lại đưa text thẳng cho Moondream. Đây là sai route và có thể tạo câu trả lời generic/không liên quan như lời chào lặp lại.

v6.9 thêm `model_registry.runtime_model()`:

- Có ảnh + UI/UX Vision Lite → Vision pipeline như cũ.
- Không có ảnh + composite model → tự chuyển sang companion Balanced cho text reasoning.
- Metadata vẫn giữ model người dùng đã chọn để UI giải thích route thực tế.

## Hermes control plane nhẹ

`app/hermes_runtime.py` cung cấp lớp điều phối local, không thêm dependency nặng:

1. Conversation-first router: câu hỏi thông tin đi direct chat; matched skill hoặc side-effect intent mới vào Agent Executor.
2. Durable transcript JSONL theo session.
3. `request_id` idempotency để tránh append/trả kết quả trùng khi client retry.
4. Local agent roster: General / Research / Builder / Verifier.
5. Peer message bus local-only giữa các agent profile.
6. Steer / cancel control registry cho subagent/team integration tiếp theo.
7. Protected-instruction path classifier cho `AGENTS.md`, skills, memory, Hermes config.
8. Không tự nâng permission; policy Green/Yellow/Red hiện tại vẫn là authority chính.

## API mới

- `GET /api/hermes/status`
- `GET /api/hermes/agents`
- `GET /api/hermes/session?session=<id>`
- `GET /api/hermes/peers`
- `GET /api/hermes/runs`
- `POST /api/hermes/peer`
- `POST /api/hermes/run/register`
- `POST /api/hermes/run/steer`
- `POST /api/hermes/run/cancel`
- `POST /api/hermes/protected-write`

`POST /api/chat` ở server v6.9 nhận thêm `request_id` và trả metadata `hermes.route` + `model_route.runtime_selected`.

## Launcher recovery

Windows/macOS launcher trước đây chỉ kiểm tra HTTP 200 ở `/health`. Nếu server cũ v6.8 vẫn chiếm port 11435, ứng dụng mới có thể tiếp tục dùng runtime cũ và người dùng tưởng update không có tác dụng.

v6.9 kiểm tra đúng `version=6.9.0` + Hermes flag. Nếu thấy server cũ, launcher gọi `/api/app/shutdown`, chờ port nhả ra rồi mới chạy `studio_server_v69.py`.

## Safety / giới hạn

- Peer bus hiện là control-plane local, chưa tự làm agent gọi agent vô hạn.
- Steer/cancel là registry foundation; wiring sâu vào mọi worker sẽ làm ở batch sau.
- Protected path classifier không thay Permission Engine; mọi write tool vẫn phải đi qua Permission Gate hiện có.
- Hermes v0.21.0 có phạm vi rất lớn; v6.9 chỉ lấy các pattern phù hợp với app local nhẹ, không nhập toàn bộ framework.
