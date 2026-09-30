"""PayPayほけん（あんしんドライブ等）の通知メールを整形してDiscordへ送る。"""

import base64
import html
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


PAYPAY_INSURANCE_ADDRESS = "paypay-master@mail.paypay-insurance.co.jp"
JST = ZoneInfo("Asia/Tokyo")

ENROLLED_SUBJECT = "加入手続き完了のご連絡"
ENDING_SUBJECT = "保険期間終了予定のお知らせ"


class PayPayInsuranceHandler(BaseHandler):
    """件名で通知の種類を判定し、契約情報を抜き出してEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = PAYPAY_INSURANCE_ADDRESS

    @staticmethod
    def _extract_html(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            text = PayPayInsuranceHandler._extract_html(part)
            if text:
                return text
        return ""

    @staticmethod
    def _html_to_text(raw):
        raw = re.sub(r"(?is)<(head|style|script)\b.*?</\1>", "", raw)
        raw = re.sub(r"(?i)<br\s*/?>", "\n", raw)
        text = html.unescape(re.sub(r"<[^>]+>", "", raw))
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())

    @staticmethod
    def _link(raw, label):
        """「■{label}は<a href=...>こちら</a>」形式のリンク先を返す。"""
        match = re.search(rf"■{label}は<a href=\"([^\"]+)\"", raw)
        return html.unescape(match.group(1)) if match else None

    @staticmethod
    def _match(text, pattern, default="不明"):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    @staticmethod
    def _with_relative(value):
        """「2026/09/29 10:00」に Discord の相対時刻表示を添える。"""
        try:
            moment = datetime.strptime(value, "%Y/%m/%d %H:%M").replace(tzinfo=JST)
        except ValueError:
            return value
        return f"{value}（<t:{int(moment.timestamp())}:R>）"

    def _parse(self, subject, raw):
        text = self._html_to_text(raw)
        policy = self._match(text, r"対象のご契約：\s*(\S+)")
        if subject == ENROLLED_SUBJECT:
            return {
                "kind": "加入完了",
                "plan": self._match(text, r"この度は、(.+?)にご加入"),
                "policy": policy,
                "start": self._match(text, r"保険開始日：\s*(.+)"),
                "end": self._match(text, r"保険終了日：\s*(.+)"),
                "link_label": "契約内容の確認",
                "link": self._link(raw, "ご契約内容の確認・変更"),
            }
        if subject == ENDING_SUBJECT:
            return {
                "kind": "終了予定",
                "plan": self._match(text, r"ご契約をいただいております(.+?)の保険期間が"),
                "policy": policy,
                "end": self._match(text, r"の保険期間が([\d/]+ [\d:]+)をもって終了予定"),
                "link_label": "契約延長の手続き",
                "link": self._link(raw, "契約延長の手続き"),
            }
        return None

    async def handle(self, details):
        subject = details.get("subject", "")
        raw = self._extract_html(details.get("payload", {}))
        notification = self._parse(subject, raw)
        if notification is None:
            await self._send_unknown(subject, self._html_to_text(raw))
            return

        if notification["kind"] == "加入完了":
            embed = Embed(
                title="保険加入完了",
                description=f"{notification['plan']}に加入しました",
                color=Color.green(),
            )
            embed.add_field(name="開始", value=notification["start"], inline=True)
            embed.add_field(
                name="終了", value=self._with_relative(notification["end"]), inline=True
            )
        else:
            embed = Embed(
                title="保険期間終了予定",
                description=f"{notification['plan']}がまもなく終了します",
                color=Color.orange(),
            )
            embed.add_field(
                name="終了", value=self._with_relative(notification["end"]), inline=True
            )
        embed.add_field(name="契約番号", value=notification["policy"], inline=True)
        if notification["link"]:
            embed.add_field(
                name="リンク",
                value=f"[{notification['link_label']}]({notification['link']})（スマホのみ）",
                inline=False,
            )
        embed.set_footer(text="PayPayほけん")

        await self.sender(content=f"🚗 {embed.description}", embed=embed)

    async def _send_unknown(self, subject, text):
        """未対応の件名は本文をテキスト化してそのまま送る。"""
        text = text or "(本文なし)"
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"
        embed = Embed(title=subject or "(件名なし)", description=text, color=Color.blue())
        embed.set_footer(text="PayPayほけん（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
