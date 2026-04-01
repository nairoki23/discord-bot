from service.gmail.HandlerBase import BaseHandler
import re
import base64
from discord import Embed
from datetime import datetime
TRACE_STORE = {
    "4015852TOMIBUNKIYOMIDAITE": "富分清見台店",
    "SUICA GOOGLEPAY": "Suica Googlepay",
    "UOKUNI FOOD SERVICES NATI": "魚国総本社木更津高専売店",
    "SEVEN-ELEVEN": "セブンイレブン",
    "POPLAR GROUP": "ポプラ",
    "HIDAKAYA SOGAHIGASHIGUCHI": "日高屋蘇我東店",
    "PAYPAL *DISCORD": "Discord_paypal",
    "DAILY YAMAZAKI": "デイリーヤマザキ",
    "LAWSON": "ローソン",
    "ITO YOKADO": "イトーヨーカドー",
    "STARBUCKS COFFEE JAPAN": "スターバックスコーヒージャパン",
    "JR EAST": "JR東日本",
    "BELC CHIBAHAMANO TEN": "ベルク千葉浜野店",
    "DONQUIJOTE KISARAZU": "ドン・キホーテ木更津店",
    "MATUMOTOKIYOSI": "マツモトキヨシ",
    "MCDONALDS MOBILE ORDER": "マクドナルド",
    "MCDONALD S": "マック",
    "CLOUDFLARE": "Cloudflare",
    "VisaMobile2Cashback":"Visa割キャッシュバック"
}



class ChibabankHandler(BaseHandler):
    def __init__(self, sender):
        # 親クラスの初期化（self.bot = bot が実行される）
        super().__init__(sender)
        self.address="mail@vdebit.chibabank.co.jp"

    async def handle(self, details):
        text = base64.urlsafe_b64decode(details["payload"]["body"]["data"]).decode("utf-8")
        if details["subject"]=="【TSUBASAちばぎんVisaデビットカード】ご利用のお知らせ":
            # 抽出用パターン
            date_match = re.search(r'お取引日：\s*([\d/]+)', text)
            amount_match = re.search(r'お取引金額：\s*(.+)', text)
            content_match = re.search(r'お取引内容：\s*(.+)', text)
            auth_num = re.search(r'承認番号：\s*(\d+)', text).group(1)
            # 値の整形
            date = date_match.group(1) if date_match else "不明"
            # 金額は .00 JPY が邪魔なので数値部分だけ抜き取ってカンマを維持、または除去
            raw_price=amount_match.group(1)
            amount = amount_match.group(1).split('.')[0] if amount_match else "0"
            store = content_match.group(1).strip() if content_match else "不明"
            if store in TRACE_STORE :
                store=TRACE_STORE[store]
            embed=Embed(
                title="ちばぎんのvisaカードが使われました",
                description=store+"で"+raw_price+"利用しました。",
                timestamp=datetime.strptime(date, "%Y/%m/%d"),
            )
            embed.add_field(name="使用金額(日本円)", value=amount, inline=True)
            embed.add_field(name="承認番号", value=auth_num, inline=True)

            await self.sender(
                content=store+"で"+raw_price+"利用しました。",
                embed=embed
            )
        elif details["subject"]== "【TSUBASAちばぎんVisaデビットカード】ご返金受付のお知らせ":
            date_match = re.search(r'ご返金受付日：\s*([\d/]+)', text)
            amount_match = re.search(r'ご返金予定額：\s*(.+)', text)
            content_match = re.search(r'お取引内容：\s*(.+)', text)
            auth_match = re.search(r'承認番号：\s*(\d+)', text)

            # 2. 値の整形
            date = date_match.group(1) if date_match else "不明"
            auth_num = auth_match.group(1) if auth_match else "不明"

            # 金額の整形（-150.00 JPY -> -150）
            raw_price = amount_match.group(1) if amount_match else "0"
            amount = raw_price.split('.')[0] if amount_match else "0"

            # 加盟店名の整形
            store = content_match.group(1).strip() if content_match else "不明"
            if store in TRACE_STORE:
                store = TRACE_STORE[store]

            # 3. Embedの作成（返金用なので色やタイトルを変更すると分かりやすい）
            embed = Embed(
                title="ちばぎんデビット：返金/キャッシュバック",
                description=f"{store} より {raw_price}の返金受付がありました。",
                color=0x00ff00, # 返金なので緑色にするなど
                timestamp=datetime.strptime(date, "%Y/%m/%d"),
            )
            embed.add_field(name="返金額(日本円)", value=f"{amount}円", inline=True)
            embed.add_field(name="承認番号", value=auth_num, inline=True)

            # 4. 送信
            await self.sender(
                content=f"{store} から {raw_price}の返金がありました。",
                embed=embed
            )