import requests				# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
from pprint import pprint
import utils
from datetime import datetime

def get_data(num):
    payload = {
        'okurijoNo':num,}
    s = requests.Session()
    r = s.get('https://k2k.sagawa-exp.co.jp/p/web/okurijosearch.do',params=payload)

    soup = bs(r.text, 'html.parser')
    print (soup)
    res={}
    packs=soup.find("section",id="c01")#荷物ごとになる
    st= packs.find("dt",id="list1")
    res=utils.Pack(
        brand=3,
        num=st.find(class_="number nowrap").find("strong").get_text(strip=True),
        state_title=st.find("span",class_="state").get_text(strip=True),
        state_summary=st.find("td",colspan="3").get_text(strip=True),
        details=[]
    )
    detail=packs.find("dd",id="detail1").find_all("table",class_="table_basic table_okurijo_detail2")
    info=detail[0].find_all("tr")#色々情報取れるけどヤマトに合わせて設計してるので捨てる
    if info[4].find("th").get_text(strip=True)=="お荷物個数":
        res.type="お荷物個数"+info[4].find("td").get_text(strip=True)
    
    for d in detail[1].find_all("tr"):
        tds=d.find_all("td")
        if len(tds)!=3:
            continue
        res.details.append(
            utils.Detail(
                title=tds[0].get_text(strip=True),
                time=utils.adjust_year(datetime.strptime(f"{datetime.now().year}/{tds[1].get_text(strip=True)}", "%Y/%m/%d %H:%M")),
                place_name=tds[2].get_text(strip=True)
            )
        )
    return res

if __name__ == "__main__":
    pprint(get_data(input()))