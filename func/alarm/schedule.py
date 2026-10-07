"""アラームの日時指定の解析と次回通知時刻の計算。

書式（日付と時刻は空白区切り、どちらか片方だけでもよい）:
  時刻: "M" / "H:M" / "H:M:S"（":M" や "H:" のように一部を空欄にできる）
  日付: "month/day" / "year/month/day"（"/day" や "year//day" のように一部を空欄にできる）
  各欄は数字、"*"（毎回）、空欄（未指定）。year は 令和n[年] / 平成n[年] / Rn / Hn も可。

未指定の欄の扱い:
  - 指定された最も細かい単位より細かい欄 → 最小値（時刻は 0、月・日は 1）
  - それ以外 → 最初の通知では「今か次」に合わせる。以降は
    - "*" より大きい欄 → その値に固定（例: "/* 12:50" は今月中だけ毎日 12:50）
    - "*" より細かい欄 → 固定せず毎回「次」に合わせる（例: "*//5" は毎月 5 日）
"""
import calendar
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

EVERY = "*"

FIELD_NAMES = ("year", "month", "day", "hour", "minute", "second")
_MIN = (1, 1, 1, 0, 0, 0)
_MAX = (9999, 12, 31, 23, 59, 59)

# 年が未指定のときに次の一致を探す範囲（2/29 などのために余裕を持たせる）
SEARCH_YEARS = 30

_ERA_START = {"令和": 2018, "r": 2018, "平成": 1988, "h": 1988}
_YEAR_RE = re.compile(r"(令和|平成|r|h)?(元|\d+)年?")


@dataclass(frozen=True)
class AlarmSpec:
    # year, month, day, hour, minute, second の順。int = 固定値、EVERY = 毎回、None = 未指定
    fields: tuple

    @property
    def repeats(self) -> bool:
        return EVERY in self.fields

    def first(self, now: datetime) -> datetime | None:
        """now より後の最初の通知時刻。該当なしなら None。"""
        return _next_match(now, [f if isinstance(f, int) else None for f in self.fields])

    def next_after(self, prev: datetime, first: datetime) -> datetime | None:
        """prev より後の次の通知時刻。繰り返さない・終了なら None。

        未指定の欄は、最も大きい "*" より大きければ first の値に固定し、細かければ固定しない。
        """
        if not self.repeats:
            return None
        coarsest_every = self.fields.index(EVERY)
        pattern = [
            getattr(first, name) if f is None and i < coarsest_every
            else None if f is None or f == EVERY
            else f
            for i, (name, f) in enumerate(zip(FIELD_NAMES, self.fields))
        ]
        return _next_match(prev, pattern)


def parse_alarm(text: str) -> AlarmSpec:
    """入力を AlarmSpec に変換する。解釈できなければ ValueError。"""
    tokens = unicodedata.normalize("NFKC", text).split()
    if not tokens:
        raise ValueError("日時が指定されていません")

    fields: list = [None] * 6
    has_date = has_time = False
    for token in tokens:
        if "/" in token:
            if has_date:
                raise ValueError("日付が複数あります")
            has_date = True
            parts = token.split("/")
            if len(parts) > 3:
                raise ValueError(f"日付の形式が不正です: {token}")
            offset = 3 - len(parts)  # month/day なら year を飛ばす
        else:
            if has_time:
                raise ValueError("時刻が複数あります")
            has_time = True
            parts = token.split(":")
            if len(parts) > 3:
                raise ValueError(f"時刻の形式が不正です: {token}")
            offset = 4 if len(parts) == 1 else 3  # コロンなしは分

        for i, part in enumerate(parts, start=offset):
            fields[i] = _parse_field(i, part)

    specified = [i for i, f in enumerate(fields) if f is not None]
    if not specified:
        raise ValueError("日時が指定されていません")
    finest = max(specified)
    for i in range(finest + 1, 6):
        fields[i] = _MIN[i]

    return AlarmSpec(tuple(fields))


def _parse_field(index: int, part: str):
    if part == "":
        return None
    if part == EVERY:
        return EVERY

    if index == 0:
        value = _parse_year(part)
    elif part.isdigit():
        value = int(part)
    else:
        raise ValueError(f"{FIELD_NAMES[index]} の値が不正です: {part}")

    if not _MIN[index] <= value <= _MAX[index]:
        raise ValueError(f"{FIELD_NAMES[index]} の値が範囲外です: {part}")
    return value


def _parse_year(part: str) -> int:
    match = _YEAR_RE.fullmatch(part.lower())
    if not match:
        raise ValueError(f"year の値が不正です: {part}")
    era, num = match.groups()
    if num == "元":
        if era is None:
            raise ValueError(f"year の値が不正です: {part}")
        n = 1
    else:
        n = int(num)
    return _ERA_START[era] + n if era else n


def _next_match(after: datetime, pattern: list) -> datetime | None:
    """after より後で pattern（int = 固定、None = 任意）に一致する最初の時刻（秒単位）。"""
    year, month, day, hour, minute, second = pattern
    try:
        t = after.replace(microsecond=0) + timedelta(seconds=1)
        last_year = year if year is not None else t.year + SEARCH_YEARS

        # 合わない欄があれば、その欄が次に一致する時刻まで進めてやり直す（t は単調増加）
        while t.year <= last_year:
            if year is not None and t.year < year:
                t = datetime(year, 1, 1)
            elif month is not None and t.month != month:
                t = datetime(t.year, month, 1) if t.month < month else datetime(t.year + 1, 1, 1)
            elif day is not None and t.day != day:
                if t.day < day <= calendar.monthrange(t.year, t.month)[1]:
                    t = datetime(t.year, t.month, day)
                else:
                    t = _next_month(t)
            elif hour is not None and t.hour != hour:
                t = t.replace(hour=hour, minute=0, second=0) if t.hour < hour else _next_day(t)
            elif minute is not None and t.minute != minute:
                t = t.replace(minute=minute, second=0) if t.minute < minute else _next_hour(t)
            elif second is not None and t.second != second:
                t = t.replace(second=second) if t.second < second else _next_minute(t)
            else:
                return t
    except (OverflowError, ValueError):
        # 9999 年を超える
        pass
    return None


def _next_month(t: datetime) -> datetime:
    return datetime(t.year + 1, 1, 1) if t.month == 12 else datetime(t.year, t.month + 1, 1)


def _next_day(t: datetime) -> datetime:
    return datetime(t.year, t.month, t.day) + timedelta(days=1)


def _next_hour(t: datetime) -> datetime:
    return t.replace(minute=0, second=0) + timedelta(hours=1)


def _next_minute(t: datetime) -> datetime:
    return t.replace(second=0) + timedelta(minutes=1)
