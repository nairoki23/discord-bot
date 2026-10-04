import discord
from discord import Embed
from discord.ext import commands,tasks
from func.tracking.model.brand import Brand
from func.tracking.track import get_track, AlreadyTrackingError, NotOwnerError
from func.tracking.model.pack import Pack
from func.tracking.model.state import State
from datetime import datetime


BRAND_NAME={Brand.yamato:"ヤマト運輸",Brand.sagawa:"佐川急便",Brand.jp:"日本郵便"}
# Discord の Embed の上限
MAX_FIELDS=25
MAX_FIELD_NAME=256
MAX_FIELD_VALUE=1024
MAX_DESCRIPTION=4096


def truncate(text:str,limit:int)->str:
    return text if len(text)<=limit else text[:limit-1]+"…"


def format_est_date(est)->str:
    # 時刻付きは時間帯の終わりの時刻を持っている
    if isinstance(est,datetime):
        return est.strftime('%-m/%-d %-H:%Mまで')
    return est.strftime('%-m/%-d')


def make_embed(pack:Pack):
    description="\n".join(t.strip() for t in (pack.state_summary,pack.state_note) if t and t.strip())
    em=Embed(
            title=truncate(pack.state_title,256),
            description=truncate(description,MAX_DESCRIPTION),
            color={Brand.yamato:0xfccf00,Brand.sagawa:0x3B499F,Brand.jp:0xcc0000}[pack.brand]
        )
    if pack.est_date:
        em.add_field(name="お届け予定",value=format_est_date(pack.est_date),inline=True)
    if pack.type and pack.type.strip():
        em.add_field(name="品名・種別",value=truncate(pack.type.strip(),MAX_FIELD_VALUE),inline=True)

    details=list(reversed(pack.details))
    room=MAX_FIELDS-len(em.fields)
    if len(details)>room:
        # 新しい履歴を優先し、残りは件数だけ出す
        shown,hidden=details[:room-1],len(details)-(room-1)
    else:
        shown,hidden=details,0
    for d in shown:
        value=" ".join(t for t in (d.place_name.strip(),d.time.strftime('%-m/%-d %-H:%M')) if t)
        em.add_field(name=truncate(d.title.strip() or "-",MAX_FIELD_NAME),value=truncate(value,MAX_FIELD_VALUE),inline=False)
    if hidden:
        em.add_field(name="それ以前の履歴",value=f"ほか {hidden} 件",inline=False)
    em.set_footer(text=f"{BRAND_NAME[pack.brand]} {pack.num}")
    return em


def format_tracking_list(trackings)->str:
    if not trackings:
        return "追跡中の荷物はありません。"
    blocks=[]
    for b in Brand:
        lines=[]
        for t in trackings:
            if t.brand!=b:
                continue
            state=t.latest_pack.state_title if t.latest_pack else "未取得"
            lines.append(f"・{t.name}（{t.tracking_num}）: {state}")
        if lines:
            blocks.append(f"**{BRAND_NAME[b]}**\n"+"\n".join(lines))
    # メッセージ本文の上限は 2000 文字
    return truncate("\n\n".join(blocks),2000)


FETCH_ERROR_MESSAGE="荷物情報を取得できませんでした。追跡番号と配送業者を確認してください。"


class Tracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.track=get_track()
    # Slash Command の定義


    def make_cb(self,ch_id,name,user_id):
        mention=f"<@{user_id}> "
        async def cb(pack:Pack|None):
            ch = self.bot.get_channel(ch_id) or await self.bot.fetch_channel(ch_id)
            if pack is None:
                await ch.send(content=mention+name+"の取得に失敗し続けたため、追跡を終了します。")
                return
            em=make_embed(pack)
            if pack.state_type==State.arrival:
                await ch.send(
                    content=mention+pack.name+"が到着しました。\n追跡を終了します。",
                    embed=em
                )
            else:
                await ch.send(
                    content=mention+pack.name + "の配達状況が更新されました。",
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
            _,pack=await self.track.start_track(
                tracking_num,brand,name,
                self.make_cb(interaction.channel_id,name,interaction.user.id),
                owner_id=interaction.user.id,
            )
        except AlreadyTrackingError:
            await interaction.followup.send(content=f"{tracking_num} は既に追跡中です。")
            return
        if pack is None:
            await interaction.followup.send(
                content=f"{name}（{tracking_num}）の追跡を開始しました。\n"
                        "現在は荷物情報を取得できませんでした（伝票番号が未登録の可能性があります）。"
                        "取得できるまで確認を続け、状況が更新されたらお知らせします。",
            )
            return
        if pack.state_type==State.arrival:
            await interaction.followup.send(
                content=pack.name+"は既に配達完了しているため、追跡しません。",
                embed=make_embed(pack),
            )
            return
        await interaction.followup.send(
            content=pack.name+"の追跡を開始しました。\n配達状況が更新されたらお知らせします。",
            embed=make_embed(pack),
        )

    @discord.app_commands.command(name="stop-tracking", description="荷物の監視を終了")
    async def stop_tracking(self, interaction: discord.Interaction,tracking_num:str,brand:Brand|None=None):
        brand, tracking_num = self.track.parse_tracking(tracking_num, brand)
        if brand is None or not tracking_num:
            await interaction.response.send_message(content="追跡番号または配送業者が定まりませんでした。")
            return
        try:
            stopped=self.track.stop_track(tracking_num,brand,requester_id=interaction.user.id)
        except NotOwnerError:
            await interaction.response.send_message(content="追跡を依頼した本人しか停止できません。",ephemeral=True)
            return
        if stopped:
            await interaction.response.send_message(content=f"{tracking_num} の追跡を終了しました。")
        else:
            await interaction.response.send_message(content=f"{tracking_num} は追跡していません。")


    @discord.app_commands.command(name="tracking-list", description="現状の監視リスト")
    async def tracking_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(
            content=format_tracking_list(self.track.list_tracks()),
        )



async def setup(bot: commands.Bot):
    await bot.add_cog(Tracking(bot))
