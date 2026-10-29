import base64
import unittest
from datetime import datetime, timezone

from utils.gmail_handlers.hellocycling import HELLO_CYCLING_ADDRESS, HelloCyclingHandler


def text_payload(body, date="Wed, 28 Oct 2026 09:56:51 +0000 (UTC)"):
    return {
        "mimeType": "text/plain",
        "headers": [{"name": "Date", "value": date}],
        "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()},
    }


FOOTER_TEXT = """
※本メールにお心当たりのない方は、お手数ですが、削除していただけますようお願い申し上げます。
※このメールは送信専用のメールアドレスから配信されています。
　ご返信いただいてもお答えできませんのでご了承ください。

───────────────────────────────────
HELLO CYCLINGお客様サポート窓口
https://www.hellocycling.jp/app/openapp?url=help/normal_mail
"""

STARTED_BODY = """
テスト さま

この度はHELLO CYCLINGをご利用いただき、誠にありがとうございます。
HELLO CYCLINGの利用が開始されました。

･･･････････････････････････････････････････
【ご利用状況】
開始ステーション：【臨時】テスト駅前駐輪場

利用開始：2026/10/28 18時38分

車両番号：K0001

ブランド：HELLO CYCLING

決済方法：クレジットカード

･･･････････････････････････････････････････
""" + FOOTER_TEXT

RETURNED_BODY = """
テスト さま

この度はHELLO CYCLINGをご利用いただき誠にありがとうございました。
HELLO CYCLINGの返却および決済のお手続きが完了いたしました。

･･･････････････････････････････････････････
【ご利用内容】
注文ID：123456789

開始ステーション：【臨時】テスト駅前駐輪場

返却ステーション：テスト公園

車両番号：K0001

ブランド：HELLO CYCLING

ご利用期間：2026/10/28 18時38分 〜 2026/10/28 18時56分

ご利用時間：18分48秒

クーポン割引：{coupon}
お支払い金額：{amount}
決済方法：クレジットカード


■ご利用内容詳細について
ご利用内容の詳細はマイページからもご確認いただけます。

･･･････････････････････････････････････････
""" + FOOTER_TEXT

PASSWORD_RESET_BODY = """
テスト さま

ログインパスワードの再発行を受付ましたので、パスワードの再設定をお願いいたします。

･･･････････････････････････････････････････

新しいパスワード：Secret#123

･･･････････････････････････････････････････
""" + FOOTER_TEXT

NOTICE_BODY = """テスト さま

日頃よりHELLO CYCLINGをご利用いただき、誠にありがとうございます。

■終了日時
2026年9月29日（火）11時

今後ともHELLO CYCLINGをよろしくお願いいたします。
･･･････････････････････････････････････････
※本メールにお心当たりのない方は、お手数ですが、削除していただけますようお願い申し上げます。
･･･････････････････････････････････････････
HELLO CYCLING（ハローサイクリング）
"""


class HelloCyclingHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = HelloCyclingHandler(sender)
        self.assertEqual(handler.address, HELLO_CYCLING_ADDRESS)
        await handler.handle({"subject": subject, "payload": payload})
        self.assertEqual(len(sent), 1)
        return sent[0]

    @staticmethod
    def fields(embed):
        return [(field.name, field.value) for field in embed.fields]

    @staticmethod
    def sent_text(message):
        embed = message["embed"]
        return " ".join(
            [message["content"], embed.title, embed.description]
            + [f"{field.name} {field.value}" for field in embed.fields]
        )

    async def test_started_shows_station_time_and_bike(self):
        message = await self.send("【HELLO CYCLING】利用開始", text_payload(STARTED_BODY))

        embed = message["embed"]
        self.assertEqual(message["content"], "🚲 【臨時】テスト駅前駐輪場で利用を開始しました")
        self.assertEqual(embed.title, "シェアサイクル利用開始")
        self.assertEqual(embed.footer.text, "HELLO CYCLING")
        # 2026/10/28 18:38 JST = 2026-10-28T09:38:00Z
        self.assertEqual(self.fields(embed), [
            ("利用開始", "2026/10/28 18時38分（<t:1793180280:R>）"),
            ("開始ステーション", "【臨時】テスト駅前駐輪場"),
            ("車両番号", "K0001"),
            ("決済方法", "クレジットカード"),
        ])

    async def test_returned_shows_period_amount_and_stations_without_zero_coupon(self):
        body = RETURNED_BODY.format(coupon="0円", amount="0円")
        message = await self.send("【HELLO CYCLING】返却完了", text_payload(body))

        embed = message["embed"]
        self.assertEqual(message["content"], "✅ 返却しました（0円）")
        self.assertEqual(embed.title, "シェアサイクル返却")
        self.assertEqual(self.fields(embed), [
            ("利用期間", "2026/10/28 18時38分 〜 18時56分"),
            ("利用時間", "18分48秒"),
            ("お支払い金額", "0円"),
            ("開始ステーション", "【臨時】テスト駅前駐輪場"),
            ("返却ステーション", "テスト公園"),
            ("車両番号", "K0001"),
            ("決済方法", "クレジットカード"),
            ("注文ID", "123456789"),
        ])

    async def test_returned_shows_coupon_when_applied(self):
        body = RETURNED_BODY.format(coupon="100円", amount="30円")
        message = await self.send("【HELLO CYCLING】返却完了", text_payload(body))

        self.assertEqual(message["content"], "✅ 返却しました（30円）")
        self.assertIn(("クーポン割引", "100円"), self.fields(message["embed"]))

    async def test_personal_name_is_not_sent(self):
        for subject, body in (
            ("【HELLO CYCLING】利用開始", STARTED_BODY),
            ("【HELLO CYCLING】返却完了", RETURNED_BODY.format(coupon="0円", amount="0円")),
            ("【HELLO CYCLING】お知らせ", NOTICE_BODY),
        ):
            with self.subTest(subject=subject):
                message = await self.send(subject, text_payload(body))
                self.assertNotIn("テスト さま", self.sent_text(message))

    async def test_password_reset_does_not_send_password(self):
        message = await self.send(
            "【HELLO CYCLING】パスワード再発行のお知らせ", text_payload(PASSWORD_RESET_BODY)
        )

        self.assertEqual(message["content"], "🔑 **【HELLO CYCLING】パスワード再発行のお知らせ**")
        self.assertNotIn("Secret#123", self.sent_text(message))

    async def test_notice_sends_body_without_boilerplate(self):
        message = await self.send(
            "【HELLO CYCLING】Yahoo!ウォレット決済終了のお知らせ", text_payload(NOTICE_BODY)
        )

        embed = message["embed"]
        self.assertEqual(message["content"], "📩 **【HELLO CYCLING】Yahoo!ウォレット決済終了のお知らせ**")
        self.assertEqual(embed.title, "Yahoo!ウォレット決済終了のお知らせ")
        self.assertEqual(embed.description, (
            "日頃よりHELLO CYCLINGをご利用いただき、誠にありがとうございます。\n"
            "\n"
            "■終了日時\n"
            "2026年9月29日（火）11時\n"
            "\n"
            "今後ともHELLO CYCLINGをよろしくお願いいたします。"
        ))

    async def test_long_notice_is_truncated(self):
        message = await self.send("【HELLO CYCLING】お知らせ", text_payload("あ" * 1500))

        self.assertTrue(message["embed"].description.endswith("…(省略)"))
        self.assertLess(len(message["embed"].description), 1100)

    async def test_embed_timestamp_is_received_time(self):
        message = await self.send("【HELLO CYCLING】利用開始", text_payload(STARTED_BODY))

        self.assertEqual(
            message["embed"].timestamp, datetime(2026, 10, 28, 9, 56, 51, tzinfo=timezone.utc)
        )
