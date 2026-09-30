import platform
from datetime import datetime, timedelta

from discord.ext import commands
from discord import app_commands
import discord

from utils.check_user import interaction_user


def _format_uptime(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}日")
    if days or hours:
        parts.append(f"{hours}時間")
    parts.append(f"{minutes}分")
    return "".join(parts)


class BootCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.boot_time = None

    async def cog_load(self):  # 関数名的に起動時に一回呼ばれる
        self.boot_time = datetime.now()

    @app_commands.command(name="status", description="Botの稼働状況を確認します")
    async def status(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        if self.boot_time is None:
            await interaction.response.send_message(content="不明")
            return
        embed = discord.Embed(title="稼働状況")
        embed.add_field(
            name="起動日時",
            value=self.boot_time.strftime("%Y/%m/%d %H:%M:%S"),
            inline=False,
        )
        embed.add_field(
            name="稼働時間",
            value=_format_uptime(datetime.now() - self.boot_time),
            inline=False,
        )
        embed.add_field(
            name="実行環境",
            value=(
                f"Python {platform.python_version()} / discord.py {discord.__version__}\n"
                f"{platform.system()} {platform.release()}"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(BootCog(bot))
