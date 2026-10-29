import base64
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.gmail_handlers.inforich import INFORICH_ADDRESS, InforichHandler


def html_payload(content, date="Tue, 13 Oct 2026 09:00:02 +0900"):
    raw = (
        "<!DOCTYPE html><html><head><style>.emailContent p { white-space: pre-line; }</style></head>"
        "<body><header><img alt=\"logo\"></header>"
        f"<section class=\"emailContent\">{content}</section>"
        "<footer><a href=\"https://chargespot.jp\">https://chargespot.jp</a></footer></body></html>"
    )
    return {
        "mimeType": "multipart/mixed",
        "headers": [{"name": "Date", "value": date}],
        "parts": [{
            "mimeType": "multipart/related",
            "parts": [{
                "mimeType": "text/html",
                "body": {"data": base64.urlsafe_b64encode(raw.encode()).decode()},
            }],
        }],
    }


RECEIPT_SUBJECT = "CHARGESPOTをご利用いただきましてありがとうございます。"
RECEIPT_CONTENT = """<h1>CHARGESPOTをご利用いただきましてありがとうございます。</h1>
<ul>
<li>オーダー番号：<span>701300000000000000000</span></li>
<li>決済方法：<span>クレジットカード</span></li>
<li>利用金額（円）：<span>1650</span></li>
<li>貸出場所: <span>テスト駅 中央改札内</span></li>
<li>返却場所: <span>テストストア 駅前店</span></li>
</ul>
<blockquote>
<ul>
<li>「利用金額（円）」につきましてはご登録のお支払い方法にて決済されます。</li>
<li>本メールの送信アドレスは送信専用となっております。</li>
</ul>
</blockquote>
<hr>
<p>お問い合わせ先：
  CHARGESPOT サポートセンター
<a href="mailto:support@example.com">support@example.com</a></p>
"""

RESUBMIT_SUBJECT = "SPOTJOBS本人確認書類再提出のお願い"
RESUBMIT_CONTENT = """<h1>SPOTJOBS本人確認書類再提出のお願い</h1>
    <hr>
    <p><span>テスト</span>様</p>
    <p>この度はSPOTJOBS（スポットジョブズ）へお申し込みありがとうございます。
        ご提出いただいた書類に、不備がございましたので再提出をお願いいたします。

        【間違いやすいポイント】
        ・提出書類間違い

        登録方法の動画をご用意しております。<a href="https://example.com/video">★こちら★</a>
    </p>
    <hr>
    <p style="text-align: center; margin: 24px 0"><img src="https://example.com/a.jpg" alt=""></p>
    <p style="text-align: center; margin: 32px 0"><a href="https://www.spot.jobs/">働き方ガイドはこちら</a></p>
"""

VERIFIED_CONTENT = """<h1>SPOTJOBS本人確認完了のおしらせ</h1>
    <hr>
    <p><span>テスト</span>様</p>
    <p>ご提出いただいた書類の確認が完了いたしましたのでお知らせいいたします。</p>
    <p><a href="https://app.spot.jobs/on-boarding">こちら</a>からログインをし、マップをご確認ください。</p>
"""


class InforichHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = InforichHandler(sender)
        self.assertEqual(handler.address, INFORICH_ADDRESS)
        await handler.handle({"subject": subject, "payload": payload})
        self.assertEqual(len(sent), 1)
        return sent[0]

    @staticmethod
    def fields(embed):
        return [(field.name, field.value) for field in embed.fields]

    async def test_chargespot_receipt_shows_amount_and_places(self):
        message = await self.send(RECEIPT_SUBJECT, html_payload(RECEIPT_CONTENT))

        embed = message["embed"]
        self.assertEqual(message["content"], "🔋 モバイルバッテリーを返却しました（1,650円）")
        self.assertEqual(embed.title, "CHARGESPOT 利用完了")
        self.assertEqual(embed.footer.text, "CHARGESPOT")
        self.assertEqual(self.fields(embed), [
            ("利用金額", "1,650円"),
            ("貸出場所", "テスト駅 中央改札内"),
            ("返却場所", "テストストア 駅前店"),
            ("決済方法", "クレジットカード"),
            ("オーダー番号", "701300000000000000000"),
        ])

    async def test_embed_timestamp_is_received_time(self):
        message = await self.send(RECEIPT_SUBJECT, html_payload(RECEIPT_CONTENT))

        self.assertEqual(
            message["embed"].timestamp,
            datetime(2026, 10, 13, 9, 0, 2, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

    async def test_spotjobs_resubmit_shows_body_with_links_without_name(self):
        message = await self.send(RESUBMIT_SUBJECT, html_payload(RESUBMIT_CONTENT))

        embed = message["embed"]
        self.assertEqual(message["content"], f"⚠️ **{RESUBMIT_SUBJECT}**")
        self.assertEqual(embed.title, RESUBMIT_SUBJECT)
        self.assertEqual(embed.footer.text, "SPOTJOBS")
        self.assertEqual(embed.description, (
            "この度はSPOTJOBS（スポットジョブズ）へお申し込みありがとうございます。\n"
            "ご提出いただいた書類に、不備がございましたので再提出をお願いいたします。\n"
            "\n"
            "【間違いやすいポイント】\n"
            "・提出書類間違い\n"
            "\n"
            "登録方法の動画をご用意しております。[★こちら★](https://example.com/video)"
        ))
        self.assertNotIn("テスト様", embed.description)
        self.assertNotIn("働き方ガイド", embed.description)

    async def test_spotjobs_verified_joins_paragraphs(self):
        message = await self.send("SPOTJOBS本人確認完了のおしらせ", html_payload(VERIFIED_CONTENT))

        embed = message["embed"]
        self.assertEqual(message["content"], "✅ **SPOTJOBS本人確認完了のおしらせ**")
        self.assertEqual(embed.description, (
            "ご提出いただいた書類の確認が完了いたしましたのでお知らせいいたします。\n\n"
            "[こちら](https://app.spot.jobs/on-boarding)からログインをし、マップをご確認ください。"
        ))

    async def test_unknown_subject_sends_body_text(self):
        message = await self.send(
            "CHARGESPOTからのお知らせ",
            html_payload("<h1>お知らせ</h1><p>本文テキスト</p>"),
        )

        embed = message["embed"]
        self.assertEqual(message["content"], "📩 **CHARGESPOTからのお知らせ**")
        self.assertEqual(embed.title, "お知らせ")
        self.assertEqual(embed.description, "本文テキスト")
        self.assertEqual(embed.footer.text, "CHARGESPOT")

    async def test_long_body_is_truncated(self):
        message = await self.send(
            "SPOTJOBSのお知らせ", html_payload(f"<p>{'あ' * 1500}</p>")
        )

        self.assertTrue(message["embed"].description.endswith("…(省略)"))
        self.assertLess(len(message["embed"].description), 1100)
