from dotenv import load_dotenv
import os
import discord
from discord.ext import commands

# .env読み込み
load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}.")
    await bot.tree.sync()
    print("Synced slash commands.")

# Cogを読み込む
async def load_extensions():
    await bot.load_extension("cogs.ping")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv("DISCORD_TOKEN"))

import asyncio
asyncio.run(main())