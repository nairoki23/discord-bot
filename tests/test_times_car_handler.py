import base64
import unittest

from utils.gmail_handlers.times_car import (
    RESERVATION_LIST_URL,
    TIMES_CAR_ADDRESS,
    TimesCarHandler,
)


def text_payload(body):
    return {
        "mimeType": "text/plain",
        "body": {"data": base64.urlsafe_b64encode(body.encode()).decode()},
    }


RESERVED_BODY = """――――――――――――――
【Times CAR】予約登録完了
――――――――――――――

テスト太郎　様

以下の内容で予約を受付けましたので、ご確認ください。

┏━━■予約内容■━━━━━┓

※予約内容を変更したい方はこちら
https://share.timescar.jp/view/reserve/list.jsp

■予約番号
123456789
■ステーション
テスト駅前
https://share.timescar.jp/view/station/detail.jsp?scd=AB12
■車両
アクア（ハイブリッド） （品川 500 あ 1234:ブルー）
■料金プラン
時間料金
■利用開始日時
2026/10/06 11:45
■返却予定日時
2026/10/06 13:00
■利用予定時間
1時間15分
■課金予定料金
1100円
※20kmを超えてからの走行距離に対して、別途距離料金が加算されます。

┗━━━━━━━━━━━━┛
"""

CANCELED_BODY = """――――――――――――――
【Times CAR】予約取消完了
――――――――――――――

テスト太郎　様

以下の予約が取り消されましたので、ご確認ください。

┏━━■取消内容■━━━━━┓

■予約番号
123456780
■ステーション
テスト駅前
https://share.timescar.jp/view/station/detail.jsp?scd=AB12
■車両
アクア（ハイブリッド） （品川 500 あ 1234:ブルー）
■利用開始日時
2026/10/06 11:00
■返却予定日時
2026/10/06 12:45
■利用予定時間
1時間45分


┗━━━━━━━━━━━━┛
"""


class TimesCarHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = TimesCarHandler(sender)
        self.assertEqual(handler.address, TIMES_CAR_ADDRESS)
        await handler.handle({"subject": subject, "payload": payload})
        self.assertEqual(len(sent), 1)
        return sent[0]

    async def test_reservation_shows_time_station_car_and_price(self):
        message = await self.send("【Times CAR】予約登録完了", text_payload(RESERVED_BODY))

        embed = message["embed"]
        self.assertEqual(message["content"], "🚗 テスト駅前で予約しました")
        self.assertEqual(embed.title, "カーシェア予約完了")
        self.assertEqual(embed.url, RESERVATION_LIST_URL)
        # 2026/10/06 11:45 JST = 2026-10-06T02:45:00Z
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("利用開始", "2026/10/06 11:45（<t:1791254700:R>）"),
            ("返却予定", "2026/10/06 13:00"),
            ("利用時間", "1時間15分"),
            ("ステーション", "[テスト駅前](https://share.timescar.jp/view/station/detail.jsp?scd=AB12)"),
            ("車両", "アクア（ハイブリッド） （品川 500 あ 1234:ブルー）"),
            ("予定料金", "1100円"),
            ("予約番号", "123456789"),
        ])

    async def test_cancel_shows_canceled_reservation(self):
        message = await self.send("【Times CAR】予約取消完了", text_payload(CANCELED_BODY))

        embed = message["embed"]
        self.assertEqual(message["content"], "❌ テスト駅前の予約を取り消しました")
        self.assertEqual(embed.title, "カーシェア予約取消")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("利用開始", "2026/10/06 11:00"),
            ("返却予定", "2026/10/06 12:45"),
            ("利用時間", "1時間45分"),
            ("ステーション", "[テスト駅前](https://share.timescar.jp/view/station/detail.jsp?scd=AB12)"),
            ("車両", "アクア（ハイブリッド） （品川 500 あ 1234:ブルー）"),
            ("予約番号", "123456780"),
        ])

    async def test_personal_name_is_not_sent(self):
        message = await self.send("【Times CAR】予約登録完了", text_payload(RESERVED_BODY))

        embed = message["embed"]
        sent_text = " ".join(
            [message["content"], embed.description]
            + [f"{field.name} {field.value}" for field in embed.fields]
        )
        self.assertNotIn("テスト太郎", sent_text)

    async def test_unknown_subject_sends_body_text(self):
        message = await self.send(
            "【Times CAR】お知らせ", text_payload("本文テキスト\r\n2行目")
        )

        self.assertEqual(message["content"], "📩 **【Times CAR】お知らせ**")
        self.assertEqual(message["embed"].description, "本文テキスト\n2行目")
        self.assertEqual(message["embed"].footer.text, "Times CAR（未対応の通知）")
