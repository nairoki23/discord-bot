import discord
from discord.ext import commands
from dotenv import dotenv_values
config = dotenv_values(".env")


class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # BAN対象のユーザーIDリスト
        self.ng_list = []
        for s in config.get("USER").split(","):
            self.ng_list.append(int(s))
        print(self.ng_list)
    # 共通のBANチェック処理
    async def scan_and_ban(self, guild: discord.Guild):
        # ボット自身にBAN権限があるかまず確認
        if not guild.me.guild_permissions.ban_members:
            print(f"Bot does not have ban permissions in guild: {guild.name}")
            return
        for user_id in self.ng_list:
            member = guild.get_member(user_id)
            try:
                if member:
                    # サーバー内にいる場合：ロールの上下関係をチェック
                    if guild.me.top_role > member.top_role and member.id != guild.owner_id:
                        await guild.ban(member, reason="")                    
                else:
                    # サーバー内にいない場合：IDを使って直接BAN（事前BAN）
                    await guild.ban(discord.Object(id=user_id), reason="")
            except discord.Forbidden:
                # 権限不足（相手のロールが高い場合など）
                continue
            except discord.HTTPException as e:
                # 既にBANされている場合などはエラーが出るので無視してOK
                if e.code == 10007: # Unknown Member
                    continue

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
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.scan_and_ban(guild)

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.scan_and_ban(guild)

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload):
        if payload.user_id in self.ng_list:
            guild = self.bot.get_guild(payload.guild_id)
            if guild:
                await self.scan_and_ban(guild)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if user.id in self.ng_list:
            await self.scan_and_ban(guild)


async def setup(bot):
    print("Loading Ban Cog...")
    await bot.add_cog(Ban(bot))