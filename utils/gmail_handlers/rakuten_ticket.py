"""楽天チケットの抽選申込・抽選結果メールを整形してDiscordへ送る。"""

import base64
import re

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


RAKUTEN_TICKET_ADDRESS = "support@ticket.rakuten.co.jp"
REVIEW_URL = "https://ticket.rakuten.co.jp/lots/review"

APPLIED_SUBJECT = "抽選申込受付完了のお知らせ　【楽天チケット】"
RESULT_SUBJECT = "【楽天チケット】 抽選結果のご案内"
LOST_PHRASE = "チケットをご用意することができませんでした"

# (タイトル, 色, 本文の動詞)
RESULTS = {
    "落選": ("抽選結果: 落選", Color.light_grey(), "は落選でした"),
    "当選": ("抽選結果: 当選", Color.green(), "に当選しました！"),
    "要確認": ("抽選結果: 要確認", Color.gold(), "の抽選結果が届きました（結果確認ページで確認してください）"),
}


class RakutenTicketHandler(BaseHandler):
    """件名で申込完了／抽選結果を判定し、公演と希望内容をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = RAKUTEN_TICKET_ADDRESS

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = RakutenTicketHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = RakutenTicketHandler._extract_body(part)
            if text:
                return text
        return ""

    @staticmethod
    def _match(text, pattern, default="不明"):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    @staticmethod
    def _choices(text):
        """【第N希望】ごとの公演日・会場・申込内容を返す。"""
        return [
            {"rank": rank, "date": date.strip(), "venue": venue.strip(), "seat": seat.strip()}
            for rank, date, venue, seat in re.findall(
                r"【第(\d+)希望】\n公演日:(.+)\n会場:(.+)\n申込内容\n(.+)", text
            )
        ]

    @staticmethod
    def _result(text):
        if LOST_PHRASE in text:
            return "落選"
        if "ご用意することができました" in text or "当選" in text:
            return "当選"
        return "要確認"

    def _parse(self, subject, text):
        if subject == APPLIED_SUBJECT:
            kind = "申込"
        elif subject == RESULT_SUBJECT:
            kind = self._result(text)
        else:
            return None
        return {
            "kind": kind,
            "event": self._match(text, r"■イベント名:\s*(.+)"),
            "lottery": self._match(text, r"■受付名称:\s*(.+)", ""),
            "announce": self._match(text, r"■抽選結果発表日時:\s*(.+)", ""),
            "receipt": self._match(text, r"■受付番号\n(\S+)", ""),
            "url": self._match(text, r"■抽選結果確認ページ:\s*(\S+)", REVIEW_URL),
            "choices": self._choices(text),
        }

    async def handle(self, details):
        subject = details.get("subject", "")
        text = self._extract_body(details.get("payload", {})).replace("\r\n", "\n")
        notification = self._parse(subject, text)
        if notification is None:
            await self._send_unknown(subject, text)
            return

        event = notification["event"]
        if notification["kind"] == "申込":
            embed = Embed(
                title="チケット抽選申込完了",
                description=f"{event}に申し込みました",
                color=Color.blue(),
                url=notification["url"],
            )
        else:
            title, color, verb = RESULTS[notification["kind"]]
            embed = Embed(
                title=title, description=f"{event}{verb}", color=color, url=notification["url"]
            )

        if notification["lottery"]:
            embed.add_field(name="受付", value=notification["lottery"], inline=True)
        if notification["kind"] == "申込" and notification["announce"]:
            embed.add_field(name="結果発表", value=notification["announce"], inline=True)
        for choice in notification["choices"]:
            embed.add_field(
                name=f"第{choice['rank']}希望",
                value=f"{choice['date']} / {choice['venue']}\n{choice['seat']}",
                inline=False,
            )
        if notification["receipt"]:
            embed.add_field(name="受付番号", value=notification["receipt"], inline=True)
        embed.set_footer(text="楽天チケット")

        await self.sender(content=f"🎫 {embed.description}", embed=embed)

    async def _send_unknown(self, subject, text):
        """未対応の件名は本文をそのまま送る。"""
        text = text.strip() or "(本文なし)"
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"
        embed = Embed(title=subject or "(件名なし)", description=text, color=Color.blue())
        embed.set_footer(text="楽天チケット（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
