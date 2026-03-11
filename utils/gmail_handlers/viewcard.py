import base64
from .base import BaseHandler
import re
from datetime import datetime
from discord import Embed,Color
class ViewHandler(BaseHandler):
    def __init__(self, sender):
        # 親クラスの初期化（self.bot = bot が実行される）
        super().__init__(sender)
        self.address="viewcard@mail.viewsnet.jp"

    async def handle(self, details):
        text = base64.urlsafe_b64decode(details["payload"]["parts"][0]["body"]["data"]).decode("utf-8")
        if details["subject"]=="◆速報版◆ビューカードご利用情報のお知らせ（本人会員利用）":
            text = base64.urlsafe_b64decode(details["payload"]["parts"][0]["body"]["data"]).decode("utf-8")
            patterns = {
                "card": r"ご利用カード\s+：(.+)",
                "user": r"・ 利用者\s+：(.+)",
                "date": r"・ 利用日時\s+：(.+)",
                "type": r"・ 利用種別\s+：(.+)",
                "amount": r"・ 利用金額\s+：([\d,]+)円",
                "shop": r"・ 利用加盟店\s+：(.+)"
            }
            data={}
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                data[key] = match.group(1).strip() if match else "不明"

            embed = Embed(
                title=data['card']+"が使用されました",
                color=Color.green(),
                timestamp=datetime.strptime(data["date"], "%Y/%m/%d %H:%M:%S"),
            )
            
            # メイン情報の追加
            embed.add_field(name="利用金額", value=f"**{data['amount']} 円**", inline=False)
            embed.add_field(name="利用加盟店", value=data['shop'], inline=True)
            embed.add_field(name="種別", value=data['type'], inline=True)
            embed.set_footer(text="ビューカード")

            await self.sender(
                content=data['shop']+"で"+data['amount']+"円利用しました。",
                embed=embed
            )
        elif details["subject"]=="－確報版－ ビューカードご利用情報のお知らせ（本人会員利用）":
            # この形式専用のパターン（利用日時→利用日、利用種別を削除）
            patterns = {
                "card": r"ご利用カード\s+：(.+)",
                "user": r"・ 利用者\s+：(.+)",
                "date": r"・ 利用日\s+：(.+)",
                "amount": r"・ 利用金額\s+：([\d,]+)円",
                "shop": r"・ 利用加盟店\s+：(.+)"
            }
            
            data = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                data[key] = match.group(1).strip() if match else "不明"

            # 時刻がないので、日付としてパースしてその日の 00:00:00 とする
            try:
                dt_obj = datetime.strptime(data["date"], "%Y/%m/%d")
            except:
                dt_obj = datetime.now() # パース失敗時のフォールバック

            embed = Embed(
                title=data['card'] + "が使用されました",
                color=Color.green(),
                timestamp=dt_obj,
            )
            
            # フィールド追加（利用種別がないのでシンプルに）
            embed.add_field(name="利用金額", value=f"**{data['amount']} 円**", inline=False)
            embed.add_field(name="利用加盟店", value=data['shop'], inline=True)
            embed.add_field(name="利用者", value=data['user'], inline=True)
            embed.set_footer(text="ビューカード - 利用通知")

            await self.sender(
                content=f"{data['shop']}での{data['amount']}円の利用が確定しました。",
                embed=embed
            )