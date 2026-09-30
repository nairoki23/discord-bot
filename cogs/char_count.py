import unicodedata

import discord
from discord.ext import commands


def count_chars(text: str) -> dict[str, int]:
    """文字数を各種基準で数える。"""
    no_newline = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "")
    no_space = "".join(c for c in text if not c.isspace())

    alpha = hiragana = katakana = kanji = digit = 0
    for c in no_space:
        code = ord(c)
        if c.isascii() and c.isalpha():
            alpha += 1
        elif c.isdigit():
            digit += 1
        elif 0x3041 <= code <= 0x309F:
            hiragana += 1
        elif 0x30A0 <= code <= 0x30FF or 0x31F0 <= code <= 0x31FF or 0xFF66 <= code <= 0xFF9F:
            # 長音符 ー (U+30FC) はカタカナ扱い
            katakana += 1
        elif "CJK UNIFIED IDEOGRAPH" in unicodedata.name(c, "") or 0x3400 <= code <= 0x4DBF:
            kanji += 1

    return {
        "total": len(text.replace("\r\n", "\n")),
        "no_newline": len(no_newline),
        "no_space": len(no_space),
        "alpha": alpha,
        "hiragana": hiragana,
        "katakana": katakana,
        "kanji": kanji,
        "digit": digit,
    }


class CharCount(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(name="char_count", description="文字数をカウントします")
    @discord.app_commands.describe(text="カウントする文字列（改行は \\n と入力しても可）")
    async def char_count(self, interaction: discord.Interaction, text: str):
        text = text.replace("\\n", "\n")
        r = count_chars(text)
        embed = discord.Embed(title="文字数カウント")
        embed.add_field(name="全体", value=f"{r['total']}", inline=True)
        embed.add_field(name="改行除く", value=f"{r['no_newline']}", inline=True)
        embed.add_field(name="改行・空白除く", value=f"{r['no_space']}", inline=True)
        embed.add_field(name="アルファベット", value=f"{r['alpha']}", inline=True)
        embed.add_field(name="ひらがな", value=f"{r['hiragana']}", inline=True)
        embed.add_field(name="カタカナ", value=f"{r['katakana']}", inline=True)
        embed.add_field(name="漢字", value=f"{r['kanji']}", inline=True)
        embed.add_field(name="数字", value=f"{r['digit']}", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CharCount(bot))
