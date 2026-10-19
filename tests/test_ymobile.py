import unittest
from unittest import mock

import requests

from cogs.data_usage import build_embed
from func.ymobile import ymobile
from func.ymobile.ymobile import Ymobile, YmobileError, YmobileMaintenance, get_mb, parse


def row(th, td):
    return f"<table><tbody><tr><th>{th}</th><td>{td}</td></tr></tbody></table>"


def usage_page(*rows):
    return (
        '<h2 class="res-fs16">10月のご利用状況</h2>'
        '<p class="res-fs14">10/1〜10/31</p>'
        '<p class="res-fs14">090-0000-0000</p>'
        f'<div class="list-toggle-content">{"".join(rows)}</div>'
    )


LOGIN_PAGE = '<form><input type="hidden" name="ticket" value="T"></form>'
MAINTENANCE_PAGE = (
    '<html><head><meta charset="utf-8"></head><body><div id="contents-body">'
    '<p>ご利用ありがとうございます。</p>'
    '<p>現在、メンテナンスを実施中のため、サービスをご利用いただけません。</p>'
    '</div></body></html>'
)
LINK_PAGE = '<form><input name="mfiv" value="IV"><input name="mfym" value="YM"></form>'
USAGE_PAGE = usage_page(
    row("基本データ量 残り", "20GB／20GB"),
    row("前月からのくりこし分", "1.5GB"),
    row("使用量 合計", "3.25GB"),
)


class FakeResponse:
    def __init__(self, text="", status=200):
        # 実サイト同様、ヘッダに charset が無く bytes で受け取る想定
        self.content = text.encode("utf-8")
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status}")


class FakeSession:
    """GET/POST の URL ごとに返すレスポンスを決める Session"""

    def __init__(self, pages):
        self.pages = pages
        self.posts = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def _respond(self, url):
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        return FakeResponse(page)

    def get(self, url, timeout=None):
        return self._respond(url)

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, data))
        return self._respond(url)


def pages(**override):
    p = {
        ymobile.LOGIN_PAGE_URL: LOGIN_PAGE,
        ymobile.LOGIN_POST_URL: "",
        ymobile.USAGE_LINK_URL: LINK_PAGE,
        ymobile.USAGE_PAGE_URL: USAGE_PAGE,
    }
    p.update(override)
    return p


class GetMbTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(get_mb("1.5GB"), 1500)
        self.assertEqual(get_mb("0.25GB"), 250)
        self.assertEqual(get_mb("10GB"), 10000)
        self.assertEqual(get_mb("500MB"), 500)
        self.assertEqual(get_mb("1,024MB"), 1024)
        self.assertEqual(get_mb(" 3.0 GB "), 3000)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            get_mb("-")


class ParseTests(unittest.TestCase):
    def test_parse(self):
        data = parse(USAGE_PAGE)
        self.assertEqual(data.base, 20000)
        self.assertEqual(data.kurikoshi, 1500)
        self.assertEqual(data.used, 3250)
        self.assertEqual(data.all_usable, 21500)
        self.assertEqual(data.remaining, 18250)
        self.assertEqual(data.mon, "10月のご利用状況")
        self.assertEqual(data.period, "10/1〜10/31")
        self.assertEqual(data.tel, "090-0000-0000")

    def test_integer_gb_and_extra_rows(self):
        data = parse(usage_page(
            row("基本データ量 残り", "30GB／30GB"),
            row("今月のくりこし分", "2GB"),
            row("追加データ量", "500MB"),
            row("その他", "-"),
            row("使用量 合計", "0GB"),
        ))
        self.assertEqual(data.all_usable, 32500)
        self.assertEqual(data.remaining, 32500)

    def test_unexpected_page(self):
        with self.assertRaises(YmobileError):
            parse("<html>メンテナンス中です</html>")


class GetTests(unittest.TestCase):
    def test_maintenance_is_not_retried(self):
        sessions = []

        def factory():
            s = FakeSession(pages(**{ymobile.LOGIN_PAGE_URL: MAINTENANCE_PAGE}))
            sessions.append(s)
            return s

        with mock.patch.object(ymobile.requests, "Session", side_effect=factory):
            with self.assertRaises(YmobileMaintenance):
                Ymobile("0", "pw").get()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].posts, [])

    def test_parse_bytes_without_header_charset(self):
        data = parse(('<meta charset="utf-8">' + USAGE_PAGE).encode("utf-8"))
        self.assertEqual(data.kurikoshi, 1500)

    def test_new_session_each_time(self):
        sessions = []

        def factory():
            s = FakeSession(pages())
            sessions.append(s)
            return s

        with mock.patch.object(ymobile.requests, "Session", side_effect=factory):
            y = Ymobile("09000000000", "pw")
            y.get()
            y.get()

        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0].posts[0], (ymobile.LOGIN_POST_URL, {
            "telnum": "09000000000", "password": "pw", "ticket": "T",
        }))
        self.assertEqual(sessions[0].posts[1], (ymobile.USAGE_PAGE_URL, {"mfiv": "IV", "mfym": "YM"}))

    def test_retry_after_failure(self):
        results = iter([
            FakeSession(pages(**{ymobile.USAGE_LINK_URL: "<html>ログインしてください</html>"})),
            FakeSession(pages()),
        ])
        with mock.patch.object(ymobile.requests, "Session", side_effect=lambda: next(results)):
            data = Ymobile("0", "pw").get()
        self.assertEqual(data.remaining, 18250)

    def test_raise_after_retries(self):
        with mock.patch.object(
            ymobile.requests, "Session",
            side_effect=lambda: FakeSession(pages(**{ymobile.LOGIN_PAGE_URL: requests.Timeout("timeout")})),
        ):
            with self.assertRaises(requests.Timeout):
                Ymobile("0", "pw").get()


class EmbedTests(unittest.TestCase):
    def test_embed(self):
        embed = build_embed(parse(USAGE_PAGE))
        self.assertIn("18.25GB/21.5GB", embed.description)
        self.assertEqual([(f.name, f.value) for f in embed.fields], [
            ("今月の使用量", "3.25GB"),
            ("今月のくりこし分", "1.5GB"),
        ])
        self.assertEqual(embed.footer.text, "10月のご利用状況\t090-0000-0000")


if __name__ == "__main__":
    unittest.main()
