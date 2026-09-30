# CLAUDE.md

個人用 Discord Bot（授業予定・Google Calendar・Gmail 通知・宅配追跡・Y!mobile 残量・タイマーなど）。
詳細な仕様は `SPEC.md` を参照。ここには作業時に守るべきことだけを書く。

## 実行・テスト

- Python 3.10 以上（`X | None` 構文を使用）。依存は `requirements.txt`。
- 起動: リポジトリ直下で `python main.py`（`.env` と `.gcp_keys/` を相対パスで読むため、カレントディレクトリ必須）。
- テスト: リポジトリ直下で `python -m unittest`。
  - 既存の `venv/` は Python 3.9 かつ依存未インストールなので、そのままでは動かない。
  - Google API は Fake に差し替えてテストする（`tests/test_google_calendar.py` 参照）。実 API を叩くテストは書かない。
- 本番は systemd サービス `discordbot`（`manage.md`）。本番操作はしない。

## 秘密情報

- `.env` と `.gcp_keys/` は読まない・出力しない・コミットしない。
- 新しい環境変数を追加したら `.env.example` と `SPEC.md` の環境変数表を更新する。

## アーキテクチャ（レイヤーと依存方向）

```
cogs/     Discord との接点（コマンド・イベント）。1 ファイル = 1 Cog。func / service に依存してよい
func/     ドメインロジック。Discord に依存しない。service に依存してよい
service/  長寿命のシングルトン。service 同士は依存しない。取得は service/container.py 経由
utils/    共通ユーティリティ（権限チェック、デバッグ送信、Gmail handler）
```

- 依存方向を逆にしない（func から discord を import しない、service から cogs / func を import しない）。
- サービスは `service/container.py` の `get_timer()` / `get_google_auth()` / `get_gmail_service()` / `get_google_calendar_service()` で取得する。直接インスタンス化しない。
  - `get_timer()` 等は `set_loop()` 後でないと `RuntimeError`。モジュール import 時に呼ばない。
- Calendar と Gmail は同じ `GoogleAuth` を共有する。
- 各サービスの詳細: `service/timer/CLAUDE.md`、`service/google/CLAUDE.md`（認証・Calendar）、`service/google/gmail/CLAUDE.md`

## Cog を追加するとき

- `cogs/` 以下の `*.py` は `main.py` が自動ロードする。`_` 始まりはスキップ。
- 形式は `cogs/ping.py` に倣う: `commands.Cog` サブクラス + `discord.app_commands.command` + `async def setup(bot)`。
- 個人情報や外部アカウントに触るコマンドは、先頭で `utils.check_user.interaction_user(interaction)` を呼び、`False` なら return する。
- コマンドの `description` やユーザー向けメッセージは日本語。

## Gmail 通知ハンドラを追加するとき

- `utils/gmail_handlers/` に `service/google/gmail/handler_base.BaseHandler` を継承したクラスを作り、`handle(details)` を実装。
- `utils/gmail_handlers/__init__.py` に import を追加。
- 解析結果と Embed のテストを `tests/` に追加（`tests/test_credit_card_handler.py` 参照）。

## 開発フロー

- `main`: 本番で動いているもの / `dev`: 開発版
- 機能追加は `feat/*`、バグ修正は `fix/*` を `dev` から切り、`dev` へ PR を出す。
- `main` に直接コミット・PR しない。

## 既知の注意点

- 環境変数 `USER` は「コマンド実行許可ユーザー」と「BAN 対象」の両方に使われている（要確認。`SPEC.md` 参照）。
- `TEST_GUILD` は実質未使用で、スラッシュコマンドはグローバル同期。
