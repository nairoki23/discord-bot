# service/google/gmail

Gmail の新着メールを Pub/Sub で受け取り、送信元アドレスごとの handler に振り分ける。

## 構成

- `service.py` / `GmailService`: Gmail API クライアント生成、watch 登録、Pub/Sub 購読。handler 登録の窓口。
- `process.py` / `GmailProcess`: Pub/Sub 通知 → history 差分 → メッセージ取得 → handler 呼び出し。
- `handler_base.py` / `BaseHandler`: handler の基底クラス。
- `test_message.py`: 実メールを handler に通して動作確認する CLI（下記）。

## 受信の流れ

1. `setup_gmail_watch()`: `users.watch` で INBOX を `GCP_TOPIC_ID` に通知させ、初期 `historyId` を記録。
2. `start_listening()`: サービスアカウント鍵で `GCP_SUBSCRIPTION_ID` を購読。
3. Pub/Sub の callback は **別スレッド**で呼ばれるので、`asyncio.run_coroutine_threadsafe` で Bot のループに渡す（`GmailService.callback`）。
4. `sub_callback`: 即 ack → 前回の `historyId` から `history.list`（`messageAdded`）で差分取得。
5. `process_message`: 処理済み ID（直近 100 件）は飛ばす → `messages.get` で詳細取得 → `From` のアドレスが一致する handler の `handle(details)` を呼ぶ。

## handler

- `BaseHandler(sender)` を継承し、`self.address` に対象の送信元アドレスを設定、`async handle(details)` を実装する。
  - `sender` は Discord の送信関数（`channel.send` など）。
  - `details`: `id`, `from`, `subject`, `snippet`, `is_unread`, `payload`（Gmail API の生 payload）。
- 1 アドレスにつき handler は 1 つ。同じアドレスの再登録は `set_handler` が `False` を返す。
- handler の実装は `utils/gmail_handlers/` に置く（このディレクトリには置かない）。登録は `cogs/service/gmail.py` の `cog_load`。
  - 新しい handler を追加したら `test_message.py` の `register_handlers` も揃える。

## 注意点

- 状態（history ID、処理済み ID、handler）はメモリ上のみ。再起動中に届いたメールは処理されない。
- `history.list` が失敗（history 期限切れなど）した場合はその通知分を捨てる。
- ack は処理前に行うので、処理中の例外で再配信はされない。
- スコープは `gmail.readonly`。送信・ラベル変更などはできない（必要なら `service/google/auth.py` のスコープ追加と再認証が必要）。
- Gmail watch は Google 側で約 7 日で失効する。再登録は `cogs/service/gmail.py` の `setup_gmail_watch`（`tasks.loop(hours=24)`）が担当。

## 動作確認（`test_message.py`）

```
python -m service.google.gmail.test_message --list [--query 'from:...']
python -m service.google.gmail.test_message <message-id>
```

- 本番と同じ handler を登録し、送信先を `DEBUG_WEBHOOK` に差し替えて実行する（本番チャンネルには送られない）。
- 実際の Gmail アカウントを読むので、実行はユーザーに任せる。
