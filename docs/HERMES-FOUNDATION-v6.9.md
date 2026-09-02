# Orcha — Hermes-inspired Foundation

> Historical foundation: introduced during the pre-Orcha v6.9 phase. Current product name is **Orcha**.

## Nguồn tham khảo

Kiến trúc học các **ý tưởng kiến trúc** từ `NousResearch/hermes-agent` release `v2026.8.31` (Hermes Agent v0.21.0): durable agent conversations, peer messaging, steer/cancel control, MCP command-center thinking và protected agent instructions.

Hermes Agent phát hành theo MIT License. Orcha **không copy source Hermes** trong phần triển khai này; `hermes_runtime.py`, endpoints và UI được viết lại độc lập để phù hợp runtime ít RAM. Nếu về sau copy hoặc port đoạn code cụ thể từ Hermes, phải giữ attribution/license tương ứng.

## Conversation-first routing

Một lỗi cũ của pre-Orcha runtime là text-only prompt có thể bị gửi nhầm vào composite vision model. Foundation này bổ sung `runtime_model()` để tách model người dùng chọn khỏi model thực tế dùng cho request:

- Có ảnh + UI/UX Vision Lite → Vision pipeline.
- Không có ảnh + composite model → companion Balanced cho text reasoning.
- Metadata vẫn giữ route thực tế để UI giải thích.

## Hermes control plane nhẹ

`app/hermes_runtime.py` cung cấp lớp điều phối nhẹ:

1. Conversation-first router: câu hỏi thông tin đi direct chat; matched skill hoặc side-effect intent mới vào Agent Executor.
2. Durable transcript JSONL theo session.
3. `request_id` idempotency để tránh append/trả kết quả trùng khi client retry.
4. Local agent roster: General / Research / Builder / Verifier.
5. Peer message bus local-only giữa các agent profile.
6. Steer / cancel control registry cho subagent/team integration.
7. Protected-instruction path classifier cho `AGENTS.md`, skills, memory, Hermes config.
8. Không tự nâng permission; policy Green/Yellow/Red vẫn là authority chính.

## API

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

## Launcher recovery

Launcher kiểm tra đúng version/feature flags ở `/health`. Nếu runtime cũ vẫn chiếm port 11435, launcher shutdown runtime cũ trước khi khởi động Orcha hiện tại.

## Orcha v7.4 extension

Hermes control plane vẫn là local coordination layer, nhưng Orcha không còn local-only:

- Data Hub bổ sung fresh external evidence theo read-only sync lane.
- Mobile Runtime có thể lựa chọn on-device hoặc trusted/private fallback.
- Hybrid execution không được tự nâng quyền hoặc vượt project privacy policy.

## Safety / giới hạn

- Peer bus không tự tạo vòng agent vô hạn.
- Protected path classifier không thay Permission Engine.
- Hybrid source sync chỉ đọc; write ra hệ thống ngoài phải đi qua tool/permission contract riêng.
- Orcha chỉ áp dụng các pattern phù hợp, không nhập toàn bộ Hermes framework.
