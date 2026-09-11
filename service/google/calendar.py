from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build


@dataclass(frozen=True)
class CalendarEvent:
    summary: str
    start: date | datetime
    end: date | datetime
    description: str = ""
    location: str = ""
    html_link: str = ""
    calendar_name: str = ""

    @property
    def is_all_day(self) -> bool:
        return isinstance(self.start, date) and not isinstance(self.start, datetime)


class GoogleCalendarService:
    def __init__(
        self,
        get_creds: Callable,
        calendar_id: str = "primary",
        timezone: str = "Asia/Tokyo",
    ):
        self.get_creds = get_creds
        self.calendar_id = calendar_id
        self.timezone = ZoneInfo(timezone)

    def is_available(self) -> bool:
        return self.get_creds() is not None

    def today_range(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        now = self._localize(now or datetime.now(self.timezone))
        start = datetime.combine(now.date(), time.min, self.timezone)
        return start, start + timedelta(days=1)

    def week_range(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        now = self._localize(now or datetime.now(self.timezone))
        monday = now.date() - timedelta(days=now.weekday())
        start = datetime.combine(monday, time.min, self.timezone)
        return start, start + timedelta(days=7)

    def tomorrow_range(self, now: datetime | None = None) -> tuple[datetime, datetime]:
        today_start, _ = self.today_range(now)
        start = today_start + timedelta(days=1)
        return start, start + timedelta(days=1)

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        api = self._service()
        events: list[CalendarEvent] = []
        for calendar_id, calendar_name in self._list_calendars(api):
            events.extend(
                self._list_calendar_events(api, calendar_id, calendar_name, start, end)
            )
        return sorted(events, key=self._event_sort_key)

    def _list_calendars(self, api) -> list[tuple[str, str]]:
        """Return every calendar listed for the authenticated Google account."""
        request = api.calendarList().list(showHidden=True)
        calendars: list[tuple[str, str]] = []
        while request is not None:
            response = request.execute()
            for item in response.get("items", []):
                calendar_id = item.get("id")
                if calendar_id:
                    calendars.append((calendar_id, item.get("summary") or calendar_id))
            request = api.calendarList().list_next(request, response)
        return calendars

    def _list_calendar_events(
        self,
        api,
        calendar_id: str,
        calendar_name: str,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        request = api.events().list(
            calendarId=calendar_id,
            timeMin=self._localize(start).isoformat(),
            timeMax=self._localize(end).isoformat(),
            singleEvents=True,
            orderBy="startTime",
            timeZone=str(self.timezone),
        )
        events: list[CalendarEvent] = []
        while request is not None:
            response = request.execute()
            events.extend(
                self._parse_event(item, calendar_name=calendar_name)
                for item in response.get("items", [])
            )
            request = api.events().list_next(request, response)
        return events

    def create_event(
        self,
        summary: str,
        start: date | datetime,
        end: date | datetime | None = None,
        description: str = "",
        location: str = "",
    ) -> CalendarEvent:
        is_all_day = isinstance(start, date) and not isinstance(start, datetime)
        if is_all_day:
            if end is not None and isinstance(end, datetime):
                raise ValueError("開始と終了はどちらも終日、またはどちらも時刻付きで入力してください")
            all_day_end = end or start
            assert isinstance(all_day_end, date)
            if all_day_end < start:
                raise ValueError("終了日は開始日以降にしてください")
            # Google Calendar represents all-day event end dates as exclusive;
            # command input, like the Calendar UI, treats the end date as inclusive.
            body = {
                "summary": summary.strip(),
                "start": {"date": start.isoformat()},
                "end": {"date": (all_day_end + timedelta(days=1)).isoformat()},
            }
        else:
            assert isinstance(start, datetime)
            if end is not None and not isinstance(end, datetime):
                raise ValueError("開始と終了はどちらも終日、またはどちらも時刻付きで入力してください")
            start = self._localize(start)
            timed_end = self._localize(end or (start + timedelta(hours=1)))
            if timed_end <= start:
                raise ValueError("終了日時は開始日時より後にしてください")
            body = {
                "summary": summary.strip(),
                "start": {"dateTime": start.isoformat(), "timeZone": str(self.timezone)},
                "end": {"dateTime": timed_end.isoformat(), "timeZone": str(self.timezone)},
            }
        if description:
            body["description"] = description
        if location:
            body["location"] = location

        item = self._service().events().insert(
            calendarId=self.calendar_id,
            body=body,
        ).execute()
        return self._parse_event(item)

    def _service(self):
        creds = self.get_creds()
        if creds is None:
            raise RuntimeError("Googleアカウントが認証されていません")
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    def _parse_event(self, item: dict, *, calendar_name: str = "") -> CalendarEvent:
        return CalendarEvent(
            summary=item.get("summary", "(タイトルなし)"),
            start=self._parse_datetime(item["start"]),
            end=self._parse_datetime(item["end"]),
            description=item.get("description", ""),
            location=item.get("location", ""),
            html_link=item.get("htmlLink", ""),
            calendar_name=calendar_name,
        )

    @staticmethod
    def _event_sort_key(event: CalendarEvent) -> tuple[date, time]:
        if event.is_all_day:
            assert isinstance(event.start, date)
            return event.start, time.min
        assert isinstance(event.start, datetime)
        return event.start.date(), event.start.timetz().replace(tzinfo=None)

    def _parse_datetime(self, value: dict) -> date | datetime:
        if "date" in value:
            return date.fromisoformat(value["date"])
        parsed = datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00"))
        return self._localize(parsed)

    def _localize(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=self.timezone)
        return value.astimezone(self.timezone)
