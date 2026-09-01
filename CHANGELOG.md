# Changelog

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
