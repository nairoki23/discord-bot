import base64
import unittest

from discord import Color

from utils.gmail_handlers.rakuten_ticket import (
    RAKUTEN_TICKET_ADDRESS,
    REVIEW_URL,
    RakutenTicketHandler,
)


def text_payload(text):
    # 実メールは CRLF 改行の text/plain
    data = text.replace("\n", "\r\n").encode()
    return {"mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(data).decode()}}


CHOICES = (
    "【第1希望】\n"
    "公演日:2026年12月11日(金) 19:00\n"
    "会場:テストホール(TOKYO)\n"
    "申込内容\n"
    "S席 ¥12,000 x 1枚\n"
    "合計金額:¥12,000\n\n"
    "【第2希望】\n"
    "公演日:2026年12月12日(土) 18:00\n"
    "会場:テストホール(TOKYO)\n"
    "申込内容\n"
    "アリーナ席 ¥14,000 x 1枚\n"
)

APPLIED_BODY = (
    "\n\nテスト 太郎 様\n\n抽選申込が完了いたしましたので、ご連絡いたします。\n\n"
    "-----\n\n■お名前カナ\nテスト タロウ\n■電話番号\n00000000000\n\n-----\n\n"
    "■受付番号\nRT0TEST00001\n抽選結果確認の際などに必要です。必ずお控え下さい。\n"
    "■受付日\n2026年 9月 25日 22時 38分\n\n-----\n\n"
    "■イベント名: テスト ONE-MAN LIVE 「TEST」\n"
    "■受付名称: オフィシャル2次抽選先行\n"
    "■抽選結果発表日時: 2026年10月16日(金) 昼以降\n"
    "■抽選結果確認ページ: https://ticket.rakuten.co.jp/lots/review\n\n"
    + CHOICES
)

LOST_BODY = (
    "\n\nテスト 太郎 様\n\n"
    "先日お申込みいただきました下記の抽選申込に関しまして、\n"
    "厳正な抽選の結果、チケットをご用意することができませんでした。\n\n"
    "落選の場合はオーソリは自動的に開放されます。\n\n"
    "-----\n■受付番号\nRT0TEST00002\n\n■受付日\n2026年 9月 1日 21時 14分\n\n-----\n"
    "■イベント名: テスト ONE-MAN LIVE 「TEST」\n"
    "■受付名称: オフィシャル1次抽選先行\n"
    "■抽選結果発表日時: 2026年9月18日(金) 昼以降\n\n"
    + CHOICES
)

CHOICE_FIELDS = [
    ("第1希望", "2026年12月11日(金) 19:00 / テストホール(TOKYO)\nS席 ¥12,000 x 1枚"),
    ("第2希望", "2026年12月12日(土) 18:00 / テストホール(TOKYO)\nアリーナ席 ¥14,000 x 1枚"),
]


class RakutenTicketHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def send(self, subject, payload):
        sent = []

        async def sender(**kwargs):
            sent.append(kwargs)

        handler = RakutenTicketHandler(sender)
        self.assertEqual(handler.address, RAKUTEN_TICKET_ADDRESS)
        await handler.handle({"subject": subject, "payload": payload})
        self.assertEqual(len(sent), 1)
        return sent[0]

    async def test_application_shows_event_announcement_and_choices(self):
        message = await self.send(
            "抽選申込受付完了のお知らせ　【楽天チケット】", text_payload(APPLIED_BODY)
        )

        embed = message["embed"]
        self.assertEqual(embed.title, "チケット抽選申込完了")
        self.assertEqual(embed.url, REVIEW_URL)
        self.assertEqual(message["content"], "🎫 テスト ONE-MAN LIVE 「TEST」に申し込みました")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("受付", "オフィシャル2次抽選先行"),
            ("結果発表", "2026年10月16日(金) 昼以降"),
            *CHOICE_FIELDS,
            ("受付番号", "RT0TEST00001"),
        ])
        # 氏名・電話番号は載せない
        self.assertNotIn("00000000000", str(embed.to_dict()))

    async def test_lost_result_is_reported_as_lost(self):
        message = await self.send("【楽天チケット】 抽選結果のご案内", text_payload(LOST_BODY))

        embed = message["embed"]
        self.assertEqual(embed.title, "抽選結果: 落選")
        self.assertEqual(embed.color, Color.light_grey())
        self.assertEqual(embed.url, REVIEW_URL)
        self.assertEqual(message["content"], "🎫 テスト ONE-MAN LIVE 「TEST」は落選でした")
        self.assertEqual([(field.name, field.value) for field in embed.fields], [
            ("受付", "オフィシャル1次抽選先行"),
            *CHOICE_FIELDS,
            ("受付番号", "RT0TEST00002"),
        ])

    async def test_result_without_lost_phrase_is_not_reported_as_lost(self):
        body = LOST_BODY.replace(
            "チケットをご用意することができませんでした", "チケットをご用意することができました"
        ).replace("落選の場合", "")
        message = await self.send("【楽天チケット】 抽選結果のご案内", text_payload(body))

        self.assertEqual(message["embed"].title, "抽選結果: 当選")

    async def test_unknown_subject_falls_back_to_plain_text(self):
        message = await self.send("【楽天チケット】お知らせ", text_payload("本文です"))

        self.assertEqual(message["content"], "📩 **【楽天チケット】お知らせ**")
        self.assertEqual(message["embed"].description, "本文です")


if __name__ == "__main__":
    unittest.main()
