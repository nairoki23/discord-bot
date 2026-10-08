# service/timer

asyncio ベースのジョブスケジューラ。`TimerService`（`timer.py`）と `Job`（`job.py`）。

## 使い方

- 取得は `service.container.get_timer()`。`set_loop()` 前に呼ぶと `RuntimeError` なので、Cog の `__init__` 以降で呼ぶ。
- `schedule(when, cb, jitter=None) -> job_id`
  - `when`: 初回実行時刻（naive `datetime`。`datetime.now()` と比較される）。
  - `cb`: 引数なしの callable。同期・async どちらでもよい。
  - `jitter`: `timedelta`。実行時刻に `0〜jitter` 秒のランダムな遅延を足す（毎回適用）。
- `cancel(job_id)` / `get_next_run(job_id)` / `get_status(job_id)` / `list_jobs()`

## コールバックの戻り値で繰り返しを制御する

- `None` を返す → 終了（ジョブは削除される）。
- `datetime` を返す → その時刻に再実行（定期実行はこれで実現する）。
- 例外を投げる → `print` して終了。リトライはしない。

## 注意点

- 状態はメモリ上のみ。Bot を再起動するとジョブはすべて消える。
- 完了・キャンセルされたジョブは `jobs` から即削除されるので、終了後に `get_status` すると `None`。
- 時刻は naive datetime（ローカル時刻）前提。timezone 付きの `datetime` を渡すと `datetime.now()` との減算で落ちる。
- 利用箇所: `cogs/timer.py`（`/timer`）、`cogs/alarm.py`（`/alarm`）、`cogs/calendar.py`（明日の予定通知）、`func/tracking/track.py`（追跡の定期取得）。
