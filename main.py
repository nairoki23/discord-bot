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

    async def load_cogs(self, base: Path):
        for path in base.rglob("*.py"):
            if path.name.startswith("_"):
                continue

            # cogs.xxx.yyy / private.cogs.xxx 形式に変換
            module = ".".join(path.with_suffix("").parts)

            try:
                await self.load_extension(module)
                print(f"Loaded: {module}")
            except Exception as e:
                print(f"Failed: {module} -> {e}")

    # ボット起動時に一度だけ呼ばれる準備用関数
    async def setup_hook(self):
        guild_id = config.get("MAIN_GUILD")
        main_guild = discord.Object(id=int(guild_id)) if guild_id else None

        await self.load_cogs(Path("cogs"))
        public_ids = {id(cmd) for cmd in self.tree.get_commands()}
        # private submodule の cogs（無ければ何もロードしない）
        await self.load_cogs(Path("private/cogs"))

        # private のコマンドはグローバルから外し、MAIN_GUILD のみに登録する
        for cmd in self.tree.get_commands():
            if id(cmd) in public_ids:
                continue
            self.tree.remove_command(cmd.name, type=getattr(cmd, "type", discord.AppCommandType.chat_input))
            if main_guild:
                self.tree.add_command(cmd, guild=main_guild)

        # スラッシュコマンドの同期
        await self.tree.sync()#public: 全Guildにいずれ浸透
        if main_guild:
            await self.tree.sync(guild=main_guild)#private: MAIN_GUILDにすぐ反映
        else:
            print("MAIN_GUILD が未設定のため、private のコマンドは登録しません")
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
