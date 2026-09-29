# service/google

Google 系サービス。OAuth 認証（`auth.py`）、Calendar（`calendar.py`）、Gmail（`gmail/`、詳細は `gmail/CLAUDE.md`）。

## 認証（`auth.py` / `GoogleAuth`）

- Calendar と Gmail で **1 つの `GoogleAuth` を共有**する（`service.container.get_google_auth()`）。一度の OAuth で両方使える。
- スコープ: `gmail.modify` と `calendar`（Gmail は既読化のため modify。readonly は併記しない）。スコープを追加・変更すると既存トークンは `has_scopes` で弾かれ、再認証（`/google_auth`）が必要になる。
- `get_creds()` は有効な認証情報か `None` を返す（期限切れなら refresh して保存）。例外は投げない。
- 認証フロー: `create_cred_url()` で URL を発行 → ユーザーが Google で認証 → リダイレクト先の URL を Discord のモーダルに貼る → `interactive_creds(url)`。UI は `cogs/service/_google_auth.py`。
- トークンは `.gcp_keys/token.json` にパーミッション 600 で保存。中身を読んだり出力したりしない。
- 各サービスには `GoogleAuth` 自体ではなく `get_creds` 関数を渡す（毎回最新の認証情報を取るため）。

## Calendar（`calendar.py` / `GoogleCalendarService`）

- 取得は `service.container.get_google_calendar_service()`。登録先カレンダー（`GOOGLE_CALENDAR_ID`、既定 `primary`）とタイムゾーン（`GOOGLE_CALENDAR_TIMEZONE`、既定 `Asia/Tokyo`）は `.env` から。
- **メソッドは同期（ブロッキング）**。Cog からは `asyncio.to_thread(...)` で呼ぶ（`cogs/calendar.py` 参照）。
- 未認証時は `_service()` が `RuntimeError` を投げる。呼び出し前に `is_available()` で確認する。
- `today_range` / `tomorrow_range` / `week_range`（週は月曜始まり）は timezone 付き `datetime` を返す。naive な値は設定タイムゾーンとして扱われる。
- `list_events(start, end)`: アカウントの **全カレンダー**（非表示含む）から取得し、開始時刻順に並べて `CalendarEvent` のリストで返す。
- `create_event(...)`: `calendar_id` のカレンダーに作成。
  - `start` / `end` は両方 `date`（終日）か両方 `datetime`。混在は `ValueError`。
  - 終日イベントの `end` は **包含**（API には +1 日して送る）。時刻付きで `end` 省略時は 1 時間。
  - バリデーションエラーの `ValueError` のメッセージはそのままユーザーに見せる前提なので日本語で書く。

## テスト

- `tests/test_google_calendar.py`。`build` を Fake に差し替えて API を叩かない。
