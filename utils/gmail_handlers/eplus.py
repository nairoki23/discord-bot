"""イープラス（e+）の抽選申込・抽選結果メールを整形してDiscordへ送る。"""

import base64
import re
import unicodedata

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


EPLUS_ADDRESS = "info@eplus.co.jp"
HISTORY_URL = "https://eplus.jp/jyoukyou/"

APPLIED_SUBJECT = "【e+より】《重要》申込み完了・抽選結果確認期間のご案内"
RESULT_SUBJECT = "【e+より】抽選結果のご案内"
WON_SUBJECT = "【e+より】当選のご案内"
LOST_RESULT = "ご用意できませんでした"


class EplusHandler(BaseHandler):
    """件名で申込完了／抽選結果を判定し、公演と希望ごとの結果をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = EPLUS_ADDRESS

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = EplusHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = EplusHandler._extract_body(part)
            if text:
                return text
        return ""

    @staticmethod
    def _normalize(text):
        """全角英数・記号を半角にし、円記号として使われている \\ を ¥ に直す。"""
        text = unicodedata.normalize("NFKC", text.replace("\r\n", "\n"))
        return text.replace("\\", "¥")

    @staticmethod
    def _match(text, pattern, default=""):
        match = re.search(pattern, text)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else default

    def _choices(self, text):
        """<第N希望> ごとの抽選結果・公演日時・席種を返す（料金内訳の見出しは除く）。"""
        choices = []
        for match in re.finditer(r"<第(\d+)希望>\n((?:[ \t]+.+\n)+)", text):
            block = match.group(2)
            date = self._match(block, r"公演日時\s*:\s*(.+)")
            if not date:
                continue
            choices.append({
                "rank": match.group(1),
                "result": self._match(block, r"抽選結果\s+(.+)"),
                "date": date,
                # 「S指定 ¥13,200×2枚[チケット料金]+...」から席種とチケット代だけ残す
                "seat": self._match(block, r"席種・料金\s*:\s*([^\[\n]+)"),
            })
        return choices

    def _parse(self, subject, text):
        if subject not in (APPLIED_SUBJECT, RESULT_SUBJECT, WON_SUBJECT):
            return None
        choices = self._choices(text)
        if subject == APPLIED_SUBJECT:
            kind = "申込"
        elif subject == WON_SUBJECT or any(c["result"] == "当選" for c in choices):
            kind = "当選"
        elif choices and all(c["result"] == LOST_RESULT for c in choices):
            kind = "落選"
        else:
            kind = "要確認"
        return {
            "kind": kind,
            "event": self._match(text, r"公演名\s*:\s*(.+)", "不明"),
            "venue": self._match(text, r"会場名\s*:\s*(.+)"),
            "lottery": self._match(text, r"(?m)^◆(.+)"),
            "period": self._match(text, r"\[抽選結果確認期間\s*:\s*(.+?)\]"),
            "total": self._match(text, r"料金合計\s*:\s*(¥[\d,]+)"),
            "choices": choices,
        }

    async def handle(self, details):
        subject = details.get("subject", "")
        text = self._normalize(self._extract_body(details.get("payload", {})))
        notification = self._parse(subject, text)
        if notification is None:
            await self._send_unknown(subject, text)
            return

        event = notification["event"]
        title, color, description = {
            "申込": ("チケット抽選申込完了", Color.blue(), f"{event}に申し込みました"),
            "当選": ("抽選結果: 当選", Color.green(), f"{event}に当選しました！"),
            "落選": ("抽選結果: 落選", Color.light_grey(), f"{event}は落選でした"),
            "要確認": ("抽選結果: 要確認", Color.gold(),
                      f"{event}の抽選結果が届きました（申込み履歴で確認してください）"),
        }[notification["kind"]]
        embed = Embed(title=title, description=description, color=color, url=HISTORY_URL)

        if notification["venue"]:
            embed.add_field(name="会場", value=notification["venue"], inline=True)
        if notification["lottery"]:
            embed.add_field(name="受付", value=notification["lottery"], inline=True)
        if notification["kind"] == "申込" and notification["period"]:
            embed.add_field(name="結果確認期間", value=notification["period"], inline=False)
        for choice in notification["choices"]:
            result = {"当選": "（当選）", LOST_RESULT: "（落選）"}.get(choice["result"], "")
            embed.add_field(
                name=f"第{choice['rank']}希望{result}",
                value=f"{choice['date']}\n{choice['seat']}",
                inline=False,
            )
        if notification["kind"] in ("申込", "当選") and notification["total"]:
            label = "料金合計（最大）" if notification["kind"] == "申込" else "料金合計"
            embed.add_field(name=label, value=notification["total"], inline=True)
        embed.set_footer(text="イープラス")

        await self.sender(content=f"🎫 {description}", embed=embed)

    async def _send_unknown(self, subject, text):
        """未対応の件名（ログイン通知など）は本文をそのまま送る。"""
        text = text.strip() or "(本文なし)"
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"
        embed = Embed(title=subject or "(件名なし)", description=text, color=Color.blue())
        embed.set_footer(text="イープラス（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
