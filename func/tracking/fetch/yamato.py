import aiohttp				# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint
from ..utils import adjust_year
from ..model.detail import Detail
from ..model.pack import Pack
from ..utils import state_changer
from datetime import datetime,date
from ..model.state import State

def fetch_yamato(num):
    s = requests.Session()
    payload={
        "backrequest":"get",
        "number01":num,
        "category":"1"
    }
    r = s.post('https://toi.kuronekoyamato.co.jp/cgi-bin/tneko',data=payload)
    print(r.text)
    soup = bs(r.text,'html.parser')
    packs=soup.find_all(class_="parts-tracking-invoice-block")#荷物ごとになる
    res=[]
    for pack in packs:
        state=pack.find(class_="tracking-invoice-block-state")
        state_title=state.find(class_="tracking-invoice-block-state-title").get_text()
        data=Pack(
            brand="yamato",
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
                    today = date.today()
                    t=s.find(class_="data").get_text()
                    if t!="-":
                        data.est_date = adjust_year(datetime.strptime(f"{today.year}/{t}", "%Y/%m/%d").date())

        details=pack.find(class_="tracking-invoice-block-detail")#進み具合
        if details:
            data.details=[]
            for detail in details.find_all("li"):
                now = datetime.now()
                d=Detail(title=detail.find(class_="item").get_text(),time=adjust_year(datetime.strptime(f"{now.year}年{detail.find(class_="date").get_text()}", "%Y年%m月%d日 %H:%M")),place_name="")
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
    pprint(fetch_yamato(input()))
