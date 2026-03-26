import discord
from discord.ext import commands
from func.class_schedule.schedule import week_sc_message,class_check_message
from datetime import timedelta,date

class ClassSchedule(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash Command の定義
    @discord.app_commands.command(name="class", description="今日の授業週")
    async def today_class(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_message("今日は"+class_check_message(date.today()))
        except Exception as e:
            print(e)

    @discord.app_commands.command(name="tr_class", description="明日の授業週")
    async def tr_class(self, interaction: discord.Interaction):
        await interaction.response.send_message("明日は"+class_check_message(date.today() + timedelta(days=1)))

    @discord.app_commands.command(name="next_week", description="来週の学校予定")
    async def next_week(self, interaction: discord.Interaction):
        today = date.today()
        res="来週の予定\n"
        res+=week_sc_message(today - timedelta(days=today.weekday())+ timedelta(days=7))
        await interaction.response.send_message(res)


async def setup(bot: commands.Bot):
    await bot.add_cog(ClassSchedule(bot))
