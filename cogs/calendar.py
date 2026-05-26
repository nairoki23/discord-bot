import discord
from discord.ext import commands
import aiohttp
from utils.check_user import interaction_user
from service.container  import get_timer
from datetime import datetime,timedelta
from icalendar import Calendar
from dotenv import dotenv_values
import asyncio 
config = dotenv_values(".env")


async def fetch_calendar(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        text = await response.text()
        return Calendar.from_ical(text)

async def fetch_tomorrow_events():
    tomorrow = datetime.now().date() + timedelta(days=1)

    auth = aiohttp.BasicAuth(
        config.get("CALDAV_USER"),
        config.get("CALDAV_PASS")
    )

    async with aiohttp.ClientSession(auth=auth) as session:
        calendars = await asyncio.gather(*[
            fetch_calendar(session, url)
            for url in config.get("CALDAV_URLS").split(",")
        ])

    events = []

    for cal in calendars:
        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            start = component.get("dtstart").dt
            summary = str(component.get("summary"))

            if isinstance(start, datetime):
                event_date = start.date()
                time_str = start.strftime("%H:%M")
            else:
                event_date = start
                time_str = "終日"

            if event_date == tomorrow:
                events.append(f"{time_str} - {summary}")

    return sorted(events)



class CalendarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timer=get_timer()
    
    # Slash Command の定義
    @discord.app_commands.command(name="today", description="今日の全予定")
    async def today(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
    
    async def cog_load(self):
        async def cb():
            ch = await self.bot.fetch_channel(config.get("NOTIFICATION_CHANNEL_ID"))
            events = await fetch_tomorrow_events()
            if events:
                message = "## 明日の予定\n" + "\n".join(
                    f"- {e}" for e in events
                )
            else:
                message = "明日の予定は登録されていません"

            await ch.send(message)
            return (datetime.now() + timedelta(days=1)).replace(hour=22,minute=0,second=0,microsecond=0)
        self.timer.schedule(datetime.now().replace(hour=22,minute=0,second=0,microsecond=0),cb=cb)
    

async def setup(bot: commands.Bot):
    await bot.add_cog(CalendarCog(bot))
