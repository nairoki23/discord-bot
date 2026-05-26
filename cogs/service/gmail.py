from discord.ext import commands, tasks
from discord import app_commands
from service.container import get_gmail_service,get_gmail_auth
from utils.check_user import interaction_user
import utils.gmail_handlers as handlers
from dotenv import dotenv_values
config = dotenv_values(".env")
TARGET_CHANNNEL_ID = int(config.get("NOTIFICATION_CHANNEL_ID"))

HANDLERS =(
    handlers.chibabank.ChibabankHandler,
    handlers.viewcard.ViewHandler,
    handlers.my.MyHandler
)

import discord
from discord import ui

# --- 1. コード入力用のポップアップ（Modal） ---
class GmailAuthModal(ui.Modal, title='Gmail 認証コードの入力'):
    # 入力フィールド（長いコードが入るように設定）
    auth_code = ui.TextInput(
        label='Googleから発行されたコード',
        placeholder='ここに貼り付けてください...',
        style=discord.TextStyle.long,
        min_length=10,
        required=True
    )

    def __init__(self, auth,setup):
        super().__init__()
        self.auth_handler = auth # 認証ロジックを持つクラス
        self.setup=setup
    async def on_submit(self, interaction: discord.Interaction):
        # 送信ボタンが押された時の処理
        code = self.auth_code.value
        
        # 実際に応答を返す前に「考え中...」状態にする（認証に時間がかかる場合があるため）
        await interaction.response.defer(ephemeral=True)
        
        # 認証実行（自作の認証完了メソッドを呼ぶ）
        success = self.auth_handler.interactive_creds(code)
        
        if success:
            await interaction.followup.send("認証に成功しました",ephemeral=True)
            await self.setup()
            await interaction.followup.send("Gmailサービスを開始します", ephemeral=True)
        else:
            await interaction.followup.send(" 認証に失敗しました。", ephemeral=True)
# --- 2. ボタンを表示するView ---
class GmailAuthView(ui.View):
    def __init__(self, auth_url, auth_handler,setup):
        super().__init__(timeout=None) # タイムアウトなし
        self.auth_handler = auth_handler
        self.setup=setup
        # リンクボタン（Googleのページへ飛ばす）を追加
        self.add_item(ui.Button(
            label='1. Googleで認証（外部サイト）',
            url=auth_url,
            style=discord.ButtonStyle.link
        ))

    @ui.button(label='2. コードを入力する', style=discord.ButtonStyle.primary, emoji="🔑")
    async def open_modal(self, interaction: discord.Interaction, button: ui.Button):
        # モーダルを表示する
        await interaction.response.send_modal(GmailAuthModal(self.auth_handler,self.setup))



class GmailCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth = get_gmail_auth()
        self.service=None
        self.process=None
        self.tracked_addresses=[]  # 動的追跡中のアドレス一覧
        self.setup_gmail_watch.start()
    async def sender(self):
        ch = self.bot.get_channel(TARGET_CHANNNEL_ID)
        if not ch:
            try:
                ch=await self.bot.fetch_channel(TARGET_CHANNNEL_ID)
            except Exception as e:
                print(f"チャンネル取得失敗: {e}")
                return None
        return ch.send
        
    async def cog_load(self):#関数名的に起動時に一回呼ばれる
        creds=self.auth.get_creds()
        if creds is None:
            print("GmailServiceは立ち上がりませんでした。")
            return False
        try:
            self.service = get_gmail_service(self.auth.get_creds)
            for h in HANDLERS:
                self.service.set_handler(h(await self.sender()))
            self.service.setup_gmail_watch()
            self.service.start_listening()

        except Exception as e:
            print(f"Error occurred while setting up GmailService: {e}")
            return False
        print("GmailServiceが立ち上がったよ！")
        return True
    
    @tasks.loop(hours=24.0)
    async def setup_gmail_watch(self):
        if self.auth.get_creds() is not None:
            self.service.setup_gmail_watch()
    
    @app_commands.command(name="gmail_state", description="Gmailのserviceの状況を確認します")
    async def gmail_state(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        creds=self.auth.get_creds()
        if creds is None:
            text="Gmailは認証されていません。"
        else:
            text="Gmailは認証されています。"
        embeds=[
                discord.Embed(title="認証状況", description=text),
                ]
        if self.service is not None:
            embeds.append(discord.Embed(title="Handler数",description=str(self.service.state_handler())))
        # 動的追跡中のアドレス一覧を表示
        if self.tracked_addresses:
            addr_list = "\n".join(f"・ {addr}" for addr in self.tracked_addresses)
            embeds.append(discord.Embed(title="追跡中メールアドレス", description=addr_list, color=discord.Color.blue()))
        else:
            embeds.append(discord.Embed(title="追跡中メールアドレス", description="なし", color=discord.Color.light_grey()))
        await interaction.response.send_message(
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

    @app_commands.command(name="gmail_auth", description="Gmailの認証を開始します")
    async def gmail_auth(self, interaction: discord.Interaction):
        try:
            if not await interaction_user(interaction):
                return
            await interaction.response.send_message({True:"",False:"既存の認証セッションは破棄しました。\n"}[self.auth.flow is None]+"Gmail認証です。画面の指示に従って認証したあと、移動したページのURLを貼ってください。",
                view= GmailAuthView(self.auth.create_cred_url(), self.auth,self.cog_load),
                ephemeral=True) # 自分にしか見えないようにする
        except Exception as e:
            print(f"Callback Error: {e}")

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
