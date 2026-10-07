import base64
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.gmail_handlers.times_car import (
    RESERVATION_LIST_URL,
    TIMES_CAR_ADDRESS,
    TimesCarHandler,
)


def text_payload(body, date="Tue, 6 Oct 2026 12:56:30 +0900"):
    return {
        "mimeType": "text/plain",
        "headers": [{"name": "Date", "value": date}],
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


class TimesCarTestCase(unittest.IsolatedAsyncioTestCase):
    async def handle(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = TimesCarHandler(sender)
        self.assertEqual(handler.address, TIMES_CAR_ADDRESS)
        await handler.handle({"subject": subject, "payload": payload})
        return sent

    async def send(self, subject, payload):
        sent = await self.handle(subject, payload)
        self.assertEqual(len(sent), 1)
        return sent[0]


class TimesCarHandlerTests(TimesCarTestCase):
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


CHANGED_BODY = RESERVED_BODY.replace("予約登録完了", "予約変更完了").replace(
    "2026/10/06 13:00", "2026/10/06 13:15"
).replace("1時間15分", "1時間30分").replace("1100円", "1320円")

RETURN_SOON_BODY = """――――――――――――――
【Times CAR】返却確認
――――――――――――――

テスト太郎　様

あと30分で返却時間となります。

┏━━■予約内容■━━━━━┓

■予約番号
123456789
■ステーション
テスト駅前
■車両
アクア（ハイブリッド） （品川 500 あ 1234:ブルー）
■利用開始日時
2026/10/06 11:45
■返却予定日時
2026/10/06 13:15 
■追加運転者
なし

┗━━━━━━━━━━━━━┛

【時間内にステーションに戻れない場合は】
次の予約が入っていなければ延長手続きが可能です。
"""

RETURNED_BODY = """――――――――――――――
【Times CAR】返却証
――――――――――――――

テスト太郎　様

以下の内容で返却を確認しました。

■利用時アンケートの回答がまだの方はご協力ください
https://share.timescar.jp/ap/questionnaire/useAnswer.html?bid=123456789
※回答期限：返却後24時間以内

┏━━■利用内容■━━━━━┓

■予約番号
123456789
■ステーション
テスト駅前
■車両
アクア（ハイブリッド） （品川 500 あ 1234:ブルー）
■予約時間
2026/10/06 11:45 - 2026/10/06 13:15
■利用時間
2026/10/06 11:45 - 2026/10/06 12:56
■走行距離
13km
■最高速度
64km/h
■急加速回数
0回
■時間料金
1,100円（1時間11分）
■距離料金
0円
※距離料金は20kmを超えてからの走行距離に対して課金
■ペナルティ金額
{penalty}
■合計金額
1,100円
――――――――――――――
┗━━━━━━━━━━━━┛
"""

FUEL_DISCOUNT_BODY = """――――――――――――――
【Times CAR】給油割引が適用されました
――――――――――――――

┏━━■内容■━━━━━━┓

■予約番号
123456789

■給油割引金額
-440円

■合計割引金額
-440円

┗━━━━━━━━━━━━┛
"""

class TimesCarOtherNotificationTests(TimesCarTestCase):
    def fields(self, embed):
        return [(field.name, field.value) for field in embed.fields]

    async def test_change_shows_updated_reservation(self):
        message = await self.send("【Times CAR】予約変更完了", text_payload(CHANGED_BODY))

        embed = message["embed"]
        self.assertEqual(message["content"], "🔁 テスト駅前の予約を変更しました")
        self.assertEqual(embed.title, "カーシェア予約変更")
        self.assertEqual(embed.url, RESERVATION_LIST_URL)
        self.assertIn(("返却予定", "2026/10/06 13:15"), self.fields(embed))
        self.assertIn(("予定料金", "1320円"), self.fields(embed))

    async def test_return_soon_shows_remaining_time_and_return_time(self):
        message = await self.send("【Times CAR】返却確認", text_payload(RETURN_SOON_BODY))

        embed = message["embed"]
        self.assertEqual(message["content"], "⏰ あと30分で返却時間です")
        # 2026/10/06 13:15 JST = 2026-10-06T04:15:00Z
        self.assertEqual(self.fields(embed), [
            ("返却予定", "2026/10/06 13:15（<t:1791260100:R>）"),
            ("ステーション", "テスト駅前"),
            ("車両", "アクア（ハイブリッド） （品川 500 あ 1234:ブルー）"),
            ("予約番号", "123456789"),
        ])

    async def test_return_receipt_shows_usage_and_fees_without_zero_penalty(self):
        body = RETURNED_BODY.format(penalty="0円（00分）")
        message = await self.send("【Times CAR】返却証", text_payload(body))

        embed = message["embed"]
        self.assertEqual(message["content"], "✅ 返却しました（合計 1,100円）")
        self.assertEqual(self.fields(embed), [
            ("利用時間", "2026/10/06 11:45 - 12:56"),
            ("走行距離", "13km"),
            ("最高速度", "64km/h"),
            ("時間料金", "1,100円（1時間11分）"),
            ("距離料金", "0円"),
            ("合計金額", "1,100円"),
            ("ステーション", "テスト駅前"),
            ("車両", "アクア（ハイブリッド） （品川 500 あ 1234:ブルー）"),
            ("予約番号", "123456789"),
        ])

    async def test_return_receipt_shows_penalty_when_charged(self):
        body = RETURNED_BODY.format(penalty="1,650円（15分）")
        message = await self.send("【Times CAR】返却証", text_payload(body))

        self.assertIn(("ペナルティ", "1,650円（15分）"), self.fields(message["embed"]))

    async def test_fuel_discount_shows_negative_amount(self):
        message = await self.send(
            "【Times CAR】給油割引が適用されました", text_payload(FUEL_DISCOUNT_BODY)
        )

        embed = message["embed"]
        self.assertEqual(message["content"], "⛽ 給油割引（-440円）が適用されました")
        self.assertEqual(self.fields(embed), [
            ("給油割引", "-440円"),
            ("合計割引", "-440円"),
            ("予約番号", "123456789"),
        ])

    async def test_embed_timestamp_is_received_time(self):
        message = await self.send("【Times CAR】返却確認", text_payload(RETURN_SOON_BODY))

        self.assertEqual(
            message["embed"].timestamp,
            datetime(2026, 10, 6, 12, 56, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

    async def test_unknown_subject_also_has_timestamp(self):
        message = await self.send("【Times CAR】お知らせ", text_payload("本文"))

        self.assertIsNotNone(message["embed"].timestamp)

    async def test_missing_date_header_leaves_timestamp_empty(self):
        payload = text_payload(RETURN_SOON_BODY)
        payload["headers"] = []
        message = await self.send("【Times CAR】返却確認", payload)

        self.assertIsNone(message["embed"].timestamp)

    async def test_ignored_subjects_are_not_sent(self):
        for subject in (
            "【Times CAR】認証コード",
            "【Times CAR】「アプリ解施錠機能」利用登録完了のお知らせ",
            "【Times CAR】スグ乗り入会　お申し込み受付完了",
            "【Times CAR】スグ乗り入会　会員登録完了のご案内",
        ):
            with self.subTest(subject=subject):
                self.assertEqual(await self.handle(subject, text_payload("本文")), [])
