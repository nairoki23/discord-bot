import unittest
from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from cogs.calendar import format_events, parse_local_datetime
from service import container
from service.google.calendar import CalendarEvent, GoogleCalendarService


JST = ZoneInfo("Asia/Tokyo")


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeEventsResource:
    def __init__(self):
        self.list_kwargs = []
        self.insert_kwargs = None

    def list(self, **kwargs):
        self.list_kwargs.append(kwargs)
        calendar_id = kwargs["calendarId"]
        return FakeRequest({
            "items": [
                {
                    "summary": f"朝会 ({calendar_id})",
                    "start": {"dateTime": "2026-08-17T09:00:00+09:00"},
                    "end": {"dateTime": "2026-08-17T09:30:00+09:00"},
                },
                {
                    "summary": "休暇",
                    "start": {"date": "2026-08-18"},
                    "end": {"date": "2026-08-19"},
                },
            ]
        })

    def list_next(self, request, response):
        return None

    def insert(self, **kwargs):
        self.insert_kwargs = kwargs
        return FakeRequest({
            **kwargs["body"],
            "htmlLink": "https://calendar.google.com/event/1",
        })


class FakeApi:
    def __init__(self):
        self.events_resource = FakeEventsResource()

    def events(self):
        return self.events_resource

    def calendarList(self):
        return FakeCalendarListResource()


class FakeCalendarListResource:
    def list(self, **kwargs):
        return FakeRequest({
            "items": [
                {"id": "primary", "summary": "個人"},
                {"id": "work@example.com", "summary": "仕事"},
            ]
        })

    def list_next(self, request, response):
        return None


class GoogleCalendarServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = GoogleCalendarService(lambda: object())

    def test_week_range_is_monday_through_next_monday(self):
        start, end = self.service.week_range(datetime(2026, 8, 19, 12, tzinfo=JST))
        self.assertEqual(start, datetime(2026, 8, 17, tzinfo=JST))
        self.assertEqual(end, datetime(2026, 8, 24, tzinfo=JST))

    def test_list_events_parses_timed_and_all_day_events(self):
        api = FakeApi()
        with patch("service.google.calendar.build", return_value=api):
            events = self.service.list_events(
                datetime(2026, 8, 17, tzinfo=JST),
                datetime(2026, 8, 24, tzinfo=JST),
            )
        self.assertEqual(events[0].summary, "朝会 (primary)")
        self.assertEqual(events[0].start.hour, 9)
        all_day_event = next(event for event in events if event.is_all_day)
        self.assertEqual(all_day_event.start, date(2026, 8, 18))
        self.assertEqual(events[0].calendar_name, "個人")
        self.assertEqual(
            [kwargs["calendarId"] for kwargs in api.events_resource.list_kwargs],
            ["primary", "work@example.com"],
        )

    def test_create_event_defaults_to_one_hour(self):
        api = FakeApi()
        with patch("service.google.calendar.build", return_value=api):
            event = self.service.create_event(
                "打ち合わせ",
                datetime(2026, 8, 17, 10, tzinfo=JST),
                location="会議室",
            )
        body = api.events_resource.insert_kwargs["body"]
        self.assertEqual(body["end"]["dateTime"], "2026-08-17T11:00:00+09:00")
        self.assertEqual(event.location, "会議室")
        self.assertTrue(event.html_link)

    def test_create_event_creates_all_day_event_for_dates(self):
        api = FakeApi()
        with patch("service.google.calendar.build", return_value=api):
            self.service.create_event("休暇", date(2026, 8, 17))
        body = api.events_resource.insert_kwargs["body"]
        self.assertEqual(body["start"], {"date": "2026-08-17"})
        self.assertEqual(body["end"], {"date": "2026-08-18"})

    def test_create_event_rejects_invalid_end(self):
        with self.assertRaisesRegex(ValueError, "終了日時"):
            self.service.create_event(
                "不正",
                datetime(2026, 8, 17, 10, tzinfo=JST),
                datetime(2026, 8, 17, 9, tzinfo=JST),
            )

    def test_container_returns_a_shared_calendar_service(self):
        previous_service = container._google_calendar_service
        previous_auth = container._google_auth
        try:
            container._google_calendar_service = None
            container._google_auth = None

            service = container.get_google_calendar_service()

            self.assertIs(service, container.get_google_calendar_service())
            self.assertTrue(callable(service.get_creds))
        finally:
            container._google_calendar_service = previous_service
            container._google_auth = previous_auth


class CalendarCogHelperTests(unittest.TestCase):
    def test_parse_local_datetime_uses_configured_timezone(self):
        parsed = parse_local_datetime("2026-08-17 22:00")
        self.assertEqual(parsed.isoformat(), "2026-08-17T22:00:00+09:00")

    def test_parse_local_datetime_without_time_is_all_day(self):
        parsed = parse_local_datetime("2026-08-17")
        self.assertEqual(parsed, date(2026, 8, 17))

    def test_parse_local_datetime_uses_current_year_for_month_and_day(self):
        parsed = parse_local_datetime("09-13", now=datetime(2026, 9, 12, tzinfo=JST))
        self.assertEqual(parsed, date(2026, 9, 13))

    def test_parse_local_datetime_moves_past_month_and_day_to_next_year(self):
        parsed = parse_local_datetime("09-11", now=datetime(2026, 9, 12, tzinfo=JST))
        self.assertEqual(parsed, date(2027, 9, 11))

    def test_parse_local_datetime_uses_current_month_for_day_only(self):
        parsed = parse_local_datetime("15 09:00", now=datetime(2026, 9, 12, tzinfo=JST))
        self.assertEqual(parsed, datetime(2026, 9, 15, 9, tzinfo=JST))

    def test_parse_local_datetime_uses_today_when_day_is_omitted(self):
        parsed = parse_local_datetime("09:00", now=datetime(2026, 9, 12, 8, tzinfo=JST))
        self.assertEqual(parsed, datetime(2026, 9, 12, 9, tzinfo=JST))

    def test_format_events_supports_all_day_event(self):
        event = CalendarEvent("休暇", date(2026, 8, 17), date(2026, 8, 18))
        self.assertEqual(format_events([event], include_date=True), "- 08/17(月) 終日 休暇")


if __name__ == "__main__":
    unittest.main()
