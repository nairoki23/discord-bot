from dotenv import dotenv_values
import discord
from discord.ext import commands

# .env読み込み
config = dotenv_values(".env")
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    # ボット起動時に一度だけ呼ばれる準備用関数
    async def setup_hook(self):
        # ここでCogを読み込む
        extensions = [
            "cogs.ping",
            "cogs.data_usage",
            "cogs.timer",
            "cogs.spending",
            "cogs.ban",
            "cogs.gmail",
            "cogs.class_schedule"
        ]
        for ext in extensions:
            await self.load_extension(ext)
        
        # スラッシュコマンドの同期
        guild = discord.Object(id=config.get("TEST_GUILD"))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Cogs loaded and Tree synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}.")

async def main():
    async with bot:
        await bot.start(config.get("DISCORD_TOKEN"))

import asyncio
asyncio.run(main())