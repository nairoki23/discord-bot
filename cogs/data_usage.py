import discord
from dotenv import dotenv_values
from discord.ext import commands
import func.ymobile as ym
# .env読み込み
config = dotenv_values(".env")

class DataUsage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.y=ym.Ymobile(config.get("PHONE_NUMBER"),config.get("YMOBILE_PASSWORD"))
        self.users=[]
        for s in config.get("USER").split(","):
            self.users.append(int(s))
    # Slash Command の定義
    @discord.app_commands.command(name="usage", description="スマホの残りデータ容量確認")
    async def usage(self, interaction: discord.Interaction):
        if(interaction.user.id not in self.users):
            await interaction.response.send_message("これはお前には見せることができません。",ephemeral=True)
            return
        await interaction.response.defer()
        self.y.get()
        print("ああ")
        text = "ご利用状況をご案内します :bulb:\n\nデータ量残量："+str(self.y.remaining/ym.GB_TO_MB)+"GB/"+str(self.y.usable/ym.GB_TO_MB)+"GB"
        embed = discord.Embed(title="データ量", description=text)
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(DataUsage(bot))
