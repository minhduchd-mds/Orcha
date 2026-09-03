# Orcha — Desktop Architecture Foundation

> Historical foundation: this document describes the lightweight desktop shell introduced before the Orcha rebrand.

## Mục tiêu

Tạo trải nghiệm phần mềm desktop cho người dùng phổ thông mà không buộc thao tác trong CMD/PowerShell, đồng thời giữ footprint thấp cho máy RAM 4 GB.

## Desktop shell

Windows dùng Edge/Chrome App Mode, backend Python chạy ẩn. macOS dùng app bundle mỏng trong DMG và mở Chrome/Edge App Mode hoặc browser mặc định.

## Backend

- Python standard library: `ThreadingHTTPServer`, `urllib`, `subprocess`.
- Ollama có thể nạp model local theo profile.
- Orcha orchestration tái sử dụng model theo nhiều pass/agent strategy.
- RAG, workflow, Planner và Supervisor kiểm soát Working Context/RAM.

## First-run

Orcha → kiểm tra runtime → kiểm tra model/provider → chọn profile → cài/pull nếu cần → Ready.

## Data

Biến mới là `ORCHA_DATA_DIR`. `ORCHA_DATA_DIR` chỉ được giữ như alias migration. macOS mặc định dùng `~/Library/Application Support/Orcha`.

## v7.4 extension

Desktop không còn là execution target duy nhất. Orcha bổ sung Data Hub cho fresh external evidence và Mobile Runtime foundation để chọn on-device/trusted-peer/private-provider theo capability + privacy policy.
