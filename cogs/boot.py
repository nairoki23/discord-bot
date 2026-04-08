from discord.ext import commands
from discord import app_commands
from datetime import datetime
import discord

class BootCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.boot_time=None
    async def cog_load(self):  # 関数名的に起動時に一回呼ばれる
        self.boot_time=datetime.now()

    @app_commands.command(name="boot-time", description="cog_loadの時間")
    async def show_boot_time(self, interaction: discord.Interaction):
        if self.boot_time is None:
            await interaction.response.send_message(
                content="不明",
            )
        else:
            await interaction.response.send_message(self.boot_time.strftime("%Y/%m/%d %H:%M:%S"))


async def setup(bot: commands.Bot):
    await bot.add_cog(BootCog(bot))
