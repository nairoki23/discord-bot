import unittest
from datetime import date, datetime

from cogs.tracking import Tracking as TrackingCog
from cogs.tracking import format_tracking_list, make_embed
from func.tracking.fetch.sagawa import parse_detail_time as parse_sagawa_time
from func.tracking.fetch.yamato import parse_yamato
from func.tracking.model.brand import Brand
from func.tracking.model.detail import Detail
from func.tracking.model.pack import Pack
from func.tracking.model.state import State
from func.tracking.track import Track, Tracking
from func.tracking.utils import nearest_datetime


def yamato_html(state_inner, summary_items="", details=""):
    return f"""
    <div class="parts-tracking-invoice-block">
      <h4 class="tracking-invoice-block-title">伝票番号：1234-5678-9012</h4>
      <div class="tracking-invoice-block-state">{state_inner}</div>
      <div class="tracking-invoice-block-summary"><ul>{summary_items}</ul></div>
      <div class="tracking-invoice-block-detail"><ol>{details}</ol></div>
    </div>
    """


def yamato_detail(title, when, place):
    return f"""<li><div class="item">{title}</div><div class="date">{when}</div>
    <div class="name"><a href="https://example.com/{place}">{place}</a></div></li>"""


class NearestDatetimeTest(unittest.TestCase):
    def test_same_year(self):
        now = datetime(2026, 9, 29, 12, 0)
        self.assertEqual(nearest_datetime(9, 28, 10, 0, now=now), datetime(2026, 9, 28, 10, 0))

    def test_past_history_across_new_year(self):
        now = datetime(2027, 1, 2, 9, 0)
        self.assertEqual(nearest_datetime(12, 31, 18, 0, now=now), datetime(2026, 12, 31, 18, 0))

    def test_future_estimate_across_new_year(self):
        now = datetime(2026, 12, 30, 9, 0)
        self.assertEqual(nearest_datetime(1, 2, now=now), datetime(2027, 1, 2))

    def test_feb_29_in_non_leap_year(self):
        now = datetime(2027, 12, 20)
        self.assertEqual(nearest_datetime(2, 29, now=now), datetime(2028, 2, 29))


class YamatoParseTest(unittest.TestCase):
    NOW = datetime(2027, 1, 2, 12, 0)

    def test_missing_summary_and_note(self):
        html = yamato_html('<h5 class="tracking-invoice-block-state-title">荷物受付</h5>')

        pack = parse_yamato(html, now=self.NOW)

        self.assertEqual(pack.state_title, "荷物受付")
        self.assertEqual(pack.state_summary, "")
        self.assertEqual(pack.state_note, "")
        self.assertEqual(pack.num, "1234-5678-9012")

    def test_full_block(self):
        html = yamato_html(
            '<h5 class="tracking-invoice-block-state-title">配達完了</h5>'
            '<p class="tracking-invoice-block-state-summary">お届けが完了しました。</p>'
            '<p class="tracking-invoice-block-state-note">置き配</p>',
            summary_items=(
                '<li><div class="item">商品名：</div><div class="data">本</div></li>'
                '<li><div class="item">お届け予定日時：</div><div class="data">01/03　14:00-16:00</div></li>'
            ),
            details=(
                yamato_detail("荷物受付", "12月31日 18:00", "A営業所")
                + yamato_detail("配達完了", "01月02日 10:30", "B営業所")
            ),
        )

        pack = parse_yamato(html, now=self.NOW)

        self.assertEqual(pack.state_type, State.arrival)
        self.assertEqual(pack.state_note, "置き配")
        self.assertEqual(pack.type, "本")
        self.assertEqual(pack.est_date, datetime(2027, 1, 3, 16, 0))
        self.assertEqual([d.time for d in pack.details], [datetime(2026, 12, 31, 18, 0), datetime(2027, 1, 2, 10, 30)])
        self.assertEqual(pack.details[0].place_url, "https://example.com/A営業所")

    def test_est_date_without_time_is_date(self):
        html = yamato_html(
            '<h5 class="tracking-invoice-block-state-title">輸送中</h5>',
            summary_items='<li><div class="item">お届け予定日時：</div><div class="data">01/04</div></li>',
        )

        self.assertEqual(parse_yamato(html, now=self.NOW).est_date, date(2027, 1, 4))

    def test_no_estimate(self):
        html = yamato_html(
            '<h5 class="tracking-invoice-block-state-title">輸送中</h5>',
            summary_items='<li><div class="item">お届け予定日時：</div><div class="data">-</div></li>',
        )

        self.assertIsNone(parse_yamato(html, now=self.NOW).est_date)

    def test_no_package_raises(self):
        with self.assertRaises(ValueError):
            parse_yamato("<html></html>", now=self.NOW)


