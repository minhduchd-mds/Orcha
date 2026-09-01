# KimiK3-Lite Desktop Studio v5.1

Local AI workspace dành cho máy cấu hình thấp. Bản v5.1 có giao diện Desktop Studio, hai khu vực chính **Trò chuyện** và **Công việc / Workflow**, chạy local qua Ollama.

## Hai khu vực chính

### Trò chuyện
- Adaptive Intelligence: Auto / Fast / Smart / Deep.
- Local Memory.
- Hybrid RAG đọc tài liệu và source code.
- Hiển thị nguồn file/chunk vừa dùng.

### Công việc
- Workflow AI tuần tự, tối ưu RAM thấp.
- Workflow mẫu: phân tích dự án, review code, review UI/UX, lập kế hoạch.
- Tự tạo workflow tối đa 12 bước.
- Lưu lịch sử và kết quả local.

## Profile model

| Profile | Base | Dung lượng gần đúng | Mục đích |
|---|---|---:|---|
| MAX | `gemma3:270m-it-qat` | ~241 MB | máy cực yếu |
| **Balanced** | `qwen3:0.6b-q4_K_M` | **~522 MB** | mặc định cho RAM 4 GB |
| Quality | `qwen3:1.7b` | ~1.4 GB | chất lượng cao hơn |

> Đây là runtime/orchestration local nhẹ, không phải bản nén lossless của full Kimi K3 2.78T.

## Windows

Yêu cầu Windows 10/11 x64, Ollama và Python 3.10+.

1. Tải `KimiK3-Lite-v5-Windows-Portable.zip` từ GitHub Actions/Release.
2. Giải nén.
3. Double-click `INSTALL.bat` lần đầu.
4. Sau đó mở `KimiK3 Studio.vbs`.
5. Chọn profile Balanced trong màn hình Setup và cài model.

Chi tiết: `WINDOWS-QUICKSTART-V5.md`.

## macOS

Yêu cầu macOS 12+, Ollama và Python 3.10+.

1. Tải `KimiK3-Lite-v5-macOS.dmg`.
2. Kéo **KimiK3 Lite Studio.app** vào Applications.
3. Mở app và cài profile model trong giao diện.

Dữ liệu local nằm tại `~/Library/Application Support/KimiK3-Lite Studio`.

Chi tiết: `MACOS-QUICKSTART-V5.md`.

## Local-first

- Studio: `http://127.0.0.1:11435`
- Ollama: `http://127.0.0.1:11434`
- Model weights không nằm trong repo; Ollama tải khi người dùng chọn profile.

## API

- `POST /api/chat`
- `POST /v1/chat/completions`
- `GET /v1/models`

## Build desktop packages

Workflow `.github/workflows/build-desktop.yml` tạo:

- `KimiK3-Lite-v5-Windows-Portable.zip`
- `KimiK3-Lite-v5-macOS.dmg`

Push lên `main` sẽ build artifact. Tag dạng `v*` sẽ tạo GitHub Release và đính kèm cả hai package.
