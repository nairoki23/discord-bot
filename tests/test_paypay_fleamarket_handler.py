import base64
import unittest

from utils.gmail_handlers.paypay_fleamarket import (
    PAYPAY_FLEAMARKET_ADDRESS,
    PURCHASE_LIST_URL,
    PayPayFleamarketHandler,
)


def text_payload(text):
    data = text.replace("\n", "\r\n").encode()
    return {"mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(data).decode()}}


MESSAGE_BODY = (
    "\n■Yahoo!フリマ:2026年09月26日（土） 17時10分14秒送信\n\n"
    "テスト 様\n\n"
    "購入者から取引メッセージが届きました。\n\n"
    "詳しくは下記URLの取引画面から出品時のYahoo! JAPAN IDでログインしてご確認ください。\n\n"
    "https://paypayfleamarket-sec.yahoo.co.jp/item/z000000001/trade/seller?cpt_s=mail&cpt_c=obems\n\n"
    "■ 出品商品\n━━━━━━━━━━━━━━━━\n\n"
    "商品名：テスト商品 256GB\n"
    "商品ID：z000000001\n"
    "商品ページ：https://paypayfleamarket.yahoo.co.jp/item/z000000001?cpt_s=mail&cpt_c=obems\n"
)

SOLD_BODY = (
    "テスト 様\n\n"
    "下記商品が購入されました。発送の手続きを進めてください。\n\n"
    "-----------------------------------------------------\n"
    "商品タイトル ： テスト商品 256GB\n"
    "商品ID : z000000001\n"
    "商品ページ：https://paypayfleamarket.yahoo.co.jp/item/z000000001?cpt_s=mail&cpt_c=ooesh\n"
    "-----------------------------------------------------\n"
)

SHIPPED_BODY = (
    "テスト 様\n\n"
    "購入いただいた下記の商品が発送されました。\n\n"
    "・購入した商品\nhttps://paypayfleamarket.yahoo.co.jp/my/purchase?cpt_s=mail&cpt_c=rsura\n\n"
    "■ 購入商品\n━━━━━━━━━━━━━━━━\n\n"
    "商品ID：z000000002\n"
    "商品名：テスト端末 12/256GB\n"
    "商品金額：110000円\n"
)


class PayPayFleamarketHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, body):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = PayPayFleamarketHandler(sender)
        self.assertEqual(handler.address, PAYPAY_FLEAMARKET_ADDRESS)
        await handler.handle({"subject": subject, "payload": text_payload(body)})
        self.assertEqual(len(sent), 1)
        return sent[0]

    async def test_trade_message_links_to_trade_page_without_tracking_query(self):
        message = await self.send(
            "Yahoo!フリマ - 取引メッセージ：テスト商品 256GB(z000000001)", MESSAGE_BODY
        )

        embed = message["embed"]
        self.assertEqual(embed.title, "取引メッセージ")
        self.assertEqual(
            embed.url, "https://paypayfleamarket-sec.yahoo.co.jp/item/z000000001/trade/seller"
        )
        self.assertEqual(
            message["content"], "💬 購入者から「テスト商品 256GB」の取引メッセージが届きました"
        )
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("商品ID", "[z000000001](https://paypayfleamarket.yahoo.co.jp/item/z000000001)"),
        ])

    async def test_sold_item_asks_to_ship(self):
        message = await self.send("【Yahoo!フリマ】「テスト商品 256GB」が購入されました", SOLD_BODY)

        embed = message["embed"]
        self.assertEqual(embed.title, "商品が購入されました")
        self.assertEqual(embed.url, "https://paypayfleamarket.yahoo.co.jp/item/z000000001")
        self.assertEqual(
            message["content"], "🛍️ 「テスト商品 256GB」が購入されました。発送の手続きを進めてください"
        )

    async def test_shipped_item_shows_price(self):
        message = await self.send("【Yahoo!フリマ】「テスト端末 12/256GB」が発送されました", SHIPPED_BODY)

        embed = message["embed"]
        self.assertEqual(embed.title, "商品が発送されました")
        self.assertEqual(embed.url, PURCHASE_LIST_URL)
        self.assertEqual(message["content"], "📦 購入した「テスト端末 12/256GB」が発送されました")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("商品金額", "110,000円"),
            ("商品ID", "z000000002"),
        ])

    async def test_unknown_subject_falls_back_to_plain_text(self):
        message = await self.send("【Yahoo!フリマ】お知らせ", "本文です")

        self.assertEqual(message["content"], "📩 **【Yahoo!フリマ】お知らせ**")
        self.assertEqual(message["embed"].description, "本文です")


if __name__ == "__main__":
    unittest.main()
