"""Times CAR（カーシェア）の予約通知メールを整形してDiscordへ送る。"""

import base64
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


TIMES_CAR_ADDRESS = "inquiry@share.timescar.jp"
RESERVATION_LIST_URL = "https://share.timescar.jp/view/reserve/list.jsp"
JST = ZoneInfo("Asia/Tokyo")

RESERVED_SUBJECT = "【Times CAR】予約登録完了"
CANCELED_SUBJECT = "【Times CAR】予約取消完了"


class TimesCarHandler(BaseHandler):
    """件名で予約登録／取消を判定し、予約内容をEmbedで送る。"""

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
        """「■項目名」の次行以降（次の■まで）を {項目名: [行, ...]} で返す。"""
        sections = {}
        label = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("■"):
                label = line[1:]
                sections[label] = []
            elif label is not None and line and not line.startswith(("※", "┗")):
                sections[label].append(line)
            else:
                label = None
        return sections

    @staticmethod
    def _with_relative(value):
        """「2026/10/06 11:45」に Discord の相対時刻表示を添える。"""
        try:
            moment = datetime.strptime(value, "%Y/%m/%d %H:%M").replace(tzinfo=JST)
        except ValueError:
            return value
        return f"{value}（<t:{int(moment.timestamp())}:R>）"

    def _parse(self, subject, text):
        if subject == RESERVED_SUBJECT:
            kind = "予約"
        elif subject == CANCELED_SUBJECT:
            kind = "取消"
        else:
            return None

        sections = self._sections(text)

        def first(label):
            lines = sections.get(label) or [""]
            return lines[0]

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
        }

    async def handle(self, details):
        subject = details.get("subject", "")
        text = self._extract_body(details.get("payload", {})).replace("\r\n", "\n")
        notification = self._parse(subject, text)
        if notification is None:
            await self._send_unknown(subject, text)
            return

        station = notification["station"] or "(ステーション不明)"
        if notification["kind"] == "予約":
            title, color, emoji = "カーシェア予約完了", Color.green(), "🚗"
            description = f"{station}で予約しました"
            start = self._with_relative(notification["start"])
        else:
            title, color, emoji = "カーシェア予約取消", Color.red(), "❌"
            description = f"{station}の予約を取り消しました"
            start = notification["start"]

        embed = Embed(title=title, description=description, color=color, url=RESERVATION_LIST_URL)
        embed.add_field(name="利用開始", value=start or "不明", inline=True)
        embed.add_field(name="返却予定", value=notification["end"] or "不明", inline=True)
        if notification["duration"]:
            embed.add_field(name="利用時間", value=notification["duration"], inline=True)
        if notification["station"]:
            value = notification["station"]
            if notification["station_url"]:
                value = f"[{value}]({notification['station_url']})"
            embed.add_field(name="ステーション", value=value, inline=True)
        if notification["car"]:
            embed.add_field(name="車両", value=notification["car"], inline=True)
        if notification["price"]:
            embed.add_field(name="予定料金", value=notification["price"], inline=True)
        if notification["number"]:
            embed.add_field(name="予約番号", value=notification["number"], inline=True)
        embed.set_footer(text="Times CAR")

        await self.sender(content=f"{emoji} {description}", embed=embed)

    async def _send_unknown(self, subject, text):
        """未対応の件名は本文をそのまま送る。"""
        text = text.strip() or "(本文なし)"
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"
        embed = Embed(title=subject or "(件名なし)", description=text, color=Color.blue())
        embed.set_footer(text="Times CAR（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
