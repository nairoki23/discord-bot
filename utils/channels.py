"""channels.json から通知先のチャンネル / スレッド ID を読む。"""

import json
from pathlib import Path

CHANNELS_PATH = Path("./channels.json")


def load_channels(path: Path = CHANNELS_PATH) -> dict:
    if not path.exists():
        print(f"{path} が見つかりません。channels.example.json をコピーして作成してください")
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


channels = load_channels()


def get_channel_id(key: str) -> int | None:
    """未設定（キーなし・null・空文字）なら None。ID は数値でも文字列でもよい。"""
    value = channels.get(key)
    if value in (None, ""):
        return None
    return int(value)
