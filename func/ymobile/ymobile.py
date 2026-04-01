import requests	
from bs4 import BeautifulSoup as bs
from datetime import datetime
from dotenv import dotenv_values
from discord.ext import commands
config = dotenv_values(".env")


import dataclasses
@dataclasses.dataclass
class YmobileData:
    kurikoshi: int = None
    base: int = None
    used: int = None
    all_usable: int = None
    remaining: int = None
    mon: str = None
    period: str = None
    tel: str = None

class Ymobile():
    def __init__(self,_PhoneNumber,_PassWord):
        self.PhoneNumber=_PhoneNumber
        self.PassWord=_PassWord
        self.s = requests.Session()
        

    def login(self):
        r = self.s.get('https://my.ymobile.jp/muc/d/webLink/doSend/MWBWL0130')
        soup = bs(r.text,'html.parser')
        ticket = soup.find('input',type='hidden').get('value')
        payload = {
            'telnum': self.PhoneNumber,
            'password': self.PassWord,
            'ticket':ticket
        }
        self.s.post('https://id.my.ymobile.jp/sbid_auth/type1/2.0/login.php', data=payload)

    def access(self):
        r = self.s.get('https://my.ymobile.jp/muc/d/webLink/doSend/MRERE0000')
        soup = bs(r.text,'html.parser')
        auth_token = soup.find_all('input')
        payload = {
            'mfiv': auth_token[0].get('value'),
            'mfym': auth_token[1].get('value'),
        }
        req = self.s.post('https://re61.my.ymobile.jp/resfe/top/', data=payload)
        self.res = bs(req.text,'html.parser')

    def trim(self):
        def get_mb(s:str) -> int:
            s=s.replace("GB", "").split(".")
            return int(s[0])*1000+int(s[1])*(10**(3-len(s[1])))
        
       
        data={}

        YmobileData()
        kurikoshi=0
        base=0
        used=0
        other=0
        for t in self.res.find(class_="list-toggle-content").find_all("table"):
            data[t.find("tbody").find("th").get_text(strip=True)]=t.find("tbody").find("td").get_text(strip=True)
            continue
        for k in data:
            if "くりこし分" in k:
                kurikoshi=get_mb(data[k])
            elif k=="基本データ量 残り":
                base=get_mb(data[k].split("／")[0])
            elif k=="使用量 合計":
                print(data[k])
                used=get_mb(data[k])
            else :
                other=other+get_mb(data[k])
        all_usable=kurikoshi+base+other
        p=self.res.find_all("p",class_="res-fs14")
        return YmobileData(
            kurikoshi=kurikoshi,
            base=base,
            used=used,
            all_usable=all_usable,
            remaining=all_usable-used,
            mon=self.res.find("h2",class_="res-fs16").get_text(strip=True),
            period=p[0].get_text(strip=True),
            tel=p[1].get_text(strip=True),
        )

    def get(self):
        self.login()
        self.access()
        return self.trim()
if __name__ == "__main__":
    y=Ymobile(config.get("PHONE_NUMBER"),config.get("YMOBILE_PASSWORD"))
    data=y.get()
    print(data)