import base64
import unittest

from discord import Color

from utils.gmail_handlers.eplus import EPLUS_ADDRESS, HISTORY_URL, EplusHandler


def text_payload(text):
    # 実メールは CRLF 改行の text/plain（全角英数・\ 表記の円）
    data = text.replace("\n", "\r\n").encode()
    return {"mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(data).decode()}}


def choices(first_result="", second_result=""):
    def result(value):
        return f"　抽選結果　　{value}\n" if value else ""

    return (
        "公演名　　　：　テストバンド\n"
        "会場名　　　：　テスト　アリーナ\n"
        "席種枚数\n"
        "＜第１希望＞\n"
        + result(first_result)
        + "　公演日時　　：　2027/02/28(日)  16：00開場 17：00開演\n"
        "　席種・料金　：　Ｓ指定 \\13,200×2枚［チケット料金］＋\\1,210×2枚［サービス料］\n"
        "＜第２希望＞\n"
        + result(second_result)
        + "　公演日時　　：　2027/02/28(日)  16：00開場 17：00開演\n"
        "　席種・料金　：　Ａ指定 \\8,800×2枚［チケット料金］＋\\1,210×2枚［サービス料］\n"
    )


PRICE = (
    "\n料金\n"
    "　　料金合計　：　\\28,820　【最大購入金額です】\n"
    "　　内訳\n"
    "　　　＜第１希望＞\n"
    "　　　チケット料金　：　\\26,400\n"
    "　　　サービス料　：　\\2,420\n"
    "　　--------------------------------------------------------\n\n"
    "支払方法　　：　クレジットカード\n"
)

HEADER = (
    "\n───────────────\n＜　抽選結果のご案内　＞　\n───────────────\n\n"
    "◆２／２８　２枚　ＮＦ全ステイタス二次\n"
    "イープラスをご利用いただきまして、誠にありがとうございます。\n"
)

APPLIED_BODY = (
    HEADER
    + "テスト太郎様のプレオーダーを下記の内容で受付けました。\n\n"
    "［抽選結果確認期間　：　2026/08/29(土)　13:00　〜　2026/08/30(日)　18:00］\n\n"
    "▼申込み履歴(申込み状況照会)\nhttps://eplus.jp/jyoukyou/\n━━━━━━━━━━━━━━━━━\n"
    + choices()
    + PRICE
)

WON_BODY = (
    HEADER
    + "テスト太郎様にお申込みいただいたチケットを下記の内容にてご用意いたしました。\n"
    "━━━━━━━━━━━━━━━━━\n"
    + choices("当選", "ご用意できませんでした")
    + PRICE.replace("　【最大購入金額です】", "")
)

LOST_BODY = (
    HEADER
    + "テスト太郎様の下記申込みについては、抽選の結果チケットをご用意することができませんでした。\n\n"
    + choices("ご用意できませんでした", "ご用意できませんでした")
    + "※抽選結果は申込み履歴(申込み状況照会)からもご確認いただけます。\n"
)


class EplusHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, body):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = EplusHandler(sender)
        self.assertEqual(handler.address, EPLUS_ADDRESS)
        await handler.handle({"subject": subject, "payload": text_payload(body)})
        self.assertEqual(len(sent), 1)
        return sent[0]

    async def test_application_shows_period_choices_and_max_total(self):
        message = await self.send("【e+より】《重要》申込み完了・抽選結果確認期間のご案内", APPLIED_BODY)

        embed = message["embed"]
        self.assertEqual(embed.title, "チケット抽選申込完了")
        self.assertEqual(embed.url, HISTORY_URL)
        self.assertEqual(message["content"], "🎫 テストバンドに申し込みました")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("会場", "テスト アリーナ"),
            ("受付", "2/28 2枚 NF全ステイタス二次"),
            ("結果確認期間", "2026/08/29(土) 13:00 〜 2026/08/30(日) 18:00"),
            ("第1希望", "2027/02/28(日) 16:00開場 17:00開演\nS指定 ¥13,200×2枚"),
            ("第2希望", "2027/02/28(日) 16:00開場 17:00開演\nA指定 ¥8,800×2枚"),
            ("料金合計（最大）", "¥28,820"),
        ])

    async def test_won_result_marks_each_choice(self):
        message = await self.send("【e+より】当選のご案内", WON_BODY)

        embed = message["embed"]
        self.assertEqual(embed.title, "抽選結果: 当選")
        self.assertEqual(embed.color, Color.green())
        self.assertEqual(message["content"], "🎫 テストバンドに当選しました！")
        self.assertEqual([(field.name, field.value) for field in embed.fields][2:], [
            ("第1希望（当選）", "2027/02/28(日) 16:00開場 17:00開演\nS指定 ¥13,200×2枚"),
            ("第2希望（落選）", "2027/02/28(日) 16:00開場 17:00開演\nA指定 ¥8,800×2枚"),
            ("料金合計", "¥28,820"),
        ])

    async def test_lost_result_when_every_choice_lost(self):
        message = await self.send("【e+より】抽選結果のご案内", LOST_BODY)

        embed = message["embed"]
        self.assertEqual(embed.title, "抽選結果: 落選")
        self.assertEqual(embed.color, Color.light_grey())
        self.assertEqual(message["content"], "🎫 テストバンドは落選でした")
        self.assertEqual([field.name for field in embed.fields], [
            "会場", "受付", "第1希望（落選）", "第2希望（落選）",
        ])

    async def test_result_subject_with_a_won_choice_is_won(self):
        body = LOST_BODY.replace("　抽選結果　　ご用意できませんでした", "　抽選結果　　当選", 1)
        message = await self.send("【e+より】抽選結果のご案内", body)

        self.assertEqual(message["embed"].title, "抽選結果: 当選")

    async def test_unknown_subject_falls_back_to_plain_text(self):
        message = await self.send("【e+より】認証コード通知", "認証コード：１２３４５６")

        self.assertEqual(message["content"], "📩 **【e+より】認証コード通知**")
        self.assertEqual(message["embed"].description, "認証コード:123456")


if __name__ == "__main__":
    unittest.main()
