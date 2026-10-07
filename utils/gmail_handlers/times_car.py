"""Times CAR（カーシェア）の通知メールを整形してDiscordへ送る。"""

import base64
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


TIMES_CAR_ADDRESS = "inquiry@share.timescar.jp"
RESERVATION_LIST_URL = "https://share.timescar.jp/view/reserve/list.jsp"
MYPAGE_URL = "https://share.timescar.jp/mypage"
JST = ZoneInfo("Asia/Tokyo")

# 件名から「【Times CAR】」を除いた部分 → 通知の種類
SUBJECT_KINDS = {
    "予約登録完了": "予約",
    "予約変更完了": "変更",
    "予約取消完了": "取消",
    "返却確認": "返却確認",
    "返却証": "返却証",
    "給油割引が適用されました": "給油割引",
}
# 通知しない件名（「【Times CAR】」を除いた部分）
IGNORED_SUBJECTS = {
    "認証コード",
    "「アプリ解施錠機能」利用登録完了のお知らせ",
    "スグ乗り入会　お申し込み受付完了",
    "スグ乗り入会　会員登録完了のご案内",
}


class TimesCarHandler(BaseHandler):
    """件名で通知の種類を判定し、「■項目名」ごとの内容をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = TIMES_CAR_ADDRESS

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = TimesCarHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = TimesCarHandler._extract_body(part)
            if text:
                return text
        return ""

    @staticmethod
    def _sections(text):
        """「■項目名」の次行以降を {項目名: [行, ...]} で返す。※・罫線・次の■で区切る。"""
        sections = {}
        label = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("■"):
                label = line[1:]
                sections[label] = []
            elif label is None or not line:
                continue
            elif line.startswith(("※", "┗", "―", "--")):
                label = None
            else:
                sections[label].append(line)
        return sections

    @staticmethod
    def _subject_body(subject):
        return subject.removeprefix("【Times CAR】").strip()

    @staticmethod
    def _received_at(payload):
        """Date ヘッダの受信日時。読めなければ None。"""
        for header in payload.get("headers", []):
            if header.get("name", "").lower() == "date":
                try:
                    return parsedate_to_datetime(header["value"])
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _with_relative(value):
        """「2026/10/06 11:45」に Discord の相対時刻表示を添える。"""
        try:
            moment = datetime.strptime(value, "%Y/%m/%d %H:%M").replace(tzinfo=JST)
        except ValueError:
            return value
        return f"{value}（<t:{int(moment.timestamp())}:R>）"

    @staticmethod
    def _period(value):
        """「2026/10/06 11:45 - 2026/10/06 12:56」の同じ日付を省いて短くする。"""
        match = re.fullmatch(r"(\S+) (\S+) - (\S+) (\S+)", value)
        if match and match.group(1) == match.group(3):
            return f"{match.group(1)} {match.group(2)} - {match.group(4)}"
        return value

    def _parse(self, subject, text):
        kind = SUBJECT_KINDS.get(self._subject_body(subject))
        if kind is None:
            return None
        sections = self._sections(text)

        def first(label):
            return (sections.get(label) or [""])[0]

        station_lines = sections.get("ステーション", [])
        return {
            "kind": kind,
            "number": first("予約番号"),
            "station": station_lines[0] if station_lines else "",
            "station_url": next((l for l in station_lines[1:] if l.startswith("https://")), None),
            "car": first("車両"),
            "start": first("利用開始日時"),
            "end": first("返却予定日時"),
            "duration": first("利用予定時間"),
            "price": first("課金予定料金"),
            "minutes_left": self._match(text, r"あと(\d+分)で返却時間"),
            "used": self._period(first("利用時間")),
            "distance": first("走行距離"),
            "max_speed": first("最高速度"),
            "time_fee": first("時間料金"),
            "distance_fee": first("距離料金"),
            "penalty": first("ペナルティ金額"),
            "total": first("合計金額"),
            "fuel_discount": first("給油割引金額"),
            "total_discount": first("合計割引金額"),
        }

    @staticmethod
    def _match(text, pattern, default=""):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    @staticmethod
    def _add_fields(embed, fields):
        for name, value in fields:
            if value:
                embed.add_field(name=name, value=value, inline=True)

    def _station_field(self, notification):
        value = notification["station"]
        if value and notification["station_url"]:
            value = f"[{value}]({notification['station_url']})"
        return ("ステーション", value)

    def _build(self, n):
        """通知の種類ごとに (絵文字, Embed) を組み立てる。"""
        station = n["station"] or "(ステーション不明)"
        kind = n["kind"]

        if kind in ("予約", "変更", "取消"):
            title, color, emoji, description = {
                "予約": ("カーシェア予約完了", Color.green(), "🚗", f"{station}で予約しました"),
                "変更": ("カーシェア予約変更", Color.blurple(), "🔁", f"{station}の予約を変更しました"),
                "取消": ("カーシェア予約取消", Color.red(), "❌", f"{station}の予約を取り消しました"),
            }[kind]
            start = n["start"] if kind == "取消" else self._with_relative(n["start"])
            embed = Embed(title=title, description=description, color=color, url=RESERVATION_LIST_URL)
            self._add_fields(embed, [
                ("利用開始", start or "不明"),
                ("返却予定", n["end"] or "不明"),
                ("利用時間", n["duration"]),
                self._station_field(n),
                ("車両", n["car"]),
                ("予定料金", n["price"]),
                ("予約番号", n["number"]),
            ])
            return emoji, embed

        if kind == "返却確認":
            description = f"あと{n['minutes_left']}で返却時間です" if n["minutes_left"] else "まもなく返却時間です"
            embed = Embed(title="返却時間のお知らせ", description=description, color=Color.orange(), url=RESERVATION_LIST_URL)
            self._add_fields(embed, [
                ("返却予定", self._with_relative(n["end"]) or "不明"),
                self._station_field(n),
                ("車両", n["car"]),
                ("予約番号", n["number"]),
            ])
            return "⏰", embed

        if kind == "返却証":
            description = f"返却しました（合計 {n['total']}）" if n["total"] else "返却しました"
            penalty = n["penalty"] if n["penalty"] and not n["penalty"].startswith("0円") else ""
            embed = Embed(title="カーシェア返却", description=description, color=Color.teal())
            self._add_fields(embed, [
                ("利用時間", n["used"]),
                ("走行距離", n["distance"]),
                ("最高速度", n["max_speed"]),
                ("時間料金", n["time_fee"]),
                ("距離料金", n["distance_fee"]),
                ("ペナルティ", penalty),
                ("合計金額", n["total"]),
                self._station_field(n),
                ("車両", n["car"]),
                ("予約番号", n["number"]),
            ])
            return "✅", embed

        amount = n["fuel_discount"] or n["total_discount"]
        description = f"給油割引（{amount}）が適用されました" if amount else "給油割引が適用されました"
        embed = Embed(title="給油割引", description=description, color=Color.gold(), url=MYPAGE_URL)
        self._add_fields(embed, [
            ("給油割引", n["fuel_discount"]),
            ("合計割引", n["total_discount"]),
            ("予約番号", n["number"]),
        ])
        return "⛽", embed

    async def handle(self, details):
        subject = details.get("subject", "")
        if self._subject_body(subject) in IGNORED_SUBJECTS:
            return
        payload = details.get("payload", {})
        text = self._extract_body(payload).replace("\r\n", "\n")
        received_at = self._received_at(payload)
        notification = self._parse(subject, text)
        if notification is None:
            await self._send_unknown(subject, text, received_at)
            return

        emoji, embed = self._build(notification)
        embed.timestamp = received_at
        embed.set_footer(text="Times CAR")
        await self.sender(content=f"{emoji} {embed.description}", embed=embed)

    async def _send_unknown(self, subject, text, received_at=None):
        """未対応の件名は本文をそのまま送る。"""
        text = text.strip() or "(本文なし)"
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"
        embed = Embed(
            title=subject or "(件名なし)", description=text, color=Color.blue(), timestamp=received_at
        )
        embed.set_footer(text="Times CAR（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
