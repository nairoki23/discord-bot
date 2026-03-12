import requests	
from bs4 import BeautifulSoup as bs
from datetime import datetime
from dotenv import dotenv_values
from discord.ext import commands
config = dotenv_values(".env")


class Ymobile():
    def __init__(self,_PhoneNumber,_PassWord):
        self.PhoneNumber=_PhoneNumber
        self.PassWord=_PassWord
        self.s = requests.Session()
        
        #単位は1mb
        self.kurikoshi=0
        self.base=0
        self.other=0#その他容量
        self.used=0


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
        print(self.res)
        mon=self.res.find("h2",class_="res-fs16").get_text(strip=True)
        p=self.res.find_all("p",class_="res-fs14")
        data={}
        for t in self.res.find(class_="list-toggle-content").find_all("table"):
            data[t.find("tbody").find("th").get_text(strip=True)]=t.find("tbody").find("td").get_text(strip=True)
            continue
        for k in data:
            if "くりこし分" in k:
                self.kurikoshi=get_mb(data[k])
            elif k=="基本データ量 残り":
                self.base=get_mb(data[k].split("／")[0])
            elif k=="使用量 合計":
                print(data[k])
                self.used=get_mb(data[k])
            else :
                self.other=self.other+get_mb(data[k])
        all_usable=self.kurikoshi+self.base+self.other
        return {
            "kurikoshi":self.kurikoshi,
            "base":self.base,
            "used":self.used,
            "all_usable":all_usable,
            "remaining":all_usable-self.used
        }

    def get(self):
        self.login()
        self.access()
        return self.trim()
if __name__ == "__main__":
    y=Ymobile(config.get("PHONE_NUMBER"),config.get("YMOBILE_PASSWORD"))
    data=y.get()
    print(data)