import requests				# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint
import utils
from datetime import datetime
from ..model.brand import Brand


def fetch_jp(num):
    payload = {
        'reqCodeNo1':num,}
    s = requests.Session()
    r = s.get('https://trackings.post.japanpost.jp/services/srv/search/direct?locale=ja',params=payload)

    soup = bs(r.text, 'html.parser')
    pack=soup.find("div",class_="indent").find_all("table")
    kyoku={}
    for p in pack[2].find_all("tr"):
        tds=p.find_all("td")
        if len(tds)!=3:
            continue
        l=tds[1].find("a")
        kyoku[l.get_text()]=l.get("href")
        continue
    details=[]
    for i,d in enumerate(pack[1].find_all("tr")):
        if i%2:
            continue
        tds=d.find_all("td")
        if len(tds)!=5:
            continue
        place_name=tds[3].get_text()
        details.append(
            utils.Detail(
                title=tds[1].get_text(),
                time=datetime.strptime(tds[0].get_text(), "%Y/%m/%d %H:%M"),
                place_name=place_name,
                place_url=kyoku[place_name.split("（")[0]]
            )
        )
        continue
    
    p_i=pack[0].find_all("td")
    res=utils.Pack(
        brand="jp",
        num=p_i[0].get_text(),
        type=p_i[1].get_text(),
        details=details,
        state_title=details[-1].title,
    )  
    return res


if __name__ == "__main__":
    pprint(get_data(input()))