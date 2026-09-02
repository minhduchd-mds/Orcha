# Orcha v7.4 — Mobile Runtime Foundation

Orcha Mobile được thiết kế như một **execution selector**, không phải bản desktop Ollama nhét nguyên lên điện thoại.

## Mục tiêu

- Cho phép chat/task nhẹ chạy on-device khi đủ RAM/storage.
- Giữ `privacy=strict` không tự đẩy dữ liệu ra ngoài.
- Khi task quá nặng, có thể ưu tiên trusted desktop peer trước private remote provider.
- Model selection dựa trên capability thiết bị thay vì hard-code một model duy nhất.

## Decision flow

```text
Mobile task
  ↓
Device capability
  OS · RAM · storage · battery · thermal · network
  ↓
Privacy policy
  ↓
Task classifier
  chat · code · reasoning · vision
  ↓
Model selector
  ├─ on_device
  ├─ trusted_desktop_peer
  ├─ private_remote_provider
  └─ defer
```

## Runtime families

Foundation hiện mô tả các backend mobile phù hợp như:

- `llama.cpp`
- `MLC`
- `ExecuTorch`
- Core ML adapter trên Apple platforms khi có package tương thích

Một Ollama tag desktop **không được coi là package chạy trực tiếp trên iOS/Android**. Model phải được quantize/build phù hợp backend mobile.

## Device contract

```json
{
  "device": {
    "os": "ios",
    "ram_gb": 6,
    "free_storage_gb": 10,
    "battery_percent": 80,
    "thermal_state": "normal",
    "network": true,
    "installed_model_ids": ["qwen-06b-q4"]
  },
  "task": "Chat tiếng Việt và tóm tắt tài liệu",
  "privacy": "balanced"
}
```

## Current API

- `GET /api/mobile/models`
- `POST /api/mobile/recommend`

## Current selector rules

- 3–4 GB RAM: ưu tiên lớp 270M–600M.
- 6 GB+ RAM: có thể xét lớp ~1.5B Q4 nếu storage và thermal cho phép.
- Vision/UIUX đòi hỏi model/runtime tương thích image; nếu máy yếu thì selector có thể chọn peer/remote.
- Battery thấp hoặc thermal serious/critical → tránh workload nặng on-device.
- `privacy=strict` + không đủ local → `defer`, không tự chuyển remote.

## Trusted desktop peer

Roadmap ưu tiên một peer protocol để điện thoại có thể giao task nặng cho Orcha desktop cá nhân qua LAN/VPN:

```text
Phone
  encrypted request
      ↓
Trusted Orcha Desktop
  Project / Model / Agent Team
      ↓
verified result
      ↓
Phone
```

Peer execution phải có device pairing, project allowlist, encrypted transport và approval policy. v7.4 **chưa tuyên bố đã có mobile app hay peer transport thật**; hiện có selector/API foundation để triển khai đúng hướng.

## Mobile product roadmap

1. Companion UI: Project, Task, Approval Inbox, Chat.
2. Device capability probe.
3. Mobile model download/eviction manager.
4. On-device runtime adapter.
5. Trusted desktop pairing.
6. Cross-device encrypted project state.
7. Push notification cho approval/task completion.
8. Background sync tuân thủ battery/data policy của iOS/Android.
