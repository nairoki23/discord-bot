import asyncio
import traceback

import discord
from dotenv import dotenv_values
from discord.ext import commands

from func.ymobile.ymobile import Ymobile, YmobileMaintenance
from utils.check_user import interaction_user

# .env読み込み
config = dotenv_values(".env")


def build_embed(data) -> discord.Embed:
    text = "ご利用状況をご案内します :bulb:\n\nデータ量残量：" + str(data.remaining/1000) + "GB/" + str(data.all_usable/1000) + "GB"
    embed = discord.Embed(title="データ量", description=text)
    embed.add_field(name="今月の使用量", value=str(data.used/1000) + "GB", inline=True)
    embed.add_field(name="今月のくりこし分", value=str(data.kurikoshi/1000) + "GB", inline=True)
    embed.set_footer(text=data.mon + "\t" + data.tel)
    return embed


class DataUsage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.y = Ymobile(config.get("PHONE_NUMBER"), config.get("YMOBILE_PASSWORD"))

    # Slash Command の定義
    @discord.app_commands.command(name="usage", description="スマホの残りデータ容量確認")
    async def usage(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        await interaction.response.defer()
        try:
            # requests は同期なのでイベントループを止めないよう別スレッドで実行する
            data = await asyncio.to_thread(self.y.get)
            embed = build_embed(data)
        except YmobileMaintenance:
            await interaction.followup.send("My Y!mobile がメンテナンス中のため取得できません :construction:\n時間をおいて試してください")
            return
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"データ残量を取得できませんでした :warning:\n`{type(e).__name__}: {e}`")
            return
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DataUsage(bot))
