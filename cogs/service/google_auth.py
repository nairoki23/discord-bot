import asyncio
import inspect

import discord
from discord import app_commands, ui
from discord.ext import commands

from service.container import get_google_auth
from utils.check_user import interaction_user


class GoogleAuthModal(ui.Modal, title="Google 認証URLの入力"):
    authorization_response = ui.TextInput(
        label="認証後に表示されたページのURL",
        placeholder="https://... のURLをそのまま貼り付けてください",
        style=discord.TextStyle.long,
        min_length=10,
        required=True,
    )

    def __init__(self, auth, on_authenticated=None):
        super().__init__()
        self.auth = auth
        self.on_authenticated = on_authenticated

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success = await asyncio.to_thread(
            self.auth.interactive_creds,
            self.authorization_response.value,
        )
        if not success:
            await interaction.followup.send("認証に失敗しました。URLを確認して再度お試しください。", ephemeral=True)
            return
        if self.on_authenticated is not None:
            result = self.on_authenticated()
            if inspect.isawaitable(result):
                await result
        await interaction.followup.send("Google アカウントの認証に成功しました。", ephemeral=True)


class GoogleAuthView(ui.View):
    def __init__(self, auth_url, auth, on_authenticated=None):
        super().__init__(timeout=900)
        self.auth = auth
        self.on_authenticated = on_authenticated
        self.add_item(ui.Button(label="1. Googleで認証", url=auth_url, style=discord.ButtonStyle.link))

    @ui.button(label="2. 認証後のURLを入力", style=discord.ButtonStyle.primary, emoji="🔑")
    async def open_modal(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(GoogleAuthModal(self.auth, self.on_authenticated))


class Google_Auth(commands.Cog):
    """Shared Google OAuth entry point for Calendar and Gmail."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.auth = get_google_auth()

    @app_commands.command(name="google_auth", description="Google Calendar と Gmail の認証を開始します")
    async def google_auth(self, interaction: discord.Interaction):
        if not await interaction_user(interaction):
            return
        try:
            url = self.auth.create_cred_url()
        except Exception as exc:
            print(f"Google auth URL creation failed: {exc}")
            await interaction.response.send_message(
                "認証の準備に失敗しました。Google OAuth の設定を確認してください。",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "Google Calendar と Gmail の認証です。Google で認証後、遷移先 URL を入力してください。",
            view=GoogleAuthView(url, self.auth),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Google_Auth(bot))
