import discord
from discord.ext import commands
import json 
from datetime import datetime,timedelta
day_map = {'m': '月曜', 't': '火曜', 'w': '水曜', 'h': '木曜', 'f': '金曜'}

schedule={}

with open("utils/classweek.json", 'r', encoding='utf-8') as f:
    schedule = json.load(f)

def check(today:datetime):
    code=schedule.get(today.strftime("%Y/%m/%d"))
    print(today)
    if code:
        return "今日は"+day_map[code[0]]+"第"+code[1:]+"回授業日です。"
    else:
        return "今日は非授業日です。"


class ClassWeek(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash Command の定義
    @discord.app_commands.command(name="class", description="今日の授業週")
    async def today_class(self, interaction: discord.Interaction):
        interaction.response.send_message(check(datetime.now()))
    
    @discord.app_commands.command(name="tr_class", description="明日の授業週")
    async def tr_class(self, interaction: discord.Interaction):
        interaction.response.send_message(check(datetime.now() + timedelta(days=1)))

async def setup(bot: commands.Bot):
    await bot.add_cog(ClassWeek(bot))

if __name__ == "__main__":
    print(check(datetime.now()))