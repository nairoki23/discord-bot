import asyncio

from discord.ext import commands, tasks
from discord import app_commands
import discord

from service.container import get_gmail_service, get_google_auth
from utils.check_user import interaction_user
import utils.gmail_handlers as handlers
from utils.channels import get_channel_id
from dotenv import dotenv_values
config = dotenv_values(".env")
TARGET_CHANNNEL_ID = get_channel_id("notification_channel_id")
CREDIT_CARD_THREAD_ID = get_channel_id("credit_card_thread_id")
ENV_TRACK_ADDRESSES = [a.strip() for a in config.get("GMAIL_TRACK_ADDRESSES", "").split(",") if a.strip()]

HANDLERS = (
    handlers.my.MyHandler,
    handlers.paypay_insurance.PayPayInsuranceHandler,
    handlers.rakuten_ticket.RakutenTicketHandler,
    handlers.eplus.EplusHandler,
    handlers.paypay_fleamarket.PayPayFleamarketHandler,
)

class GmailCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth = get_google_auth()
        self.service=None
        self.process=None
        self.tracked_addresses=[]  # 動的追跡中のアドレス一覧
        self.setup_gmail_watch.start()
    async def sender(self, channel_id=TARGET_CHANNNEL_ID):
        ch = self.bot.get_channel(channel_id)
        if not ch:
            try:
                ch=await self.bot.fetch_channel(channel_id)
            except Exception as e:
                print(f"チャンネル取得失敗: {e}")
                return None
        return ch.send
        
    async def _load_env_tracked_addresses(self):
        """.envのGMAIL_TRACK_ADDRESSESから追跡対象を自動登録する"""
        for address in ENV_TRACK_ADDRESSES:
            if address in self.tracked_addresses:
                print(f"[Gmail] {address} は既に追跡中のためスキップ")
                continue
            handler = handlers.generic.GenericHandler(await self.sender(), address)
            result = self.service.set_handler(handler)
            if result:
                self.tracked_addresses.append(address)
                print(f"[Gmail] .envから追跡対象を自動登録: {address}")
            else:
                print(f"[Gmail] .envからの自動登録に失敗: {address}")

    async def cog_load(self):#関数名的に起動時に一回呼ばれる
        creds=self.auth.get_creds()
        if creds is None:
            print("GmailServiceは立ち上がりませんでした。")
            return False
        try:
            self.service = get_gmail_service(self.auth.get_creds)
            sender = await self.sender()
            for handler_class in HANDLERS:
                self.service.set_handler(handler_class(sender))
            credit_card_sender = await self.sender(
                CREDIT_CARD_THREAD_ID or TARGET_CHANNNEL_ID
            )
            for address in handlers.credit_card.CreditCardHandler.ADDRESSES:
                self.service.set_handler(
                    handlers.credit_card.CreditCardHandler(
                        credit_card_sender, address, self.service.mark_as_read
                    )
                )
            self.service.setup_gmail_watch()
            self.service.start_listening()

        except Exception as e:
            print(f"Error occurred while setting up GmailService: {e}")
            return False
        print("GmailServiceが立ち上がったよ！")
        # .envの追跡対象を自動登録
        await self._load_env_tracked_addresses()
        return True
    
    @tasks.loop(hours=24.0)
    async def setup_gmail_watch(self):
        if self.auth.get_creds() is not None:
            self.service.setup_gmail_watch()
    
    @app_commands.command(name="gmail_state", description="Google連携の認証状況とHandler登録状況を確認します")
    async def gmail_state(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        await interaction.response.defer()

        creds = self.auth.get_creds()
        if creds is None:
            auth_text = "未認証です。`/google_auth` を実行してください。"
        elif self.service is None:
            auth_text = "認証情報はありますが、Gmailサービスが起動していません。`/gmail_start` を実行してください。"
        else:
            # ローカルのcredsが有効でも、Google側で失効している場合があるため実際にAPIへ接続して確認する
            connected = await asyncio.to_thread(self.service.verify_connection)
            auth_text = (
                "認証済み（Gmail APIへの接続を確認しました）"
                if connected
                else "トークンはありますが、Gmail APIへの接続に失敗しました。再認証が必要な可能性があります。"
            )
        embeds = [discord.Embed(title="認証状況", description=auth_text)]

        if self.service is not None:
            addresses = self.service.handler_addresses()
            if addresses:
                lines = "\n".join(
                    f"・ {address or '(アドレス未指定・素通し用)'} — {handler_type}"
                    for address, handler_type in addresses
                )
                embeds.append(discord.Embed(title=f"登録Handler（{len(addresses)}件）", description=lines, color=discord.Color.blue()))
            else:
                embeds.append(discord.Embed(title="登録Handler", description="なし", color=discord.Color.light_grey()))

        await interaction.followup.send(
            content="Gmailサービスの状態",
            embeds=embeds
            )


    @app_commands.command(name="gmail_start", description="Gmailサービスの開始")
    async def gmail_start(self,interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        await interaction.response.defer()
        st=await self.cog_load()
        await interaction.followup.send(content={True:"Gmailサービスを起動しました",False:"Gmailサービスの起動に失敗しました"}[st])

    @app_commands.command(name="gmail_track", description="メールアドレスを追跡対象に追加します")
    @app_commands.describe(address="追跡するメールアドレス")
    async def gmail_track(self, interaction: discord.Interaction, address: str):
        if not await interaction_user(interaction):
            return
        if self.service is None:
            await interaction.response.send_message("Gmailサービスが起動していません。先に `/gmail_start` を実行してください。", ephemeral=True)
            return
        # 簡易バリデーション
        if "@" not in address or "." not in address:
            await interaction.response.send_message("有効なメールアドレスを入力してください。", ephemeral=True)
            return
        if address in self.tracked_addresses:
            await interaction.response.send_message(f"`{address}` は既に追跡中です。", ephemeral=True)
            return
        handler = handlers.generic.GenericHandler(await self.sender(), address)
        result = self.service.set_handler(handler)
        if result:
            self.tracked_addresses.append(address)
            await interaction.response.send_message(f"✅ `{address}` を追跡対象に追加しました。", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ `{address}` の登録に失敗しました（既に別のハンドラーが登録されている可能性があります）。", ephemeral=True)

    @app_commands.command(name="gmail_untrack", description="メールアドレスの追跡を解除します")
    @app_commands.describe(address="追跡を解除するメールアドレス")
    async def gmail_untrack(self, interaction: discord.Interaction, address: str):
        if not await interaction_user(interaction):
            return
        if address not in self.tracked_addresses:
            await interaction.response.send_message(f"`{address}` は追跡対象に含まれていません。", ephemeral=True)
            return
        try:
            self.service.del_handler(address)
            self.tracked_addresses.remove(address)
            await interaction.response.send_message(f"✅ `{address}` の追跡を解除しました。", ephemeral=True)
        except Exception as e:
            print(f"Untrack error: {e}")
            await interaction.response.send_message(f"❌ 解除に失敗しました。", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GmailCog(bot))
