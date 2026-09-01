# KimiK3-Lite v5 Desktop Architecture

## Mục tiêu

Tạo trải nghiệm phần mềm local cho người dùng phổ thông mà không buộc thao tác trong CMD/PowerShell, đồng thời giữ footprint thấp cho máy RAM 4 GB.

## Desktop shell

Windows dùng Edge/Chrome App Mode, backend Python chạy ẩn. macOS dùng app bundle mỏng trong DMG và mở Chrome/Edge App Mode hoặc browser mặc định.

## Backend

- Python standard library: ThreadingHTTPServer, urllib, subprocess.
- Ollama nạp đúng một model local theo profile.
- Adaptive Intelligence tái sử dụng model theo nhiều pass tuần tự.
- RAG và workflow chạy tuần tự để kiểm soát RAM.

## First-run

Studio → kiểm tra Ollama → kiểm tra model → chọn MAX/Balanced/Quality → ollama pull/create → Ready.

## Data

Có thể override bằng `KIMIK3_DATA_DIR`. Bản macOS lưu dưới `~/Library/Application Support/KimiK3-Lite Studio`.
