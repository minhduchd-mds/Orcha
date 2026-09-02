# Orcha — Model Manager + Auto Router + UI/UX Vision Lite

> Historical foundation: introduced before the Orcha rebrand. Current product name is **Orcha**.

## Năng lực
1. Model Registry tách khỏi core.
2. Custom Ollama Model CRUD.
3. RAM Guard theo bộ nhớ vật lý.
4. Capability-based Auto Model Router.
5. Model mode / selection contract.
6. Fallback khi model được chọn lỗi.
7. Per-model runtime benchmark + declared capability score.
8. Model comparison contract.
9. UI Model Manager: install/remove/use/custom/benchmark.
10. UI/UX Vision Lite composite pipeline + screenshot audit.

## UI/UX Vision Lite

Vision model: `moondream:1.8b-v2-q2_K` (~1.5 GB, image + text, 2K native context).
Companion: Orcha Balanced / Qwen3 0.6B.

```text
Screenshot
  -> Vision observation
  -> Balanced reasoning
  -> local RAG / UX rules
  -> P0/P1/P2 + recommendation + acceptance criteria
```

Vision là lớp quan sát để giảm hallucination và chi phí RAM. Virtual Context, project knowledge, memory và UX reasoning do Orcha orchestration runtime quản lý.

## Model Registry

Built-in model không bị ghi đè/xóa khỏi registry. Custom model được lưu trong data directory, nên update source không làm mất model user thêm.

## Auto Router

Router phân loại `chat`, `code`, `reasoning`, `uiux`; lọc theo RAM rồi xếp capability score. Nếu có screenshot, model không có image modality bị trừ điểm mạnh.

Từ Orcha v7.4, Model Router được mở rộng về mặt kiến trúc để phục vụ cả desktop local, mobile on-device, trusted desktop peer và private remote provider.

## Safety

- RAM Guard ngăn lock model vượt mức RAM khuyến nghị.
- `ollama rm` chỉ chạy khi người dùng chủ động bấm gỡ weights.
- Registry delete không tự xóa weights Ollama.
- Capability metadata không giả danh benchmark học thuật.
- Mobile model recommendation không có nghĩa desktop Ollama tag chạy trực tiếp trên iOS/Android.
