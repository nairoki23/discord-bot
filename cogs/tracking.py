import discord
from discord import Embed
from discord.ext import commands,tasks
from func.tracking.model.brand import Brand
from func.tracking.track import get_track
from func.tracking.model.pack import Pack
async def make_send(sender,pack:Pack|None):
    if pack is None:
        await sender("荷物の情報の取得に失敗。")
        return
    print(pack.brand)
    em=Embed(
            title=pack.state_title,
            description=pack.state_summary,
            color={Brand.yamato:0xfccf00,Brand.sagawa:0x3B499F,Brand.jp:0xcc0000}[pack.brand]
        )
    for d in reversed(pack.details):
        em.add_field(name=d.title,value=d.place_name+"\t"+d.time.strftime('%-d日 %-H:%-M'),inline=False)
    await sender(
        content=pack.name+"は"+pack.state_title+"です。",
        embed=em,
    )





class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track=get_track()
    # Slash Command の定義
    @discord.app_commands.command(name="tracking-check", description="宅配状況の一回だけの確認")
    async def tracking_check(self, interaction: discord.Interaction,tracking_num:str,brand:Brand,name:str="名無しの荷物"):
        await interaction.response.defer()
        data=await self.track.fetch_pack(tracking_num,brand,name)
        await make_send(interaction.followup.send,data)

    @discord.app_commands.command(name="start-tracking", description="到着まで荷物を監視")
    async def start_tracking(self, interaction: discord.Interaction,tracking_num:str,brand:Brand,name:str="名無しの荷物"):
        await interaction.response.defer()

async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
