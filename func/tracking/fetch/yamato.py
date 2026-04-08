import aiohttp
import ssl
# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint
from ..utils import adjust_year
from ..model.detail import Detail
from ..model.pack import Pack
from ..model.brand import Brand
from ..utils import state_changer
from datetime import datetime,date
from ..model.state import State
import asyncio
import re

def create_ssl_context():
    ctx = ssl.create_default_context()

    # 記事と同じポイント：AESGCMを許可
    ctx.set_ciphers(
        '@SECLEVEL=2:'
        'ECDH+AESGCM:'
        'ECDH+CHACHA20:'
        'ECDH+AES:'
        'DHE+AES:'
        'AESGCM:'
        '!aNULL:!eNULL:!aDSS:!SHA1:!AESCCM:!PSK'
    )
    return ctx




async def fetch(num):
    async with aiohttp.ClientSession() as session:
        payload = {
            "backrequest": "get",
            "number01": num,
            "category": "1",
        }

        async with session.post("https://toi.kuronekoyamato.co.jp/cgi-bin/tneko", data=payload,ssl=create_ssl_context()
) as response:
            if response.status != 200:
                raise Exception(f"HTTP error: {response.status}")

            text = await response.text()
            return text

async def fetch_yamato(num):
    text=await fetch(num)
    soup = bs(text,'html.parser')
    packs=soup.find_all(class_="parts-tracking-invoice-block")#荷物ごとになる
    res=[]
    for pack in packs:
        state=pack.find(class_="tracking-invoice-block-state")
        state_title=state.find(class_="tracking-invoice-block-state-title").get_text()
        data=Pack(
            brand=Brand("yamato"),
            num=pack.find(class_="tracking-invoice-block-title").get_text().split("：")[1],
            state_title=state_title,
            state_type=state_changer({"配達完了":State("arrival")},state_title),
            state_summary=state.find(class_="tracking-invoice-block-state-summary").get_text(),
            state_note=state.find(class_="tracking-invoice-block-state-note").get_text()
        )
        summary=pack.find(class_="tracking-invoice-block-summary")
        if summary:
            for s in summary.find_all("li"):
                if s.find(class_="item").get_text().replace("：","")=="商品名":
                    data.type=s.find(class_="data").get_text()
                elif s.find(class_="item").get_text().replace("：","")=="お届け予定日時":
                    t = s.find(class_="data").get_text()
                    if t != "-":
                        t="03/22"
                        t = t.replace('　', ' ').strip()
                        today = date.today()
                        # 日付取得
                        date_match = re.search(r'(\d{2}/\d{2})', t)
                        if not date_match:
                            raise ValueError("日付が見つからない")
                        date_part = date_match.group(1)
                        # 時刻取得
                        time_match = re.search(r'(\d{2}:\d{2})(?!.*\d{2}:\d{2})', t)
                        if time_match:
                            time_part = time_match.group(1)
                            data.est_date=adjust_year(datetime.strptime(f"{today.year}/{date_part} {time_part}", "%Y/%m/%d %H:%M"))
                        else:
                            data.est_date = adjust_year(datetime.strptime(f"{today.year}/{date_part}", "%Y/%m/%d").date())

        details=pack.find(class_="tracking-invoice-block-detail")#進み具合
        if details:
            data.details=[]
            for detail in details.find_all("li"):
                now = datetime.now()
                d=Detail(title=detail.find(class_="item").get_text(),time=adjust_year(datetime.strptime(f"{now.year}年{detail.find(class_='date').get_text()}", "%Y年%m月%d日 %H:%M")),place_name="")
                place=detail.find(class_="name").find("a")
                if detail.find(class_="name").find("a"):    
                    d.place_url=place.get("href")
                    d.place_name=place.get_text()
                else:
                    d.place_name=detail.find(class_="name").get_text()
                
                data.details.append(d)
        res.append(data)
    return res[0]




if __name__ == "__main__":
    pprint(asyncio.run(fetch_yamato(input())))
