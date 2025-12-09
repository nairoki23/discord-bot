import requests				# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint

def get_data(num):
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
        data={}
        data["num"]=pack.find(class_="tracking-invoice-block-title").get_text().split("：")[1]
        state=pack.find(class_="tracking-invoice-block-state")
        data["state"]={}
        data["state"]["title"]=state.find(class_="tracking-invoice-block-state-title").get_text()
        data["state"]["summary"]=state.find(class_="tracking-invoice-block-state-summary").get_text()
        data["state"]["note"]=state.find(class_="tracking-invoice-block-state-note").get_text()
        summary=pack.find(class_="tracking-invoice-block-summary")
        data["summary"]={}
        if summary:
            for s in summary.find_all("li"):
                data["summary"][s.find(class_="item").get_text().replace("：","")]=s.find(class_="data").get_text()
        details=pack.find(class_="tracking-invoice-block-detail")#進み具合
        data["detail"]=[]
        if details:
            for detail in details.find_all("li"):
                d={}
                d["title"]=detail.find(class_="item").get_text()
                d["date"]=detail.find(class_="date").get_text()
                place=detail.find(class_="name").find("a")
                if detail.find(class_="name").find("a"):    
                    d["place_url"]=place.get("href")
                    d["place_name"]=place.get_text()
                else:
                    d["place_name"]=detail.find(class_="name").get_text()
                data["detail"].append(d)
        res.append(data)
    return res




if __name__ == "__main__":
    pprint(get_data(input()))
