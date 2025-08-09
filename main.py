from dotenv import load_dotenv
import os

# .envファイルの内容を読み込む
load_dotenv()

import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(intents=intents, command_prefix="!")
tree = bot.tree

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}.")
    await tree.sync()
    print("Synced slash commands.")


@tree.command(name="ping", description="レイテンシを計測します")
async def ping(ctx: discord.Interaction):
    text = f'Pong! {round(self.bot.latency*1000)}ms'
    embed = discord.Embed(title='Latency', description=text)
    await ctx.response.send_message(embed=embed)

bot.run(os.getenv("TOKEN"))