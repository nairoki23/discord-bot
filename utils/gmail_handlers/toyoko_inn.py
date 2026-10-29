"""東横INN の予約メールを整形してDiscordへ送る。"""

import base64
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


# 送信元はホテルごとに「<ホテル名>@wm.toyoko-inn.com」なので部分一致で受ける
TOYOKO_INN_ADDRESS = "@wm.toyoko-inn.com"
RESERVATION_URL = "https://www.toyoko-inn.com/mypage/reservation"
JST = ZoneInfo("Asia/Tokyo")
FOOTER = "東横INN"
MAX_DESCRIPTION = 500


class ToyokoInnHandler(BaseHandler):
    """件名で予約・変更・キャンセルを判定し、「・項目：値」の内容をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = TOYOKO_INN_ADDRESS
        self.partial_match = True

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = ToyokoInnHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = ToyokoInnHandler._extract_body(part)
            if text:
                return text
        return ""

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
    def _kind(subject):
        if "予約キャンセル確認" in subject:
            return "キャンセル"
        if "予約変更確認" in subject:
            return "変更"
        if "予約確認" in subject:
            return "予約"
        return None

    @staticmethod
    def _items(text):
        """「・項目：値」の行を {項目: 値} で返す。"""
        items = {}
        for line in text.splitlines():
            match = re.fullmatch(r"\s*・([^：:]+)[：:]\s*(.+)", line)
            if match:
                items.setdefault(match.group(1).strip(), match.group(2).strip())
        return items

    @staticmethod
    def _hotel(text):
        """「▼ご宿泊ホテル」の罫線の次の行（ホテル名）と、ホテル詳細ページの URL。"""
        lines = [line.strip() for line in text.splitlines()]
        try:
            start = lines.index("▼ご宿泊ホテル")
        except ValueError:
            return "", None
        name, url = "", None
        for line in lines[start + 1:]:
            if line.startswith("▼"):
                break
            if not line or line.startswith("━") or line == "⠀":
                continue
            if not name:
                name = line
            elif line.startswith("https://www.toyoko-inn.com/search/detail/"):
                url = line
        return name, url

    @staticmethod
    def _hotel_from_subject(subject):
        match = re.match(r"\[([^\]]+)\]", subject)
        if match:
            return match.group(1)
        return subject.split(" ", 1)[0] if " " in subject else ""

    @staticmethod
    def _stay_with_relative(stay, checkin):
        """「2026年11月7日(土) より 1 泊」にチェックイン予定（なければ当日0時）の相対時刻を添える。"""
        date = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", stay)
        if not date:
            return stay
        time = re.match(r"(\d{1,2}):(\d{2})", checkin)
        hour, minute = (int(time.group(1)), int(time.group(2))) if time else (0, 0)
        moment = datetime(*map(int, date.groups()), hour, minute, tzinfo=JST)
        return f"{stay}（<t:{int(moment.timestamp())}:R>）"

    @staticmethod
    def _amount(value):
        """「10,911円（消費税/VAT/宿泊税込）」→「10,911円」。"""
        return value.split("（", 1)[0].strip()

    @staticmethod
    def _add_fields(embed, fields):
        for name, value in fields:
            if value:
                embed.add_field(name=name, value=value, inline=True)

    def _build(self, kind, subject, text):
        items = self._items(text)
        hotel, hotel_url = self._hotel(text)
        hotel = hotel or self._hotel_from_subject(subject) or "東横INN"
        stay = items.get("ご宿泊日", "")
        title, color, emoji, description = {
            "予約": ("ホテル予約完了", Color.green(), "🏨", f"{hotel}を予約しました"),
            "変更": ("ホテル予約変更", Color.blurple(), "🔁", f"{hotel}の予約を変更しました"),
            "キャンセル": ("ホテル予約キャンセル", Color.red(), "❌", f"{hotel}の予約をキャンセルしました"),
        }[kind]
        if kind != "キャンセル":
            stay = self._stay_with_relative(stay, items.get("チェックイン予定時刻", ""))
        embed = Embed(
            title=title,
            description=description,
            color=color,
            url=None if kind == "キャンセル" else RESERVATION_URL,
        )
        self._add_fields(embed, [
            ("宿泊日", stay or "不明"),
            ("チェックイン", items.get("チェックイン予定時刻", "")),
            ("ホテル", f"[{hotel}]({hotel_url})" if hotel_url else hotel),
            ("部屋／プラン", items.get("ルームタイプ／プラン", "")),
            ("人数", items.get("ご利用人数（1部屋あたり）", "")),
            ("合計金額", self._amount(items.get("合計金額", ""))),
            ("支払方法", items.get("支払方法", "")),
            ("予約番号", items.get("予約番号", "")),
        ])
        return emoji, embed

    async def handle(self, details):
        subject = details.get("subject", "")
        payload = details.get("payload", {})
        text = self._extract_body(payload).replace("\r\n", "\n")
        received_at = self._received_at(payload)
        kind = self._kind(subject)
        if kind is None:
            await self._send_unknown(subject, text, received_at)
            return

        emoji, embed = self._build(kind, subject, text)
        embed.timestamp = received_at
        embed.set_footer(text=FOOTER)
        await self.sender(content=f"{emoji} {embed.description}", embed=embed)

    async def _send_unknown(self, subject, text, received_at=None):
        """未対応の件名は本文をそのまま送る（宛名の行は除く）。"""
        lines = [line for line in text.strip().splitlines() if not line.strip().endswith("様")]
        text = "\n".join(lines).strip() or "(本文なし)"
        if len(text) > MAX_DESCRIPTION:
            text = text[:MAX_DESCRIPTION] + "\n…(省略)"
        embed = Embed(
            title=subject or "(件名なし)", description=text, color=Color.blue(), timestamp=received_at
        )
        embed.set_footer(text=f"{FOOTER}（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
