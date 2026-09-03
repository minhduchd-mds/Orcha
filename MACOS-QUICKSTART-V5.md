# macOS Quick Start — Orcha v7.4

Yêu cầu: macOS 12+, Python 3.10+ và Ollama nếu dùng local desktop models.

1. Mở `Orcha-v7.4.0-macOS.dmg`.
2. Kéo **Orcha.app** vào **Applications**.
3. Nếu Gatekeeper cảnh báo vì bản community chưa ký/notarize, dùng **Control-click → Open** lần đầu.
4. Orcha mở tại `127.0.0.1:11435`.
5. Vào **Model local** để chọn profile phù hợp máy.

## Data Hub

Data Hub hỗ trợ JSON API, RSS, Atom và text endpoint. Sync nền chỉ đọc dữ liệu từ nguồn ngoài và cache local; secret header nên tham chiếu qua biến môi trường.

## Mobile Runtime

Mobile Runtime foundation chọn execution path dựa trên RAM, storage, battery, thermal, network và privacy: `on_device → trusted_desktop_peer → private_remote_provider`.

## Dữ liệu

Mặc định mới: `~/Library/Application Support/Orcha` qua `ORCHA_DATA_DIR`. Runtime vẫn hỗ trợ `ORCHA_DATA_DIR` như alias migration.

DMG không chứa model weights; local model được tải riêng theo runtime/provider tương ứng.
