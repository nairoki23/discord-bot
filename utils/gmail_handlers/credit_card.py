"""クレジット／デビットカードの利用通知を共通形式でDiscordへ送る。"""

import base64
import re
from datetime import datetime

from discord import Color, Embed

from service.google.gmail.handler_base import BaseHandler


CHIBABANK_ADDRESS = "mail@vdebit.chibabank.co.jp"
VIEWCARD_ADDRESS = "viewcard@mail.viewsnet.jp"
JCB_ADDRESS = "mail@qa.jcb.co.jp"

MERCHANT_ALIASES = {
    "4015852TOMIBUNKIYOMIDAITE": "富分清見台店",
    "SUICA GOOGLEPAY": "Suica Googlepay",
    "UOKUNI FOOD SERVICES NATI": "魚国総本社木更津高専売店",
    "SEVEN-ELEVEN": "セブンイレブン",
    "POPLAR GROUP": "ポプラ",
    "HIDAKAYA SOGAHIGASHIGUCHI": "日高屋蘇我東店",
    "PAYPAL *DISCORD": "Discord_paypal",
    "DAILY YAMAZAKI": "デイリーヤマザキ",
    "LAWSON": "ローソン",
    "ITO YOKADO": "イトーヨーカドー",
    "STARBUCKS COFFEE JAPAN": "スターバックスコーヒージャパン",
    "JR EAST": "JR東日本",
    "BELC CHIBAHAMANO TEN": "ベルク千葉浜野店",
    "DONQUIJOTE KISARAZU": "ドン・キホーテ木更津店",
    "MATUMOTOKIYOSI": "マツモトキヨシ",
    "MCDONALDS MOBILE ORDER": "マクドナルド",
    "MCDONALD S": "マック",
    "CLOUDFLARE": "Cloudflare",
    "VisaMobile2Cashback": "Visa割キャッシュバック",
}
ISSUER_ALIASES = {
    "ＪＡＬカードｎａｖｉ":"JALカードnavi"
}

class CreditCardHandler(BaseHandler):
    """カード会社ごとのメールを解析し、同じ通知レイアウトで送信する。"""

    ADDRESSES = (CHIBABANK_ADDRESS, VIEWCARD_ADDRESS, JCB_ADDRESS)

    def __init__(self, sender, address):
        super().__init__(sender)
        if address not in self.ADDRESSES:
            raise ValueError(f"未対応のカード通知送信元です: {address}")
        self.address = address

    @staticmethod
    def _extract_body(payload):
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                text = CreditCardHandler._extract_body(part)
                if text:
                    return text
        for part in payload.get("parts", []):
            text = CreditCardHandler._extract_body(part)
            if text:
                return text
        return ""

    @staticmethod
    def _match(text, pattern, default="不明"):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    def _parse_chibabank(self, subject, text):
        is_refund = subject == "【TSUBASAちばぎんVisaデビットカード】ご返金受付のお知らせ"
        if subject not in {
            "【TSUBASAちばぎんVisaデビットカード】ご利用のお知らせ",
            "【TSUBASAちばぎんVisaデビットカード】ご返金受付のお知らせ",
        }:
            return None

        return {
            "issuer": "ちばぎんVisaデビット",
            "kind": "返金" if is_refund else "利用",
            "merchant": self._match(text, r"お取引内容：\s*(.+)"),
            "amount": self._match(
                text, r"ご返金予定額：\s*(.+)" if is_refund else r"お取引金額：\s*(.+)", "0"
            ),
            "date": self._match(
                text, r"ご返金受付日：\s*([\d/]+)" if is_refund else r"お取引日：\s*([\d/]+)"
            ),
            "authorization": self._match(text, r"承認番号：\s*(\d+)", ""),
        }

    def _parse_viewcard(self, subject, text):
        is_confirmed = subject == "－確報版－ ビューカードご利用情報のお知らせ（本人会員利用）"
        if subject not in {
            "◆速報版◆ビューカードご利用情報のお知らせ（本人会員利用）",
            "－確報版－ ビューカードご利用情報のお知らせ（本人会員利用）",
        }:
            return None

        return {
            "issuer": self._match(text, r"ご利用カード\s*：\s*(.+)", "ビューカード"),
            "kind": "利用確定" if is_confirmed else "利用",
            "merchant": self._match(text, r"・ 利用加盟店\s*：\s*(.+)"),
            "amount": self._match(text, r"・ 利用金額\s*：\s*([\d,]+)円", "0") + "円",
            "date": self._match(
                text, r"・ 利用日\s*：\s*(.+)" if is_confirmed else r"・ 利用日時\s*：\s*(.+)"
            ),
            "user": self._match(text, r"・ 利用者\s*：\s*(.+)", ""),
            "type": self._match(text, r"・ 利用種別\s*：\s*(.+)", ""),
        }

    def _paser_jcbcard(self, subject, text):
        is_confirmed = subject == "（売上到着分）JCBカード/ショッピングご利用のお知らせ"
        if subject not in {
            "JCBカード／ショッピングご利用のお知らせ",
            "（売上到着分）JCBカード/ショッピングご利用のお知らせ",
        }:
            return None

        return {
            "issuer": self._match(text, r"カード名称\s*：\s*(.+)", "JCBカード"),
            "kind": "利用確定" if is_confirmed else "利用",
            "merchant": self._match(text, r"【ご利用先】\s*(.+)"),
            "amount": self._match(text, r"【ご利用金額】\s*([\d,]+円)", "0円"),
            "date": self._match(
                text,
                r"【(?:ご利用日時\(日本時間\)|ご利用日)】\s*(.+)",
            ),
        }

    def _parse(self, subject, text):
        if self.address == CHIBABANK_ADDRESS:
            return self._parse_chibabank(subject, text)
        if self.address == VIEWCARD_ADDRESS:
            return self._parse_viewcard(subject, text)
        return self._paser_jcbcard(subject, text)

    @staticmethod
    def _parse_timestamp(value):
        for pattern in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, pattern)
            except ValueError:
                pass
        return None

    async def handle(self, details):
        notification = self._parse(
            details.get("subject", ""), self._extract_body(details.get("payload", {}))
        )
        if notification is None:
            return

        notification["merchant"] = MERCHANT_ALIASES.get(
            notification["merchant"], notification["merchant"]
        )
        notification["issuer"] = ISSUER_ALIASES.get(
            notification["issuer"],notification["issuer"]
        )
        is_refund = notification["kind"] == "返金"
        action = "返金がありました" if is_refund else "利用しました"
        timestamp = self._parse_timestamp(notification["date"])
        embed = Embed(
            title=f"カード{notification['kind']}通知",
            description=f"{notification['merchant']}で{notification['amount']} {action}",
            color=Color.green() if is_refund else Color.blue(),
            timestamp=timestamp,
        )
        embed.add_field(name="カード", value=notification["issuer"], inline=True)
        embed.add_field(name="金額", value=notification["amount"], inline=True)
        embed.add_field(name="利用先", value=notification["merchant"], inline=False)
        if notification.get("user"):
            embed.add_field(name="利用者", value=notification["user"], inline=True)
        if notification.get("type"):
            embed.add_field(name="種別", value=notification["type"], inline=True)
        if notification.get("authorization"):
            embed.add_field(name="承認番号", value=notification["authorization"], inline=True)
        embed.set_footer(text=notification["issuer"])

        await self.sender(content=embed.description, embed=embed)
