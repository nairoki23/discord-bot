import aiohttp
import ssl
# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint
from ..utils import nearest_datetime, text_of
from ..model.detail import Detail
from ..model.pack import Pack
from ..model.brand import Brand
from ..utils import state_changer
from datetime import datetime
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

def parse_est_date(t:str,now:datetime|None=None):
    """「09/30 14:00-16:00」のようなお届け予定日時を datetime（時刻なしは date）にする。"""
    t=t.replace('　',' ').strip()
    date_match=re.search(r'(\d{1,2})/(\d{1,2})',t)
    if not date_match:
        raise ValueError("日付が見つからない")
    month,day=int(date_match.group(1)),int(date_match.group(2))
    # 時間帯指定なら最後の時刻（終わりの時刻）を使う
    time_match=re.search(r'(\d{1,2}):(\d{2})(?!.*\d{1,2}:\d{2})',t)
    if time_match:
        return nearest_datetime(month,day,int(time_match.group(1)),int(time_match.group(2)),now=now)
    return nearest_datetime(month,day,now=now).date()


def parse_detail_time(t:str,now:datetime|None=None)->datetime:
    """「09月29日 10:00」を datetime にする。"""
    m=re.search(r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})',t)
    if not m:
        raise ValueError(f"日時を読み取れない: {t}")
    return nearest_datetime(*(int(g) for g in m.groups()),now=now)


def parse_yamato(text:str,now:datetime|None=None)->Pack:
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
            # 荷物の状態によってはサマリや備考の要素がない
            state_summary=text_of(state.find(class_="tracking-invoice-block-state-summary")),
            state_note=text_of(state.find(class_="tracking-invoice-block-state-note")),
        )
        summary=pack.find(class_="tracking-invoice-block-summary")
        if summary:
            for s in summary.find_all("li"):
                item=text_of(s.find(class_="item")).replace("：","")
                if item=="商品名":
                    data.type=text_of(s.find(class_="data"))
                elif item=="お届け予定日時":
                    t=text_of(s.find(class_="data"))
                    if t.strip() not in ("","-"):
                        data.est_date=parse_est_date(t,now=now)

        details=pack.find(class_="tracking-invoice-block-detail")#進み具合
        if details:
            data.details=[]
            for detail in details.find_all("li"):
                d=Detail(title=detail.find(class_="item").get_text(),time=parse_detail_time(detail.find(class_="date").get_text(),now=now),place_name="")
                name=detail.find(class_="name")
                place=name.find("a") if name else None
                if place:
                    d.place_url=place.get("href")
                    d.place_name=place.get_text()
                else:
                    d.place_name=text_of(name)

                data.details.append(d)
        res.append(data)
    if not res:
        raise ValueError("荷物情報が見つからない")
    return res[0]


async def fetch_yamato(num):
    return parse_yamato(await fetch(num))


if __name__ == "__main__":
    pprint(asyncio.run(fetch_yamato(input())))
