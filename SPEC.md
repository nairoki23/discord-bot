# discord-bot 仕様書

個人用 Discord Bot。学校の授業予定、Google Calendar、Gmail 通知（カード利用通知、PayPayほけん、楽天チケット、イープラス、Yahoo!フリマなど）、宅配便追跡、Y!mobile のデータ残量確認、タイマーなど、身の回りの情報を Discord に集約する。

> この文書は 2026-09-26 時点のコード（`main` / `96acb65`）から読み取った現状の仕様。
> 「こうあるべき」ではなく「今こう動いている」を書いている。意図と違う箇所は [既知の問題・要確認](#既知の問題要確認) を参照。

---

## 1. 実行環境・運用

| 項目 | 内容 |
|---|---|
| 言語 | Python 3.10 以上（`X \| None` 型構文を使用しているため 3.9 では動かない） |
| 主要ライブラリ | discord.py ≥ 2.3, google-api-python-client, google-auth-oauthlib, google-cloud-pubsub, aiohttp, beautifulsoup4, requests, nanoid, python-dotenv |
| 起動 | `python main.py`（**カレントディレクトリがリポジトリ直下である必要あり**。`.env` と JSON を相対パスで読む） |
| 本番運用 | systemd サービス `discordbot`（`manage.md` 参照: `sudo systemctl start/status/restart discordbot`） |
| 秘密情報 | `.env`、`.gcp_keys/`（OAuth クライアント、ユーザートークン、Pub/Sub 用サービスアカウント鍵）。どちらも git 管理外 |

### 1.1 環境変数（`.env`）

| キー | 用途 | 使用箇所 |
|---|---|---|
| `DISCORD_TOKEN` | Bot トークン | `main.py` |
| `MAIN_GUILD` | メインのギルド ID。`private/cogs` のコマンドはこのギルドにのみ登録する（未設定なら登録しない。後述） | `main.py` |
| `USER` | カンマ区切りのユーザー ID。**コマンド実行許可ユーザー** かつ **BAN 対象** の両方に使われている（要確認） | `utils/check_user.py`, `cogs/ban.py`, `cogs/data_usage.py` |
| `PHONE_NUMBER` / `YMOBILE_PASSWORD` | Y!mobile ログイン情報 | `cogs/data_usage.py` |
| `GMAIL_TRACK_ADDRESSES` | 起動時に自動で追跡するメールアドレス（カンマ区切り） | `cogs/service/gmail.py` |
| `GCP_PROJECT_ID` / `GCP_TOPIC_ID` / `GCP_SUBSCRIPTION_ID` | Gmail watch → Pub/Sub の設定 | `service/google/gmail/service.py` |
| `GOOGLE_SERVICE_ACCOUNT_PATH` | Pub/Sub 購読用サービスアカウント鍵（既定 `./.gcp_keys/credentials.json`。`.env.example` には未記載） | 同上 |
| `GOOGLE_OAUTH_CLIENT_PATH` | OAuth クライアント JSON（既定 `./.gcp_keys/OAuthClient.json`） | `service/google/auth.py` |
| `GOOGLE_USER_TOKEN_PATH` | 取得したユーザートークンの保存先（既定 `./.gcp_keys/token.json`、パーミッション 600） | 同上 |
| `GOOGLE_OAUTH_REDIRECT_URI` | OAuth リダイレクト先（既定 `https://nairoki.dev`） | 同上 |
| `GOOGLE_CALENDAR_ID` | `/calendar_add` の登録先（既定 `primary`） | `service/container.py` |
| `GOOGLE_CALENDAR_TIMEZONE` | カレンダーのタイムゾーン（既定 `Asia/Tokyo`） | `cogs/calendar.py`, `service/container.py` |
| `DEBUG_WEBHOOK` | デバッグ送信用 Webhook（Gmail handler のテストスクリプトで使用） | `utils/debug.py` |

### 1.2 チャンネル / スレッド ID（`channels.json`）

通知先のチャンネル ID・スレッド ID は `.env` ではなくリポジトリ直下の `channels.json` で管理する（git 管理外）。
`channels.example.json` をコピーして作る。読み込みは `utils/channels.py` の `get_channel_id(key)`。
値は数値・文字列どちらでもよく、`null` または未記載なら未設定扱い。ファイルが無い場合は全キー未設定として起動する。

| キー | 用途 | 使用箇所 |
|---|---|---|
| `notification_channel_id` | 通知の送信先チャンネル（Gmail 通知、明日の予定） | `cogs/service/gmail.py`, `cogs/calendar.py` |
| `credit_card_thread_id` | カード利用通知の送信先（未設定なら `notification_channel_id`） | `cogs/service/gmail.py` |
| `car_channel_id` | car チャンネル（未使用・予約） | なし |

---

## 2. ディレクトリ構成とレイヤー

```
main.py                 Bot 本体。cogs/ 以下を自動ロードし、スラッシュコマンドを同期
cogs/                   Discord との接点（コマンド・イベントリスナー）。1 ファイル = 1 Cog。funcやserviceに依存
  service/              Google 系の Cog（google_auth.py, gmail.py）
func/                   機能ごとのドメインロジック。Discordに依存しない、serviceに依存する（スクレイピング、予定計算など）
  class_schedule/       授業日程 JSON とその計算
  tracking/             宅配追跡（fetch/ = 業者別スクレイパ, model/ = データ型）
  ymobile/              Y!mobile マイページのスクレイピング
service/                長寿命のサービス。service同士依存しない。（シングルトン）
  container.py          サービスロケータ（get_timer, get_google_auth, get_gmail_service, get_google_calendar_service）
  timer/                asyncio ベースのジョブスケジューラ
  google/               OAuth 共通認証、Calendar、Gmail（Pub/Sub 受信 + handler 振り分け）
utils/                  共通ユーティリティ
  check_user.py         実行権限チェック
  debug.py              Webhook へのデバッグ送信
  gmail_handlers/       Gmail 受信メールの処理ハンドラ群
tests/                  unittest
private/                非公開モジュール（private リポジトリの git submodule。未取得なら空）
  cogs/                 main.py が自動ロード（private.cogs.xxx）
  func/                 非公開のドメインロジック
```

`private/` の取り扱い（依存方向、コミット手順、デプロイ）は `submodule.md` を参照。

### 2.1 起動フロー（`main.py`）

1. `.env` を読み込む。
2. `MyBot`（`commands.Bot`, prefix `!`, `Intents.all()`）を生成。
3. `main()` で `set_loop(bot.loop)` を呼び、サービスコンテナにイベントループを渡す（これ以前に `get_timer()` 等を呼ぶと `RuntimeError`）。
4. `setup_hook` で `cogs/`、続いて `private/cogs/` 以下の `*.py` を再帰的に探索して `load_extension`。
   - `_` で始まるファイルはスキップ。
   - ロード失敗は `print` するだけで起動は継続。
5. `private/cogs` のロードで増えたコマンドをグローバルから外して `MAIN_GUILD` に付け替え、`tree.sync()`（グローバル同期: public）と `tree.sync(guild=MAIN_GUILD)`（ギルド同期: private）を実行。

### 2.2 サービスコンテナ（`service/container.py`）

各サービスは遅延生成のシングルトン。

| 関数 | 返すもの | 前提 |
|---|---|---|
| `get_timer()` | `TimerService` | `set_loop` 済み |
| `get_google_auth()` | `GoogleAuth` | なし |
| `get_gmail_service(creds)` | `GmailService` | 初回は `creds`（`get_creds` 関数）と loop が必要 |
| `get_google_calendar_service()` | `GoogleCalendarService` | なし（`GoogleAuth` を共有） |

Calendar と Gmail は同じ `GoogleAuth` を共有するので、一度の OAuth で両方使える。

### 2.3 権限チェック

`utils/check_user.interaction_user(interaction)` が `USER` に含まれるユーザーかを判定し、含まれなければ「実行権限がありません」を ephemeral で返して `False`。
付いているコマンド: `/today` `/calendar_week` `/calendar_add` `/usage` `/google_auth` `/gmail_*` 全部、`/status`。
**付いていない**コマンド: `/ping` `/class` 系 `/timer` 系 `/tracking` 系 `/spending`。

## 4. テスト

- `tests/test_google_calendar.py`: Calendar サービス（週範囲、イベント解析、作成、バリデーション、コンテナの共有）と `parse_local_datetime` / `format_events`。Google API は Fake で差し替え。
- `tests/test_credit_card_handler.py`: 3 社のカード通知の解析結果と Embed レイアウト、対象外件名の無視。
- private のテストは `private/tests/` に置き、`python -m unittest discover -s private/tests -t .` で実行。
- `tests/test_credit_card_handler.py`: 3 社のカード通知の解析結果と Embed レイアウト、カードごとの色、通知後の既読付け、対象外件名の無視。
- `tests/test_paypay_insurance_handler.py`: PayPayほけんの加入完了・終了予定通知の解析結果と Embed、未対応件名のテキスト送信。
- `tests/test_rakuten_ticket_handler.py`: 楽天チケットの抽選申込・抽選結果（落選／当選）の解析結果と Embed、個人情報を載せないこと、未対応件名のテキスト送信。
- `tests/test_eplus_handler.py`: イープラスの申込完了・当選・落選の解析結果（全角の正規化、希望ごとの結果、料金内訳の除外）と Embed、未対応件名のテキスト送信。
- `tests/test_paypay_fleamarket_handler.py`: Yahoo!フリマの取引メッセージ・購入・発送通知の解析結果と Embed（計測用クエリを外したリンク）、未対応件名のテキスト送信。
- 実行: リポジトリ直下で `python -m unittest`（`.env` の `USER` などが読める状態で、Python 3.10+ と依存パッケージが必要）。
  - 現在の `venv/` は Python 3.9 で依存も未インストールのため、そのままでは失敗する。

# 5. 開発フロー
main branch:うごいてるやつ
dev branch:開発版
feat/* :機能追加
fix/* :バグ修正
など
機能追加やバグ修正はdevからブランチ切ってdevにPR