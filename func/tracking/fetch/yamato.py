import requests				# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint
import utils
from datetime import datetime,date,timedelta



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
        data=utils.Pack(
            brand="yamato",
            num=pack.find(class_="tracking-invoice-block-title").get_text().split("：")[1],
            state_title=state.find(class_="tracking-invoice-block-state-title").get_text(),
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
                    data.est_date = utils.adjust_year(datetime.strptime(f"{today.year}/{s.find(class_="data").get_text()}", "%Y/%m/%d").date())

        details=pack.find(class_="tracking-invoice-block-detail")#進み具合
        if details:
            data.details=[]
            for detail in details.find_all("li"):
                now = datetime.now()
                d=utils.Detail(title=detail.find(class_="item").get_text(),time=utils.adjust_year(datetime.strptime(f"{now.year}年{detail.find(class_="date").get_text()}", "%Y年%m月%d日 %H:%M")),place_name="")
                place=detail.find(class_="name").find("a")
                if detail.find(class_="name").find("a"):    
                    d.place_url=place.get("href")
                    d.place_name=place.get_text()
                else:
                    d.place_name=detail.find(class_="name").get_text()
                
                data.details.append(d)
        res.append(data)
    return res




if __name__ == "__main__":
    pprint(get_data(input()))