class SagawaParseTest(unittest.TestCase):
    def test_detail_time_across_new_year(self):
        self.assertEqual(
            parse_sagawa_time("12/31 18:00", now=datetime(2027, 1, 2)),
            datetime(2026, 12, 31, 18, 0),
        )


class ParseTrackingTest(unittest.TestCase):
    def test_sagawa_url(self):
        url = "https://k2k.sagawa-exp.co.jp/p/web/okurijosearch.do?okurijoNo=123456789012"
        self.assertEqual(Track().parse_tracking(url), (Brand.sagawa, "123456789012"))

    def test_number_keeps_given_carrier(self):
        self.assertEqual(Track().parse_tracking("1234", Brand.jp), (Brand.jp, "1234"))


def make_pack(n_details, **kwargs):
    return Pack(
        brand=Brand.yamato,
        num="1234",
        state_title="輸送中",
        state_type=State.other,
        details=[
            Detail(title=f"履歴{i}", place_name="営業所", time=datetime(2026, 9, 1, 0, i))
            for i in range(n_details)
        ],
        **kwargs,
    )


class MakeEmbedTest(unittest.TestCase):
    def test_shows_estimate_type_and_note(self):
        em = make_embed(make_pack(
            1,
            state_summary="輸送中です。",
            state_note="置き配指定",
            type="本",
            est_date=datetime(2026, 10, 2, 16, 0),
        ))

        self.assertEqual(em.description, "輸送中です。\n置き配指定")
        self.assertEqual([(f.name, f.value) for f in em.fields[:2]], [("お届け予定", "10/2 16:00まで"), ("品名・種別", "本")])
        self.assertEqual(em.footer.text, "ヤマト運輸 1234")

    def test_many_details_fit_in_field_limit(self):
        em = make_embed(make_pack(40, est_date=date(2026, 10, 2)))

        self.assertEqual(len(em.fields), 25)
        self.assertEqual(em.fields[0].value, "10/2")
        # 新しい履歴から並ぶ
        self.assertEqual(em.fields[1].name, "履歴39")
        self.assertEqual(em.fields[-1].value, "ほか 17 件")

    def test_exactly_full_has_no_overflow_field(self):
        em = make_embed(make_pack(25))

        self.assertEqual(len(em.fields), 25)
        self.assertEqual(em.fields[-1].name, "履歴0")

    def test_empty_place_name(self):
        pack = make_pack(1)
        pack.details[0].place_name = ""

        self.assertEqual(make_embed(pack).fields[0].value, "9/1 0:00")


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, **kwargs):
        self.sent.append(kwargs)


class FakeBot:
    def __init__(self, channel):
        self.channel = channel

    def get_channel(self, ch_id):
        return self.channel


class NotifyMentionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.channel = FakeChannel()
        cog = TrackingCog.__new__(TrackingCog)
        cog.bot = FakeBot(self.channel)
        self.cb = cog.make_cb(10, "本", 42)

    async def test_update_mentions_owner(self):
        pack = make_pack(1)
        pack.name = "本"

        await self.cb(pack)

        self.assertTrue(self.channel.sent[0]["content"].startswith("<@42> 本の配達状況"))

    async def test_arrival_mentions_owner(self):
        pack = make_pack(1)
        pack.name = "本"
        pack.state_type = State.arrival

        await self.cb(pack)

        self.assertTrue(self.channel.sent[0]["content"].startswith("<@42> 本が到着しました"))

    async def test_give_up_mentions_owner(self):
        await self.cb(None)

        self.assertTrue(self.channel.sent[0]["content"].startswith("<@42> 本の取得に失敗し続けた"))


class FormatTrackingListTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_tracking_list([]), "追跡中の荷物はありません。")

    def test_groups_by_carrier_with_state(self):
        a = Tracking("111", Brand.jp, "本")
        a.latest_pack = make_pack(1)
        b = Tracking("222", Brand.yamato, "服")

        self.assertEqual(
            format_tracking_list([a, b]),
            "**ヤマト運輸**\n・服（222）: 未取得\n\n**日本郵便**\n・本（111）: 輸送中",
        )


if __name__ == "__main__":
    unittest.main()
