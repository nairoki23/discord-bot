from dotenv import dotenv_values
import discord
from discord.ext import commands
from pathlib import Path
from service.container  import set_loop


# .env読み込み
config = dotenv_values(".env")
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    # ボット起動時に一度だけ呼ばれる準備用関数
    async def setup_hook(self):
        base = Path("./cogs")

        for path in base.rglob("*.py"):
            if path.name.startswith("_"):
                continue

            # cogs.xxx.yyy 形式に変換
            module = ".".join(path.with_suffix("").parts)

            try:
                await self.load_extension(module)
                print(f"Loaded: {module}")
            except Exception as e:
                print(f"Failed: {module} -> {e}")
        # スラッシュコマンドの同期
        guild = discord.Object(id=config.get("TEST_GUILD"))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)#TestGuildにすぐ反映
        await self.tree.sync()#全Guildにいずれ浸透
        print("Cogs loaded and Tree synced.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}.")

async def main():
    async with bot:
        set_loop(bot.loop)#Service点火
        await bot.start(config.get("DISCORD_TOKEN"))

import asyncio
asyncio.run(main())