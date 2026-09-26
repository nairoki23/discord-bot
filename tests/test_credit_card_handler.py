import base64
import unittest

from utils.gmail_handlers.credit_card import (
    CHIBABANK_ADDRESS,
    JCB_ADDRESS,
    VIEWCARD_ADDRESS,
    CreditCardHandler,
)


def encoded_payload(text):
    return {"body": {"data": base64.urlsafe_b64encode(text.encode()).decode()}}


class CreditCardHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_chibabank_usage_uses_the_common_notification_layout(self):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = CreditCardHandler(sender, CHIBABANK_ADDRESS)
        await handler.handle({
            "subject": "【TSUBASAちばぎんVisaデビットカード】ご利用のお知らせ",
            "payload": encoded_payload(
                "お取引日： 2026/09/12\n"
                "お取引金額： 1,200.00 JPY\n"
                "お取引内容： SEVEN-ELEVEN\n"
                "承認番号： 123456"
            ),
        })

        embed = sent[0]["embed"]
        self.assertEqual(embed.title, "カード利用通知")
        self.assertEqual(sent[0]["content"], "セブンイレブンで1,200.00 JPY 利用しました")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("カード", "ちばぎんVisaデビット"),
            ("金額", "1,200.00 JPY"),
            ("利用先", "セブンイレブン"),
            ("承認番号", "123456"),
        ])

    async def test_viewcard_usage_uses_the_common_notification_layout(self):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = CreditCardHandler(sender, VIEWCARD_ADDRESS)
        payload = {
            "parts": [{
                "mimeType": "text/plain",
                "body": {"data": base64.urlsafe_b64encode(
                    (
                        "ご利用カード ： ビューカード\n"
                        "・ 利用者 ： 本人\n"
                        "・ 利用日時 ： 2026/09/12 10:30:00\n"
                        "・ 利用種別 ： 一回払い\n"
                        "・ 利用金額 ： 2,000円\n"
                        "・ 利用加盟店 ： JR東日本"
                    ).encode()
                ).decode()},
            }],
        }
        await handler.handle({
            "subject": "◆速報版◆ビューカードご利用情報のお知らせ（本人会員利用）",
            "payload": payload,
        })

        embed = sent[0]["embed"]
        self.assertEqual(embed.title, "カード利用通知")
        self.assertEqual(sent[0]["content"], "JR東日本で2,000円 利用しました")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("カード", "ビューカード"),
            ("金額", "2,000円"),
            ("利用先", "JR東日本"),
            ("利用者", "本人"),
            ("種別", "一回払い"),
        ])

    async def test_jcb_usage_uses_the_common_notification_layout(self):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = CreditCardHandler(sender, JCB_ADDRESS)
        await handler.handle({
            "subject": "JCBカード／ショッピングご利用のお知らせ",
            "payload": encoded_payload(
                "カード名称　：　ＪＡＬカードｎａｖｉ\n"
                "【ご利用日時(日本時間)】　2026/09/10 11:29\n"
                "【ご利用金額】　5,680円\n"
                "【ご利用先】　ウエンデイ－ズフア－ストキツチン"
            ),
        })

        embed = sent[0]["embed"]
        self.assertEqual(embed.title, "カード利用通知")
        self.assertEqual(embed.timestamp.strftime("%Y/%m/%d %H:%M"), "2026/09/10 11:29")
        self.assertEqual(
            sent[0]["content"],
            "ウエンデイ－ズフア－ストキツチンで5,680円 利用しました",
        )
        self.assertEqual(
            [(field.name, field.value) for field in embed.fields],
            [
                ("カード", "JALカードnavi"),
                ("金額", "5,680円"),
                ("利用先", "ウエンデイ－ズフア－ストキツチン"),
            ],
        )

    async def test_jcb_confirmed_usage_uses_the_common_notification_layout(self):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = CreditCardHandler(sender, JCB_ADDRESS)
        await handler.handle({
            "subject": "（売上到着分）JCBカード/ショッピングご利用のお知らせ",
            "payload": encoded_payload(
                "カード名称　：　ＪＡＬカードｎａｖｉ\n"
                "【ご利用日】　2026/09/03\n"
                "【ご利用金額】　 300円\n"
                "【ご利用先】　東京メトロ　交通利用"
            ),
        })

        embed = sent[0]["embed"]
        self.assertEqual(embed.title, "カード利用確定通知")
        self.assertEqual(sent[0]["content"], "東京メトロ　交通利用で300円 利用しました")
        self.assertEqual(
            [(field.name, field.value) for field in embed.fields],
            [
                ("カード", "JALカードnavi"),
                ("金額", "300円"),
                ("利用先", "東京メトロ　交通利用"),
            ],
        )

    async def test_jcb_cancellation_uses_the_common_notification_layout(self):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = CreditCardHandler(sender, JCB_ADDRESS)
        await handler.handle({
            "subject": "JCBカード／ショッピング取消のお知らせ",
            "payload": encoded_payload(
                "カード名称　：　ＪＡＬカードｎａｖｉ\r\n"
                "【日時（日本時間）】　2026/09/18 12:09\r\n"
                "【金額】- 15,045円（取消）\r\n"
                "【ご利用先】　ラクテンチケツト\r\n"
            ),
        })

        embed = sent[0]["embed"]
        self.assertEqual(embed.title, "カード取消通知")
        self.assertEqual(embed.timestamp.strftime("%Y/%m/%d %H:%M"), "2026/09/18 12:09")
        self.assertEqual(sent[0]["content"], "ラクテンチケツトで15,045円 取消がありました")
        self.assertEqual(
            [(field.name, field.value) for field in embed.fields],
            [
                ("カード", "JALカードnavi"),
                ("金額", "15,045円"),
                ("利用先", "ラクテンチケツト"),
            ],
        )

    async def test_unrelated_subject_does_not_send_a_notification(self):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = CreditCardHandler(sender, CHIBABANK_ADDRESS)
        await handler.handle({"subject": "お知らせ", "payload": encoded_payload("本文")})

        self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
