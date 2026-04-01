import discord
from discord.ext import commands
import re
from datetime import datetime, timedelta
from service.container  import get_timer


def parse_duration(s: str) -> timedelta:
    s = s.strip().lower()

    # --- パターン1: 数字のみ ---
    if re.fullmatch(r"\d+(\.\d+)?", s):
        value = float(s)

        if value < 15:
            seconds = value * 60
        elif value <= 90:
            seconds = value
        else:
            seconds = value * 60

        return timedelta(seconds=seconds)

    # --- パターン2: hms形式 ---
    pattern = r"(?:(?P<h>\d+(\.\d+)?)h)?(?:(?P<m>\d+(\.\d+)?)m)?(?:(?P<s>\d+(\.\d+)?)s)?"
    match = re.fullmatch(pattern, s)

    if match:
        h = float(match.group("h") or 0)
        m = float(match.group("m") or 0)
        sec = float(match.group("s") or 0)

        return timedelta(
            hours=h,
            minutes=m,
            seconds=sec
        )

    raise ValueError(f"Invalid duration format: {s}")

def format_timedelta_ja(td: timedelta) -> str:
    total_seconds = td.total_seconds()

    # 符号対応
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)

    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60  # float

    parts = []

    if days:
        parts.append(f"{days}日")
    if hours:
        parts.append(f"{hours}時間")
    if minutes:
        parts.append(f"{minutes}分")

    # 秒は「整数なら整数」「小数ならそのまま」
    if seconds:
        if seconds.is_integer():
            parts.append(f"{int(seconds)}秒")
        else:
            parts.append(f"{seconds:.2f}秒")

    # 全部0のとき
    if not parts:
        parts.append("0秒")

    return sign + "".join(parts)

def send_cb(sender,description:str):
    async def cb():
        await sender(description+"の時間になりました。")
    return cb

class Timer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timer=get_timer(bot.loop)
    # Slash Command の定義
    @discord.app_commands.command(name="timer", description="タイマー")
    async def timer(self, interaction: discord.Interaction,time:str,description:str="タイマー"):
        try:
            parsed_time = parse_duration(time)
            self.timer.schedule(datetime.now()+parsed_time,cb=send_cb(interaction.followup.send,description))
            await interaction.response.send_message(format_timedelta_ja(parsed_time)+"後に"+description)
        except Exception as e:
            print(e)
async def setup(bot: commands.Bot):
    await bot.add_cog(Timer(bot))
