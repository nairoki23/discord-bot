import discord
from discord.ext import commands,tasks
from func.tracking.fetch.yamato import get_data

class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.periodic_task.start()
    
    def cog_unload(self):
        self.periodic_task.cancel()
    
    @tasks.loop(minutes=5)
    async def periodic_task(self):
        pass#TODO 荷物の確認

    # Slash Command の定義
    @discord.app_commands.command(name="tracking-single-check", description="宅配状況の一回だけの確認")
    async def timer(self, interaction: discord.Interaction,tracking_num:str):
        await interaction.response.defer()
        data=get_data(tracking_num)[0]
        embed = discord.Embed(title="今の状況", description=data["state"]["title"])
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
