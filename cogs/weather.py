"""天気予報の定期通知と /weather コマンド。毎晩明日の天気、日曜の夜は来週の天気も送る。"""

from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values

from func.weather.forecast import (
    TIMEZONE_NAME,
    fetch_forecast,
    format_date,
    format_day_summary,
    format_hourly,
    format_week,
)
from service.container import get_timer
from utils.channels import get_channel_id
from utils.check_user import interaction_user


config = dotenv_values(".env")
TIMEZONE = ZoneInfo(TIMEZONE_NAME)
NOTIFY_HOUR = 22


def _load_location() -> tuple[float, float] | None:
    latitude, longitude = config.get("WEATHER_LATITUDE"), config.get("WEATHER_LONGITUDE")
    if not latitude or not longitude:
        return None
    return float(latitude), float(longitude)


class WeatherCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timer = get_timer()
        self.location = _load_location()
        name = config.get("WEATHER_LOCATION_NAME") or ""
        self.location_suffix = f"（{name}）" if name else ""

    async def _day_message(self, label: str, day: date) -> str:
        assert self.location is not None
        forecast = await fetch_forecast(*self.location, day, day)
        message = f"## {label} {format_date(day)} の天気{self.location_suffix}\n"
        if forecast.daily:
            message += format_day_summary(forecast.daily[0]) + "\n"
        message += format_hourly(forecast.hourly)
        return message

    async def _week_message(self, label: str, start: date) -> str:
        assert self.location is not None
        end = start + timedelta(days=6)
        forecast = await fetch_forecast(*self.location, start, end)
        message = f"## {label} {format_date(start)}〜{format_date(end)}{self.location_suffix}\n"
        message += "-# 最高/最低気温・降水確率\n"
        message += format_week(forecast.daily)
        return message

    @app_commands.command(name="weather", description="天気予報を表示します")
    @app_commands.describe(period="今日・明日は1時間ごと、週間は明日から7日間")
    async def weather(self, interaction: discord.Interaction, period: Literal["今日", "明日", "週間"] = "明日"):
        if not await interaction_user(interaction):
            return
        if self.location is None:
            await interaction.response.send_message(
                "地点が設定されていません。`.env` に `WEATHER_LATITUDE` と `WEATHER_LONGITUDE` を設定してください。",
                ephemeral=True,
            )
            return
        await interaction.response.defer()
        today = datetime.now(TIMEZONE).date()
        try:
            if period == "週間":
                message = await self._week_message("週間天気", today + timedelta(days=1))
            elif period == "今日":
                message = await self._day_message("今日", today)
            else:
                message = await self._day_message("明日", today + timedelta(days=1))
        except Exception as exc:
            print(f"Weather forecast fetch failed: {exc}")
            await interaction.followup.send("天気予報を取得できませんでした。")
            return
        await interaction.followup.send(message)

    async def cog_load(self):
        channel_id = get_channel_id("weather_channel_id") or get_channel_id("notification_channel_id")
        if not channel_id or self.location is None:
            return

        async def notify() -> datetime:
            tomorrow = datetime.now(TIMEZONE).date() + timedelta(days=1)
            builders = []
            # 日曜の夜（翌日が月曜）は来週一週間分も送る
            if tomorrow.weekday() == 0:
                builders.append(lambda: self._week_message("来週の天気", tomorrow))
            builders.append(lambda: self._day_message("明日", tomorrow))
            for build in builders:
                try:
                    message = await build()
                    channel = await self.bot.fetch_channel(channel_id)
                    await channel.send(message)
                except Exception as exc:
                    print(f"Weather notification failed: {exc}")
            return self._next_notification_time()

        self.timer.schedule(self._next_notification_time(), cb=notify)

    @staticmethod
    def _next_notification_time() -> datetime:
        now = datetime.now(TIMEZONE)
        next_run = now.replace(hour=NOTIFY_HOUR, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        # TimerService uses naive local datetimes.
        return next_run.replace(tzinfo=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(WeatherCog(bot))
