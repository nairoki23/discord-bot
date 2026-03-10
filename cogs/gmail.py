import discord
from discord.ext import commands, tasks
from discord import app_commands
from func.gmail.auth import GmailAuth
from func.gmail.service import GmailService
from utils.check_user import interaction_user
import utils.gmail_handlers as handlers
from dotenv import dotenv_values
config = dotenv_values(".env")
TARGET_CHANNNEL_ID = int(config.get("NOTIFICATION_CHANNEL_ID"))

HANDLERS =(
    handlers.chibabank.ChibabankHandler,
    handlers.viewcard.ViewHandler,
)


class GmailCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth = GmailAuth()
        self.service=None
        self.process=None

    async def sender(self,content=None,embed=None):
        ch = self.bot.get_channel(TARGET_CHANNNEL_ID)
        if not ch:
            try:
                return await self.bot.fetch_channel(TARGET_CHANNNEL_ID)
            except Exception as e:
                print(f"チャンネル取得失敗: {e}")
                return None
                


    async def setup_hook(self):
        creds=self.auth.get_creds()
        if creds is None:
            print("GmailServiceは立ち上がりませんでした。")
            return
        try:
            self.service = GmailService(self.auth.get_creds())
            handlers={}
            for h in HANDLERS:
                handler=h(self.sender)
                handlers[handler.address]=handler
            self.service.process.setup_handler(handlers) 
            self.service.setup_gmail_watch()
            self.service.start_listening()
        except Exception as e:
            print(f"Error occurred while setting up GmailService: {e}")
            return
        print("GmailServiceが立ち上がったよ！")
    async def setup_gmail_watch(self):
        pass
    
    @app_commands.command(name="gmail_state", description="Gmailの認証状況を確認します")
    async def gmail_state(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        creds=self.auth.get_creds()
        if creds is None:
            text="Gmailは認証されていません。"
        else:
            text="Gmailは認証されています。"
        embed = discord.Embed(title="Gmail Authentication Status", description=text)
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="gmail_auth", description="Gmailの認証を開始します")


async def setup(bot: commands.Bot):
    await bot.add_cog(GmailCog(bot))
