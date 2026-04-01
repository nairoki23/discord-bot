from func.ymobile.ymobile import Ymobile 
import requests	
from bs4 import BeautifulSoup as bs
from datetime import datetime
import discord
from dotenv import dotenv_values
from discord.ext import commands
from utils.check_user import interaction_user
# .env読み込み
config = dotenv_values(".env")
GB_TO_MB = 1024

class DataUsage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.y=Ymobile(config.get("PHONE_NUMBER"),config.get("YMOBILE_PASSWORD"))
        self.users=[]
        for s in config.get("USER").split(","):
            self.users.append(int(s))
    # Slash Command の定義
    @discord.app_commands.command(name="usage", description="スマホの残りデータ容量確認")
    async def usage(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        await interaction.response.defer()
        data=self.y.get()
        try:
            text = "ご利用状況をご案内します :bulb:\n\nデータ量残量："+str(data.remaining/1000)+"GB/"+str(data.all_usable/1000)+"GB"
            embed = discord.Embed(title="データ量", description=text)
            embed.add_field(name="今月の使用量", value=str(data.used/1000)+"GB", inline=True)
            embed.add_field(name="今月のくりこし分", value=str(data.kurikoshi/1000)+"GB", inline=True)
            embed.set_footer(text=data.mon+"\t"+data.tel)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(e)
async def setup(bot: commands.Bot):
    await bot.add_cog(DataUsage(bot))
