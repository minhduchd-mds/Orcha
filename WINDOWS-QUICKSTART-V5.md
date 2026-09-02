# Windows Quick Start — Orcha v7.4

## Yêu cầu

- Windows 10/11 x64
- Python 3.10+
- Ollama nếu dùng local desktop models

## Lần đầu

1. Giải nén `Orcha-v7.4.0-Windows-Portable.zip`.
2. Chạy `INSTALL.bat` nếu máy chưa có runtime cần thiết.
3. Double-click `Orcha.vbs`.
4. Orcha mở tại `http://127.0.0.1:11435`.
5. Vào **Model local** để chọn/cài model phù hợp RAM.

## Data Hub

Mở **Data Hub** để thêm JSON API, RSS, Atom hoặc text endpoint. Source có thể tự sync theo lịch; sync nền chỉ đọc dữ liệu và lưu cache local.

## Mobile Runtime

Mở **Mobile Runtime** để mô phỏng/cấu hình capability iOS/Android và xem model/runtime được khuyến nghị. v7.4 là foundation selector; mobile app/package model riêng sẽ phát triển tiếp.

## Dữ liệu

Biến ưu tiên: `ORCHA_DATA_DIR`. Trong giai đoạn migration, Orcha vẫn đọc `KIMIK3_DATA_DIR` nếu đã có dữ liệu bản cũ.

## Lần sau

Chỉ cần chạy `Orcha.vbs`.
