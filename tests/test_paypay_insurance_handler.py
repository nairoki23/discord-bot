import base64
import unittest

from utils.gmail_handlers.paypay_insurance import (
    PAYPAY_INSURANCE_ADDRESS,
    PayPayInsuranceHandler,
)


def html_payload(body):
    raw = (
        "<!DOCTYPE html><html lang=\"ja\"><head><title>t</title></head><body>"
        f"<table><tr><td><font>{body}</font></td></tr></table></body></html>"
    )
    return {
        "mimeType": "text/html",
        "body": {"data": base64.urlsafe_b64encode(raw.encode()).decode()},
    }


ENROLLED_BODY = (
    "保険ご加入者 様<br>\n<br>\n"
    "この度は、あんしんドライブ基本プランにご加入いただきありがとうございました。<br>\n<br>\n"
    "保険ご加入者 様のご契約情報は以下となります。<br>\n"
    "対象のご契約：00Y2P0000001<br>\n"
    "保険開始日：2026/09/28 21:27<br>\n"
    "保険終了日：2026/09/29 10:00<br>\n<br>\n"
    "■ご契約内容の確認・変更は<a href=\"https://example.com/detail?a=1&amp;b=2\">こちら</a><br>\n"
    "■保険金請求の手続きは<a href=\"https://example.com/claim\">こちら</a><br>\n"
)

ENDING_BODY = (
    "保険ご加入者 様<br>\n<br>\n"
    "以下ご契約をいただいておりますあんしんドライブお手軽プランの保険期間が"
    "2026/09/29 10:00をもって終了予定です。<br>\n<br>\n"
    "対象のご契約：00Y2P0000001<br>\n<br>\n"
    "■契約延長の手続きは<a href=\"https://example.com/extend\">こちら</a><br>\n"
    "■ご契約内容の確認・変更は<a href=\"https://example.com/detail\">こちら</a><br>\n"
)


class PayPayInsuranceHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = PayPayInsuranceHandler(sender)
        self.assertEqual(handler.address, PAYPAY_INSURANCE_ADDRESS)
        await handler.handle({"subject": subject, "payload": payload})
        self.assertEqual(len(sent), 1)
        return sent[0]

    async def test_enrollment_shows_plan_period_and_detail_link(self):
        message = await self.send("加入手続き完了のご連絡", html_payload(ENROLLED_BODY))

        embed = message["embed"]
        self.assertEqual(embed.title, "保険加入完了")
        self.assertEqual(message["content"], "🚗 あんしんドライブ基本プランに加入しました")
        # 2026/09/29 10:00 JST = 2026-09-29T01:00:00Z
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("開始", "2026/09/28 21:27"),
            ("終了", "2026/09/29 10:00（<t:1790643600:R>）"),
            ("契約番号", "00Y2P0000001"),
            ("リンク", "[契約内容の確認](https://example.com/detail?a=1&b=2)（スマホのみ）"),
        ])

    async def test_ending_notice_shows_end_time_and_extension_link(self):
        message = await self.send("保険期間終了予定のお知らせ", html_payload(ENDING_BODY))

        embed = message["embed"]
        self.assertEqual(embed.title, "保険期間終了予定")
        self.assertEqual(message["content"], "🚗 あんしんドライブお手軽プランがまもなく終了します")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("終了", "2026/09/29 10:00（<t:1790643600:R>）"),
            ("契約番号", "00Y2P0000001"),
            ("リンク", "[契約延長の手続き](https://example.com/extend)（スマホのみ）"),
        ])

    async def test_unknown_subject_falls_back_to_plain_text(self):
        message = await self.send(
            "重要なお知らせ", html_payload("お知らせ本文<br>\n2行目<br>")
        )

        embed = message["embed"]
        self.assertEqual(message["content"], "📩 **重要なお知らせ**")
        self.assertEqual(embed.title, "重要なお知らせ")
        self.assertEqual(embed.description, "お知らせ本文\n2行目")


if __name__ == "__main__":
    unittest.main()
