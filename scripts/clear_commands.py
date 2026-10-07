"""Discord に登録済みのスラッシュコマンドを全削除する（開発終了時用）。

Bot（main.py）は起動せず、HTTP API だけで削除する。リポジトリ直下で実行:

    python scripts/clear_commands.py       # 削除対象を表示して確認してから削除
    python scripts/clear_commands.py -y    # 確認なしで削除

対象はグローバルコマンドと、Bot が参加している全ギルドのギルドコマンド。
main.py を起動すると、その時点の cogs のコマンドが再登録される。
"""
import argparse
import asyncio

import discord
from discord import app_commands
from dotenv import dotenv_values

# (ギルド。グローバルなら None, 登録済みコマンド)
Target = tuple[discord.abc.Snowflake | None, list[app_commands.AppCommand]]


async def collect_targets(tree: app_commands.CommandTree, guilds) -> list[Target]:
    """コマンドが 1 つ以上登録されている場所（グローバル / ギルド）を集める。"""
    targets = []
    for guild in [None, *guilds]:
        commands = await tree.fetch_commands(guild=guild)
        if commands:
            targets.append((guild, commands))
    return targets


async def clear_targets(tree: app_commands.CommandTree, targets: list[Target]):
    """空のコマンド一覧を同期して、登録済みコマンドを消す。"""
    for guild, _ in targets:
        tree.clear_commands(guild=guild)
        await tree.sync(guild=guild)


def describe(guild) -> str:
    return "グローバル" if guild is None else f"ギルド {guild.name} ({guild.id})"


async def main(yes: bool):
    config = dotenv_values(".env")
    client = discord.Client(intents=discord.Intents.none())
    tree = app_commands.CommandTree(client)

    async with client:
        await client.login(config.get("DISCORD_TOKEN"))
        guilds = [g async for g in client.fetch_guilds(limit=None)]
        targets = await collect_targets(tree, guilds)

        if not targets:
            print("登録済みのコマンドはありません")
            return

        for guild, commands in targets:
            names = ", ".join(f"/{c.name}" for c in commands)
            print(f"{describe(guild)}: {names}")

        if not yes and input("これらのコマンドをすべて削除しますか？ [y/N]: ").strip().lower() != "y":
            print("中止しました")
            return

        await clear_targets(tree, targets)
        print("削除しました（グローバルコマンドはクライアントへの反映に時間がかかることがあります）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="登録済みのスラッシュコマンドを全削除する")
    parser.add_argument("-y", "--yes", action="store_true", help="確認せずに削除する")
    asyncio.run(main(parser.parse_args().yes))
