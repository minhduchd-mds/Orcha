# Orcha v7.4 — Hybrid Data Architecture

Orcha được định vị **local-first, hybrid-capable**. Local vẫn là nơi giữ project state, memory, permission policy và dữ liệu nhạy cảm; Data Hub bổ sung dữ liệu mới từ nguồn ngoài khi project cần freshness.

## Mục tiêu

- Không khóa người dùng trong dữ liệu local cũ.
- Tự cập nhật evidence từ nhiều nguồn theo lịch.
- Giữ provenance/source URL và trạng thái sync.
- Không lưu secret trực tiếp trong source config.
- Background sync chỉ thực hiện network read.
- Không để data refresh trở thành đường bypass Permission Engine.

## Luồng

```text
External sources
  ├─ JSON API
  ├─ RSS
  ├─ Atom
  └─ text endpoint
       ↓
Source Registry
       ↓
Read-only Scheduler
       ↓
Fetch Guard
  timeout 15s
  max 5 MB
  http/https only
       ↓
Parser / Normalizer
       ↓
Local Data Hub Cache
       ↓
Project retrieval / evidence layer (next phase)
```

## Source contract

```json
{
  "id": "product-news",
  "name": "Product news",
  "type": "rss",
  "url": "https://example.com/feed.xml",
  "enabled": true,
  "interval_minutes": 60,
  "headers_env": {
    "Authorization": "ORCHA_SOURCE_TOKEN"
  }
}
```

`headers_env` map header name → environment variable name. Token value không được ghi vào `sources.json`.

## Current v7.4 API

- `GET /api/data/status`
- `GET /api/data/sources`
- `POST /api/data/sources`
- `POST /api/data/sync`
- `POST /api/data/sources/{id}/enabled`

## Scheduler

- chu kỳ kiểm tra nền: khoảng 60 giây;
- source interval tối thiểu: 15 phút;
- source bị disable không sync;
- lỗi một source không làm dừng scheduler;
- lỗi được lưu state local để UI hiển thị.

## Security boundaries

1. Background sync không POST/PUT/PATCH/DELETE lên nguồn ngoài.
2. URL hiện chỉ nhận `http`/`https`.
3. Mỗi response giới hạn 5 MB.
4. Credential lấy từ environment.
5. Data Hub không tự cấp quyền cho Project Supervisor/Agent tools.
6. Nếu sau này có connector write (Gmail/Drive/GitHub/Slack...), connector đó phải có permission contract riêng.

## Next steps

1. Incremental sync với ETag / Last-Modified.
2. Dedup theo content hash.
3. Freshness score + provenance metadata.
4. Data Hub → Context Engine indexing pipeline.
5. Connector adapters: GitHub, Drive, Notion, Slack, Calendar.
6. Per-project source allowlist.
7. Encrypted connector credential store / OS keychain.
8. Remote evidence TTL và stale-data warnings.
