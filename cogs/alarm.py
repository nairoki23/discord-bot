import discord
from discord.ext import commands
from dataclasses import dataclass
from datetime import datetime
from func.alarm.schedule import AlarmSpec, parse_alarm
from service.container import get_timer

# 登録時に表示する今後の通知時刻の数
PREVIEW_COUNT = 3


@dataclass
class AlarmEntry:
    spec: AlarmSpec
    name: str
    user_id: int
    # 通知時に取り直すので ID だけ持つ（スレッドでもよい）
    channel_id: int
    first: datetime
    next_run: datetime
    job_id: str = ""


def discord_time(when: datetime) -> str:
    ts = int(when.timestamp())
    return f"<t:{ts}:F>（<t:{ts}:R>）"


class Alarm(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timer = get_timer()
        self.alarms: dict[str, AlarmEntry] = {}

    @discord.app_commands.command(name="alarm", description="アラーム（例: 12 / 12:50 / /5 12: / /* 12:50 / */*/5 10:*:20）")
    @discord.app_commands.describe(
        time="時刻は H:M:S（: なしは分）、日付は 年/月/日（/ 一つなら 月/日）。* で毎回、空欄は次に来るもの",
        name="アラームの名前（通知・一覧・取り消しで表示）",
    )
    async def alarm(self, interaction: discord.Interaction, time: str, name: str = "アラーム"):
        try:
            spec = parse_alarm(time)
        except ValueError as e:
            await interaction.response.send_message(f"日時を解釈できませんでした: {e}", ephemeral=True)
            return

        first = spec.first(datetime.now())
        if first is None:
            await interaction.response.send_message("該当する日時がありません。", ephemeral=True)
            return

        entry = AlarmEntry(
            spec=spec,
            name=name,
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            first=first,
            next_run=first,
        )
        entry.job_id = self.timer.schedule(first, cb=self._callback(entry))
        self.alarms[entry.job_id] = entry

        text = f"{discord_time(first)} に「{entry.name}」を通知します。"
        if spec.repeats:
            upcoming = [first]
            while len(upcoming) < PREVIEW_COUNT:
                nxt = spec.next_after(upcoming[-1], first)
                if nxt is None:
                    break
                upcoming.append(nxt)
            text += "\n繰り返し: " + " → ".join(discord_time(t) for t in upcoming)
            if len(upcoming) == PREVIEW_COUNT:
                text += " → …"
        await interaction.response.send_message(text)

    def _callback(self, entry: AlarmEntry):
        async def cb():
            try:
                channel = self.bot.get_channel(entry.channel_id) or await self.bot.fetch_channel(entry.channel_id)
                await channel.send(
                    f"<@{entry.user_id}> {entry.name}の時間になりました。",
                    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
                )
            except Exception as e:
                # 送れなくても繰り返しは続ける
                print(f"[alarm {entry.job_id}] 通知に失敗: {e}")

            # sleep が早く起きても同じ時刻で二重に鳴らないよう、予定時刻と現在の遅い方から次を探す
            nxt = entry.spec.next_after(max(entry.next_run, datetime.now()), entry.first)
            if nxt is None:
                self.alarms.pop(entry.job_id, None)
                return None
            entry.next_run = nxt
            return nxt
        return cb

    def _own_alarms(self, user_id: int) -> list[AlarmEntry]:
        return sorted(
            (e for e in self.alarms.values() if e.user_id == user_id),
            key=lambda e: e.next_run,
        )

    @discord.app_commands.command(name="alarm_list", description="自分のアラーム一覧")
    async def alarm_list(self, interaction: discord.Interaction):
        entries = self._own_alarms(interaction.user.id)
        if not entries:
            await interaction.response.send_message("アラームはありません。", ephemeral=True)
            return
        lines = [
            f"- {e.name}（<#{e.channel_id}>）次回 {discord_time(e.next_run)}{' 🔁' if e.spec.repeats else ''}"
            for e in entries
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.app_commands.command(name="alarm_cancel", description="アラームを取り消す")
    @discord.app_commands.describe(alarm="取り消すアラーム")
    async def alarm_cancel(self, interaction: discord.Interaction, alarm: str):
        entry = self.alarms.get(alarm)
        if entry is None or entry.user_id != interaction.user.id:
            await interaction.response.send_message("アラームが見つかりません。", ephemeral=True)
            return
        self.timer.cancel(alarm)
        self.alarms.pop(alarm, None)
        await interaction.response.send_message(f"「{entry.name}」を取り消しました。", ephemeral=True)

    @alarm_cancel.autocomplete("alarm")
    async def alarm_cancel_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        for e in self._own_alarms(interaction.user.id):
            label = f"{e.name} {e.next_run:%Y/%m/%d %H:%M:%S}{' 🔁' if e.spec.repeats else ''}"
            if current in label:
                choices.append(discord.app_commands.Choice(name=label[:100], value=e.job_id))
        return choices[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(Alarm(bot))
