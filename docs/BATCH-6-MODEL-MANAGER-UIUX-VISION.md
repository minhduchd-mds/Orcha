# Batch 6 — Model Manager + Auto Router + UI/UX Vision Lite

## 10 hạng mục
1. Model Registry tách khỏi core.
2. Custom Ollama Model CRUD.
3. RAM Guard theo bộ nhớ vật lý.
4. Capability-based Auto Model Router.
5. Per-session model lock và Auto mode.
6. Fallback sang Balanced khi model được chọn lỗi.
7. Per-model runtime benchmark + declared capability score.
8. Model comparison contract.
9. UI Model Manager: install/remove/use/custom/benchmark.
10. UI/UX Vision Lite composite pipeline + screenshot audit.

## UI/UX Vision Lite

Vision model: `moondream:1.8b-v2-q2_K` (~1.5 GB, image + text, 2K native context).
Companion: KimiK3 Balanced / Qwen3 0.6B.

Luồng:

```text
Screenshot
  -> Vision observation
  -> Balanced reasoning
  -> local RAG / UX rules
  -> P0/P1/P2 + recommendation + acceptance criteria
```

Vision chỉ làm lớp quan sát để giảm hallucination và chi phí RAM. Context 1M virtual, project knowledge, memory và UX reasoning vẫn do KimiK3 runtime quản lý.

## Model Registry

Built-in model không bị ghi đè/xóa khỏi registry. Custom model được lưu dưới `data/models.json`, nên update source không làm mất model user thêm.

## Auto Router

Router phân loại `chat`, `code`, `reasoning`, `uiux`; lọc theo RAM rồi xếp capability score. Nếu có screenshot, model không có image modality bị trừ điểm mạnh.

## Safety

- RAM Guard ngăn user lock model vượt mức RAM khuyến nghị.
- `ollama rm` chỉ chạy khi người dùng chủ động bấm gỡ weights.
- Registry delete không tự xóa weights Ollama.
- Model score metadata được ghi rõ là declared score, không giả danh benchmark học thuật.
