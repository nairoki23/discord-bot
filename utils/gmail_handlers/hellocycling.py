"""HELLO CYCLING（シェアサイクル）の通知メールを整形してDiscordへ送る。"""

import base64
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


HELLO_CYCLING_ADDRESS = "no-reply@hellocycling.jp"
JST = ZoneInfo("Asia/Tokyo")
FOOTER = "HELLO CYCLING"
MAX_DESCRIPTION = 1000
# 本文末尾の定型文（ここから後ろは送らない）
BOILERPLATE_START = "※本メールにお心当たりのない方は"


class HelloCyclingHandler(BaseHandler):
    """利用開始・返却完了は「項目：値」を、それ以外は本文をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = HELLO_CYCLING_ADDRESS

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = HelloCyclingHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = HelloCyclingHandler._extract_body(part)
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
    def _subject_body(subject):
        return subject.removeprefix("【HELLO CYCLING】").strip()

    @staticmethod
    def _items(text):
        """「項目：値」の行を {項目: 値} で返す。"""
        items = {}
        for line in text.splitlines():
            match = re.fullmatch(r"\s*([^：:\s]+)[：:](.+)", line)
            if match:
                items.setdefault(match.group(1), match.group(2).strip())
        return items

    @staticmethod
    def _parse_time(value):
        """「2026/10/28 18時38分」を datetime にする。読めなければ None。"""
        try:
            return datetime.strptime(value.strip(), "%Y/%m/%d %H時%M分").replace(tzinfo=JST)
        except ValueError:
            return None

    @classmethod
    def _with_relative(cls, value):
        moment = cls._parse_time(value)
        if moment is None:
            return value
        return f"{value}（<t:{int(moment.timestamp())}:R>）"

    @staticmethod
    def _period(value):
        """「2026/10/28 18時38分 〜 2026/10/28 18時56分」の同じ日付を省いて短くする。"""
        match = re.fullmatch(r"(\S+) (\S+) 〜 (\S+) (\S+)", value)
        if match and match.group(1) == match.group(3):
            return f"{match.group(1)} {match.group(2)} 〜 {match.group(4)}"
        return value

    @staticmethod
    def _notice_text(text):
        """宛名と末尾の定型文を除いた本文。"""
        text = text.split(BOILERPLATE_START, 1)[0]
        lines = [line.rstrip() for line in text.strip().splitlines()]
        if lines and lines[0].endswith("さま"):
            lines = lines[1:]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        text = text.rstrip("･").strip()
        if len(text) > MAX_DESCRIPTION:
            text = text[:MAX_DESCRIPTION] + "\n…(省略)"
        return text

    @staticmethod
    def _add_fields(embed, fields):
        for name, value in fields:
            if value:
                embed.add_field(name=name, value=value, inline=True)

    def _build_started(self, items):
        station = items.get("開始ステーション", "")
        description = f"{station}で利用を開始しました" if station else "利用を開始しました"
        embed = Embed(title="シェアサイクル利用開始", description=description, color=Color.green())
        self._add_fields(embed, [
            ("利用開始", self._with_relative(items.get("利用開始", ""))),
            ("開始ステーション", station),
            ("車両番号", items.get("車両番号", "")),
            ("決済方法", items.get("決済方法", "")),
        ])
        return "🚲", embed

    def _build_returned(self, items):
        amount = items.get("お支払い金額", "")
        description = f"返却しました（{amount}）" if amount else "返却しました"
        coupon = items.get("クーポン割引", "")
        if coupon.startswith("0円"):
            coupon = ""
        embed = Embed(title="シェアサイクル返却", description=description, color=Color.teal())
        self._add_fields(embed, [
            ("利用期間", self._period(items.get("ご利用期間", ""))),
            ("利用時間", items.get("ご利用時間", "")),
            ("お支払い金額", amount),
            ("クーポン割引", coupon),
            ("開始ステーション", items.get("開始ステーション", "")),
            ("返却ステーション", items.get("返却ステーション", "")),
            ("車両番号", items.get("車両番号", "")),
            ("決済方法", items.get("決済方法", "")),
            ("注文ID", items.get("注文ID", "")),
        ])
        return "✅", embed

    def _build_password_reset(self):
        # 本文に新しいパスワードが平文で入っているので、本文は送らない
        embed = Embed(
            title="パスワード再発行",
            description="パスワードの再発行を受け付けました。新しいパスワードはメールで確認してください",
            color=Color.orange(),
        )
        return "🔑", embed

    def _build_notice(self, subject, text):
        embed = Embed(
            title=self._subject_body(subject) or subject or "(件名なし)",
            description=self._notice_text(text) or "(本文なし)",
            color=Color.blue(),
        )
        return "📩", embed

    async def handle(self, details):
        subject = details.get("subject", "")
        payload = details.get("payload", {})
        text = self._extract_body(payload).replace("\r\n", "\n")
        kind = self._subject_body(subject)

        if kind == "利用開始":
            emoji, embed = self._build_started(self._items(text))
            content = f"{emoji} {embed.description}"
        elif kind == "返却完了":
            emoji, embed = self._build_returned(self._items(text))
            content = f"{emoji} {embed.description}"
        elif "パスワード再発行" in kind:
            emoji, embed = self._build_password_reset()
            content = f"{emoji} **{subject}**"
        else:
            emoji, embed = self._build_notice(subject, text)
            content = f"{emoji} **{subject or embed.title}**"

        embed.timestamp = self._received_at(payload)
        embed.set_footer(text=FOOTER)
        await self.sender(content=content, embed=embed)
