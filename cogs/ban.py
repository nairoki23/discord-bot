import discord
from discord.ext import commands

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # BAN対象のユーザーIDリスト
        self.ng_list = [123456789012345678, 987654321098765432]

    # 共通のBANチェック処理
    async def scan_and_ban(self, guild: discord.Guild):
        # ボット自身にBAN権限があるか確認
        if not guild.me.guild_permissions.ban_members:
            return

        for member_id in self.ng_list:
            member = guild.get_member(member_id)
            if member:
                # 権限とロール順序をチェックしてBAN可能なら実行
                # 1. ボットの最高ロールが相手より上である必要がある
                # 2. サーバーオーナーはBANできない
                if guild.me.top_role > member.top_role and member.id != guild.owner_id:
                    try:
                        await member.ban(reason="NGリスト該当（権限変更検知による自動BAN）")
                        print(f"【自動BAN成功】{member.name} をサーバー '{guild.name}' から追放しました。")
                    except discord.Forbidden:
                        pass # まだ権限が足りない場合はスルー
                    except Exception as e:
                        print(f"エラー発生: {e}")

    # --- リスナー部分 ---

    # 1. ロールの設定や順序が変わったとき
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self.scan_and_ban(after.guild)

    # 2. サーバー自体の設定が変わったとき
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        await self.scan_and_ban(after)

    # 3. メンバーのロールが変わったとき（NGユーザーが役職を外された瞬間など）
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.id in self.ng_list:
            await self.scan_and_ban(after.guild)

    # 4. 新規参加時（基本）
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.id in self.ng_list:
            await self.scan_and_ban(member.guild)

async def setup(bot):
    await bot.add_cog(Security(bot))