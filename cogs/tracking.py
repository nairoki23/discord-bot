import discord
from discord import Embed
from discord.ext import commands,tasks
from func.tracking.model.brand import Brand
from func.tracking.track import get_track
from func.tracking.model.pack import Pack
from func.tracking.model.state import State


def make_embed(pack:Pack):
    em=Embed(
            title=pack.state_title,
            description=pack.state_summary,
            color={Brand.yamato:0xfccf00,Brand.sagawa:0x3B499F,Brand.jp:0xcc0000}[pack.brand]
        )
    for d in reversed(pack.details):
        em.add_field(name=d.title,value=d.place_name+"\t"+d.time.strftime('%-m/%-d %-H:%M'),inline=False)
    return em





class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track=get_track()
        self.tarck_ch_dict={
            Brand.yamato:{},
            Brand.sagawa:{},
            Brand.jp:{},
        }
    # Slash Command の定義


    async def make_cb(self,sender):
        async def cb(pack:Pack|None):
            if pack is None:
                await sender(conten="荷物取得エラー。")
            em=make_embed(pack)
            if pack.state_type==State.arrival:
                await sender(
                    content=pack.name+"が到着しました。\n追跡を終了します。",
                    embed=em
                )
            else:
                await sender(
                    content=pack.name + "の配達状況が更新されました。",
                    embed=em,
                )
        return cb






    @discord.app_commands.command(name="tracking-check", description="宅配状況の一回だけの確認")
    async def tracking_check(self, interaction: discord.Interaction,tracking_num:str,brand:Brand|None=None,name:str="名無しの荷物"):
        await interaction.response.defer()
        brand, tracking_num = self.track.parse_tracking(tracking_num, brand)
        data=await self.track.fetch_pack(tracking_num,brand,name)
        await interaction.followup.send(
            content=data.name + "は" + data.state_title + "です。",
            embed=make_embed(data),
        )

    @discord.app_commands.command(name="start-tracking", description="到着まで荷物を監視")
    async def start_tracking(self, interaction: discord.Interaction,tracking_num:str,brand:Brand,name:str="名無しの荷物"):
        await interaction.response.defer()
        ch=interaction.response.channel
        brand, tracking_num = self.track.parse_tracking(tracking_num, brand)
        cb_id=await self.track.start_track(tracking_num,brand,name,self.make_cb(ch.send))
        self.tarck_ch_dict[brand][tracking_num]={
            cb_id:ch.id
        }
async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
