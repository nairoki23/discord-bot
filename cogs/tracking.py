import discord
from discord import Embed
from discord.ext import commands,tasks
from func.tracking.model.brand import Brand
from func.tracking.track import get_track, AlreadyTrackingError, FetchError
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


FETCH_ERROR_MESSAGE="荷物情報を取得できませんでした。追跡番号と配送業者を確認してください。"


class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track=get_track()
    # Slash Command の定義


    def make_cb(self,ch_id,name):
        async def cb(pack:Pack|None):
            ch = self.bot.get_channel(ch_id) or await self.bot.fetch_channel(ch_id)
            if pack is None:
                await ch.send(content=name+"の取得に失敗し続けたため、追跡を終了します。")
                return
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
        if not tracking_num:
            await interaction.followup.send(content="追跡番号を読み取れませんでした。")
            return
        data=await self.track.fetch_pack(tracking_num,brand,name)
        if data is None:
            await interaction.followup.send(content=FETCH_ERROR_MESSAGE)
            return
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
        if not tracking_num:
            await interaction.followup.send(content="追跡番号を読み取れませんでした。")
            return
        try:
            _,pack=await self.track.start_track(tracking_num,brand,name,self.make_cb(interaction.channel_id,name))
        except AlreadyTrackingError:
            await interaction.followup.send(content=f"{tracking_num} は既に追跡中です。")
            return
        except FetchError:
            await interaction.followup.send(content=FETCH_ERROR_MESSAGE)
            return
        if pack.state_type==State.arrival:
            await interaction.followup.send(
                content=pack.name+"は既に配達完了しているため、追跡しません。",
                embed=make_embed(pack),
            )
            return
        await interaction.followup.send(
            content=pack.name+"の追跡を開始しました。",
            embed=make_embed(pack),
        )

    @discord.app_commands.command(name="stop-tracking", description="荷物の監視を終了")
    async def stop_tracking(self, interaction: discord.Interaction,tracking_num:str,brand:Brand|None=None):
        brand, tracking_num = self.track.parse_tracking(tracking_num, brand)
        if brand is None or not tracking_num:
            await interaction.response.send_message(content="追跡番号または配送業者が定まりませんでした。")
            return
        if self.track.stop_track(tracking_num,brand):
            await interaction.response.send_message(content=f"{tracking_num} の追跡を終了しました。")
        else:
            await interaction.response.send_message(content=f"{tracking_num} は追跡していません。")


    @discord.app_commands.command(name="tracking-list", description="現状の監視リスト")
    async def tracking_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        text=""
        for b in Brand:
            text+=b.value+"\n"
            for t in self.track.list_tracks():
                if t.brand==b:
                    text+=f"{t.tracking_num} {t.name}\n"
            text+="\n\n"

        await interaction.followup.send(
            content=text,
        )



async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
