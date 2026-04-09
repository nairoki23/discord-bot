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
        self.track_ch_dict={
            Brand.yamato:{},
            Brand.sagawa:{},
            Brand.jp:{},
        }
    # Slash Command の定義


    def make_cb(self,ch_id):
        async def cb(pack:Pack|None):
            ch = self.bot.get_channel(ch_id)
            if pack is None:
                await ch.send(conten="荷物取得エラー。")
            em=make_embed(pack)
            if pack.state_type==State.arrival:
                await ch.send(
                    content=pack.name+"が到着しました。\n追跡を終了します。",
                    embed=em
                )
            else:
                await ch.send(
                    content=pack.name + "の配達状況が更新されました。",
                    embed=em,
                )
        return cb


    @discord.app_commands.command(name="tracking-check", description="宅配状況の一回だけの確認")
    async def tracking_check(self, interaction: discord.Interaction,tracking_num:str,brand:Brand|None=None,name:str="名無しの荷物"):
        await interaction.response.defer()
        brand, tracking_num = self.track.parse_tracking(tracking_num, brand)
        if brand is None:
            await interaction.followup.send(
                content="配送業者が定まりませんでした。",
            )
            return
        data=await self.track.fetch_pack(tracking_num,brand,name)
        await interaction.followup.send(
            content=data.name + "は" + data.state_title + "です。",
            embed=make_embed(data),
        )

    @discord.app_commands.command(name="start-tracking", description="到着まで荷物を監視")
    async def start_tracking(self, interaction: discord.Interaction,tracking_num:str,brand:Brand|None=None,name:str="名無しの荷物"):
        await interaction.response.defer()
        brand, tracking_num = self.track.parse_tracking(tracking_num, brand)
        if brand is None:
            await interaction.followup.send(
                content="配送業者が定まりませんでした。",
            )
            return
        ch=interaction.channel
        try:
            cb_id=await self.track.start_track(tracking_num,brand,name,self.make_cb(ch.id))
            self.track_ch_dict[brand][tracking_num]={
                cb_id:ch.id
            }
        except Exception as e:
            print(e)
        await interaction.followup.send(
            content="tracking開始"
        )




    @discord.app_commands.command(name="tracking-list", description="現状の監視リスト")
    async def tracking_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        text=""
        for b in self.track_ch_dict:
            text+=str(b)+"\n"
            for code in self.track_ch_dict[b]:
                text+=str(code)+"\n"
            text+="\n\n"

        await interaction.followup.send(
            content=text,
        )



async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
