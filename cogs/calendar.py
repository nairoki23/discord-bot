import discord
from discord.ext import commands
from utils.check_user import interaction_user
from service.container  import get_timer
from datetime import datetime

class Calendar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    async def cog_load(self):#関数名的に起動時に一回呼ばれる
        #get_timer().schedule(datetime.now(),cb=)
    # Slash Command の定義
    @discord.app_commands.command(name="today", description="今日の全予定")
    async def today(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(Calendar(bot))
