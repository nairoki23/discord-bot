"""Discord commands and notifications backed by Google Calendar."""

import asyncio
from datetime import date, datetime, timedelta
import re
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values

from service.container import get_google_calendar_service, get_timer
from service.google.calendar import CalendarEvent
from utils.channels import get_channel_id
from utils.check_user import interaction_user


config = dotenv_values(".env")
TIMEZONE = ZoneInfo(config.get("GOOGLE_CALENDAR_TIMEZONE") or "Asia/Tokyo")
WEEKDAYS = ("月", "火", "水", "木", "金", "土", "日")


_DATE_INPUT = re.compile(
    r"^(?:(?:(?P<year>\d{4})[-/])?(?:(?P<month>\d{1,2})[-/])?"
    r"(?P<day>\d{1,2})(?:\s+(?P<hour>\d{1,2}):(?P<minute>\d{2}))?"
    r"|(?P<today_hour>\d{1,2}):(?P<today_minute>\d{2}))$"
)


def parse_local_datetime(value: str, *, now: datetime | None = None) -> date | datetime:
    """Parse a compact calendar input, returning ``date`` for all-day events."""
    match = _DATE_INPUT.fullmatch(value.strip().replace("T", " "))
    if not match:
        raise ValueError(
            "日時は `YYYY-MM-DD HH:MM`、`MM-DD HH:MM`、`DD HH:MM`、または `HH:MM`（今日）形式で入力してください"
        )

    current = now or datetime.now(TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=TIMEZONE)
    else:
        current = current.astimezone(TIMEZONE)
    groups = match.groupdict()
    hour = groups["hour"] or groups["today_hour"]
    minute = groups["minute"] or groups["today_minute"]
    year_text, month_text = groups["year"], groups["month"]
    if year_text and not month_text:
        raise ValueError("年を指定する場合は月日も指定してください")
    if groups["day"] is None:
        parsed_date = current.date()
    else:
        year = int(year_text) if year_text else current.year
        month = int(month_text) if month_text else current.month
        try:
            parsed_date = date(year, month, int(groups["day"]))
        except ValueError:
            raise ValueError("日付または時刻が正しくありません") from None
    try:
        # MM-DD uses this year, unless that date has already passed.  A bare DD
        # deliberately stays in the current month, as documented by the command.
        if groups["day"] is not None and not year_text and month_text and parsed_date < current.date():
            parsed_date = parsed_date.replace(year=year + 1)
        if hour is None:
            return parsed_date
        return datetime(
            parsed_date.year,
            parsed_date.month,
            parsed_date.day,
            int(hour),
            int(minute),
            tzinfo=TIMEZONE,
        )
    except ValueError:
        raise ValueError("日付または時刻が正しくありません") from None


def format_events(events: list[CalendarEvent], *, include_date: bool = False) -> str:
    """Render events into Discord-friendly, chronologically ordered list items."""
    lines: list[str] = []
    for event in events:
        if event.is_all_day:
            event_date = event.start
            assert isinstance(event_date, date)
            prefix = "終日"
        else:
            start = event.start
            assert isinstance(start, datetime)
            event_date = start.date()
            prefix = start.strftime("%H:%M")
        date_prefix = ""
        if include_date:
            date_prefix = f"{event_date:%m/%d}({WEEKDAYS[event_date.weekday()]}) "
        calendar_suffix = f" [{event.calendar_name}]" if event.calendar_name else ""
        lines.append(f"- {date_prefix}{prefix} {event.summary}{calendar_suffix}")
    return "\n".join(lines)


class CalendarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = get_google_calendar_service()
        self.timer = get_timer()

    async def _list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return await asyncio.to_thread(self.service.list_events, start, end)

    async def _send_events(self, interaction, title, start, end, *, include_date: bool) -> None:
        if not self.service.is_available():
            await interaction.response.send_message(
                "Google Calendar は認証されていません。先に `/google_auth` を実行してください。",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        try:
            events = await self._list_events(start, end)
        except Exception as exc:
            print(f"Google Calendar event list failed: {exc}")
            await interaction.followup.send("Google Calendar の予定を取得できませんでした。")
            return
        message = f"## {title}\n"
        message += format_events(events, include_date=include_date) if events else "予定は登録されていません"
        await interaction.followup.send(message)

    @app_commands.command(name="today", description="今日の予定")
    async def today(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        start, end = self.service.today_range()
        await self._send_events(interaction, "今日の予定", start, end, include_date=False)

    @app_commands.command(name="calendar_week", description="今週の予定")
    async def calendar_week(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        start, end = self.service.week_range()
        await self._send_events(interaction, "今週の予定", start, end, include_date=True)

    @app_commands.command(name="calendar_add", description="Google Calendar に予定を追加します")
    @app_commands.describe(summary="予定のタイトル", start="開始（YYYY-MM-DD／MM-DD／DD [HH:MM]、HH:MM は今日。時刻なしで終日）", end="終了（省略時: 時刻ありは1時間後、終日は翌日）", description="詳細（任意）", location="場所（任意）")
    async def calendar_add(self, interaction: discord.Interaction, summary: str, start: str, end: str | None = None, description: str = "", location: str = ""):
        if not await interaction_user(interaction):
            return
        if not self.service.is_available():
            await interaction.response.send_message("Google Calendar は認証されていません。先に `/google_auth` を実行してください。", ephemeral=True)
            return
        try:
            start_at = parse_local_datetime(start)
            end_at = parse_local_datetime(end) if end else None
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.defer()
        try:
            event = await asyncio.to_thread(self.service.create_event, summary, start_at, end_at, description, location)
        except ValueError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        except Exception as exc:
            print(f"Google Calendar event creation failed: {exc}")
            await interaction.followup.send("予定を追加できませんでした。")
            return
        link = f"\n{event.html_link}" if event.html_link else ""
        await interaction.followup.send(f"予定を追加しました: {event.summary}{link}")

    async def cog_load(self):
        channel_id = get_channel_id("notification_channel_id")
        if not channel_id:
            return

        async def notify_tomorrow() -> datetime:
            start, end = self.service.tomorrow_range()
            try:
                events = await self._list_events(start, end) if self.service.is_available() else []
                channel = await self.bot.fetch_channel(channel_id)
                message = "## 明日の予定\n"
                message += format_events(events) if events else "予定は登録されていません"
                await channel.send(message)
            except Exception as exc:
                print(f"Google Calendar tomorrow notification failed: {exc}")
            return self._next_notification_time()

        self.timer.schedule(self._next_notification_time(), cb=notify_tomorrow)

    @staticmethod
    def _next_notification_time() -> datetime:
        now = datetime.now(TIMEZONE)
        next_run = now.replace(hour=22, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        # TimerService uses naive local datetimes.
        return next_run.replace(tzinfo=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(CalendarCog(bot))
