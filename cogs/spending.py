import discord
from discord.ext import commands

class Spending(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Slash Command の定義
    @discord.app_commands.command(name="spending", description="支出")
    async def spending(self, interaction: discord.Interaction):
        text = f"Pong! {round(self.bot.latency * 1000)}ms"
        embed = discord.Embed(title="Latency", description=text)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Spending(bot))
