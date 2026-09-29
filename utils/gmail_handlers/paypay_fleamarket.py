"""Yahoo!フリマ（旧PayPayフリマ）の取引通知メールを整形してDiscordへ送る。"""

import base64
import re

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


PAYPAY_FLEAMARKET_ADDRESS = "paypay-fleamarket@mail.yahoo.co.jp"
PURCHASE_LIST_URL = "https://paypayfleamarket.yahoo.co.jp/my/purchase"

MESSAGE_SUBJECT = "Yahoo!フリマ - 取引メッセージ："
SOLD_SUBJECT = re.compile(r"^【Yahoo!フリマ】「(.+)」が購入されました$")
SHIPPED_SUBJECT = re.compile(r"^【Yahoo!フリマ】「(.+)」が発送されました$")


class PayPayFleamarketHandler(BaseHandler):
    """件名で取引メッセージ／購入／発送を判定し、商品と取引画面をEmbedで送る。"""

    def __init__(self, sender):
        super().__init__(sender)
        self.address = PAYPAY_FLEAMARKET_ADDRESS

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = PayPayFleamarketHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = PayPayFleamarketHandler._extract_body(part)
            if text:
                return text
        return ""

    @staticmethod
    def _match(text, pattern, default=""):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    @staticmethod
    def _url(text, pattern):
        """URL を探し、計測用のクエリ（?cpt_s=... など）を外して返す。"""
        match = re.search(pattern, text)
        return match.group(0).split("?")[0] if match else None

    @staticmethod
    def _price(value):
        digits = value.replace(",", "")
        return f"{int(digits):,}円" if digits.isdigit() else ""

    def _parse(self, subject, text):
        item = {
            "name": self._match(text, r"商品(?:名|タイトル)\s*[:：]\s*(.+)"),
            "id": self._match(text, r"商品ID\s*[:：]\s*(\S+)"),
            "page": self._url(text, r"https://paypayfleamarket\.yahoo\.co\.jp/item/\S+"),
        }
        if subject.startswith(MESSAGE_SUBJECT):
            partner = self._match(text, r"(出品者|購入者)から取引メッセージが届きました")
            return {
                **item,
                "kind": "メッセージ",
                "partner": partner or "相手",
                "url": self._url(text, r"https://paypayfleamarket-sec\.yahoo\.co\.jp/item/\S+/trade/\S+"),
            }
        if match := SOLD_SUBJECT.match(subject):
            return {**item, "kind": "購入", "name": item["name"] or match.group(1), "url": item["page"]}
        if match := SHIPPED_SUBJECT.match(subject):
            return {
                **item,
                "kind": "発送",
                "name": item["name"] or match.group(1),
                "price": self._price(self._match(text, r"商品金額\s*[:：]\s*([\d,]+)円")),
                "url": PURCHASE_LIST_URL,
            }
        return None

    async def handle(self, details):
        subject = details.get("subject", "")
        text = self._extract_body(details.get("payload", {})).replace("\r\n", "\n")
        notification = self._parse(subject, text)
        if notification is None:
            await self._send_unknown(subject, text)
            return

        name = notification["name"] or "(商品名不明)"
        if notification["kind"] == "メッセージ":
            title, color, emoji = "取引メッセージ", Color.blurple(), "💬"
            description = f"{notification['partner']}から「{name}」の取引メッセージが届きました"
        elif notification["kind"] == "購入":
            title, color, emoji = "商品が購入されました", Color.green(), "🛍️"
            description = f"「{name}」が購入されました。発送の手続きを進めてください"
        else:
            title, color, emoji = "商品が発送されました", Color.orange(), "📦"
            description = f"購入した「{name}」が発送されました"

        embed = Embed(title=title, description=description, color=color, url=notification["url"])
        if notification.get("price"):
            embed.add_field(name="商品金額", value=notification["price"], inline=True)
        if notification["id"]:
            value = notification["id"]
            if notification["page"]:
                value = f"[{value}]({notification['page']})"
            embed.add_field(name="商品ID", value=value, inline=True)
        embed.set_footer(text="Yahoo!フリマ")

        await self.sender(content=f"{emoji} {description}", embed=embed)

    async def _send_unknown(self, subject, text):
        """未対応の件名は本文をそのまま送る。"""
        text = text.strip() or "(本文なし)"
        if len(text) > 500:
            text = text[:500] + "\n…(省略)"
        embed = Embed(title=subject or "(件名なし)", description=text, color=Color.blue())
        embed.set_footer(text="Yahoo!フリマ（未対応の通知）")
        await self.sender(content=f"📩 **{subject}**", embed=embed)
