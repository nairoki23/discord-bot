import base64
import unittest
from datetime import datetime, timezone

from service.google.gmail.process import GmailProcess
from utils.gmail_handlers.toyoko_inn import (
    RESERVATION_URL,
    TOYOKO_INN_ADDRESS,
    ToyokoInnHandler,
)


def text_payload(body, date="Thu, 29 Oct 2026 02:11:45 +0000"):
    return {
        "mimeType": "text/plain",
        "headers": [{"name": "Date", "value": date}],
        "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()},
    }


RESERVED_BODY = """テスト 太郎 様

この度は［東横INNテスト駅前］をご予約いただき誠にありがとうございます。
以下の通り予約が完了しましたので、ご確認ください。

▼ご宿泊ホテル
━━━━━━━━━━━━━━━━━━━━
東横INNテスト駅前
住所： 〒100-0000 東京都千代田区テスト1-1-1
TEL ： 03-0000-0000
https://www.toyoko-inn.com/search/detail/00999

▼ご予約内容
━━━━━━━━━━━━━━━━━━━━

・予約番号：1234567
・ご宿泊者：てすと たろう 様
・ご宿泊日：2026年11月7日(土) より 1 泊
・チェックイン予定時刻：22:00-22:30
・ルームタイプ／プラン：お得プラン！ 禁煙ツイン
・ご利用人数（1部屋あたり）：2 名
・会員料金：10,511円（消費税/VAT込） *Webクーポン適用
・テスト市宿泊税:400円
・支払方法：オンライン決済

＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
・合計金額： 10,911円（消費税/VAT/宿泊税込）
＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝

▼キャンセル・不泊について
━━━━━━━━━━━━━━━━━━━━
当日12時以降のキャンセル： 宿泊代金の100％
"""

CANCELED_BODY = """
テスト 太郎 様

以下のご予約をキャンセルいたしました。
⠀
▼ご宿泊ホテル
━━━━━━━━━━━━━━━━━━━━
東横INNテスト空港
住所： 〒100-0000 東京都千代田区テスト2-2-2
⠀
▼ご予約内容
━━━━━━━━━━━━━━━━━━━━
⠀
・予約番号：7654321
・ご宿泊者：てすと はなこ 様
・ご宿泊日：2026年11月7日(土) より 1 泊
・ルームタイプ／プラン：早割 禁煙シングル
・ご利用人数（1部屋あたり）：1 名
・宿泊料金：8,255円（消費税/VAT込）

＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
・合計金額： 8,455円（消費税/VAT/宿泊税込）
＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
"""


class ToyokoInnHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = ToyokoInnHandler(sender)
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

    async def test_reservation_shows_stay_hotel_and_total(self):
        message = await self.send("東横INNテスト駅前 予約確認メール", text_payload(RESERVED_BODY))

        embed = message["embed"]
        self.assertEqual(message["content"], "🏨 東横INNテスト駅前を予約しました")
        self.assertEqual(embed.title, "ホテル予約完了")
        self.assertEqual(embed.url, RESERVATION_URL)
        self.assertEqual(embed.footer.text, "東横INN")
        # 2026/11/07 22:00 JST = 2026-11-07T13:00:00Z
        self.assertEqual(self.fields(embed), [
            ("宿泊日", "2026年11月7日(土) より 1 泊（<t:1794056400:R>）"),
            ("チェックイン", "22:00-22:30"),
            ("ホテル", "[東横INNテスト駅前](https://www.toyoko-inn.com/search/detail/00999)"),
            ("部屋／プラン", "お得プラン！ 禁煙ツイン"),
            ("人数", "2 名"),
            ("合計金額", "10,911円"),
            ("支払方法", "オンライン決済"),
            ("予約番号", "1234567"),
        ])

    async def test_change_uses_change_title(self):
        message = await self.send(
            "東横INNテスト駅前 予約変更確認メール", text_payload(RESERVED_BODY)
        )

        self.assertEqual(message["content"], "🔁 東横INNテスト駅前の予約を変更しました")
        self.assertEqual(message["embed"].title, "ホテル予約変更")

    async def test_cancel_shows_canceled_reservation(self):
        message = await self.send(
            "[東横INNテスト空港]予約キャンセル確認メール", text_payload(CANCELED_BODY)
        )

        embed = message["embed"]
        self.assertEqual(message["content"], "❌ 東横INNテスト空港の予約をキャンセルしました")
        self.assertEqual(embed.title, "ホテル予約キャンセル")
        self.assertIsNone(embed.url)
        self.assertEqual(self.fields(embed), [
            ("宿泊日", "2026年11月7日(土) より 1 泊"),
            ("ホテル", "東横INNテスト空港"),
            ("部屋／プラン", "早割 禁煙シングル"),
            ("人数", "1 名"),
            ("合計金額", "8,455円"),
            ("予約番号", "7654321"),
        ])

    async def test_guest_names_are_not_sent(self):
        for subject, body in (
            ("東横INNテスト駅前 予約確認メール", RESERVED_BODY),
            ("[東横INNテスト空港]予約キャンセル確認メール", CANCELED_BODY),
            ("東横INNからのお知らせ", RESERVED_BODY),
        ):
            with self.subTest(subject=subject):
                text = self.sent_text(await self.send(subject, text_payload(body)))
                self.assertNotIn("テスト 太郎", text)
                self.assertNotIn("てすと", text)

    async def test_unknown_subject_sends_body_text(self):
        message = await self.send("東横INNからのお知らせ", text_payload("本文テキスト\r\n2行目"))

        self.assertEqual(message["content"], "📩 **東横INNからのお知らせ**")
        self.assertEqual(message["embed"].description, "本文テキスト\n2行目")
        self.assertEqual(message["embed"].footer.text, "東横INN（未対応の通知）")

    async def test_embed_timestamp_is_received_time(self):
        message = await self.send("東横INNテスト駅前 予約確認メール", text_payload(RESERVED_BODY))

        self.assertEqual(
            message["embed"].timestamp, datetime(2026, 10, 29, 2, 11, 45, tzinfo=timezone.utc)
        )


class ToyokoInnHandlerAddressTests(unittest.TestCase):
    def test_handles_every_hotel_address_by_partial_match(self):
        async def sender(**kwargs):
            pass

        process = GmailProcess(lambda: None)
        handler = ToyokoInnHandler(sender)
        self.assertEqual(handler.address, TOYOKO_INN_ADDRESS)
        self.assertTrue(process.set_handler(handler))

        for address in (
            "301_chubu_international_airport_no2@wm.toyoko-inn.com",
            "nagoya_meieki_minami@wm.toyoko-inn.com",
        ):
            with self.subTest(address=address):
                self.assertIs(process.find_handler(address), handler)
        self.assertIsNone(process.find_handler("info@toyoko-inn.com"))
