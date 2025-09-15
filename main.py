from dotenv import dotenv_values
import discord
from discord.ext import commands

# .env読み込み
config = dotenv_values(".env")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Cogを読み込む
async def load_extensions():
    await bot.load_extension("cogs.ping")
    await bot.load_extension("cogs.data_usage")
    await bot.load_extension("cogs.timer")
    await bot.load_extension("cogs.spending")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}.")
    await load_extensions()
    await bot.tree.sync()
    guild = discord.Object(id=config.get("TEST_GUILD"))
    await bot.tree.sync(guild=guild)
    print("Synced slash commands.")

async def main():
    async with bot:
        await bot.start(config.get("DISCORD_TOKEN"))

import asyncio
asyncio.run(main())