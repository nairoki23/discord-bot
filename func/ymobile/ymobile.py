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
        self.charged=0
        self.usable=0
        self.used=0
        self.remaining=0


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
            return int(s[0])*1000+int(s[1])*(10**(4-len(s[1])))
        mon=self.res.find("h2",class_="res-fs16").get_text(strip=True)
        p=self.res.find_all("p",class_="res-fs14")
        ds=self.res.find(class_="list-toggle-content").find_all("table")
        self.kurikoshi=get_mb(ds[0].find("tbody").find("td").get_text(strip=True))
        self.base=get_mb(ds[1].find("tbody").find_all("tr")[1].find("td").get_text(strip=True))
        self.charged=get_mb(ds[2].find("tbody").find_all("tr")[1].find("td").find(string=True,recursive=False).strip())
        self.usable=self.kurikoshi+self.base+self.charged
        self.used=get_mb(ds[3].find("tbody").find("tr").find("td").get_text(strip=True))
        self.remaining=self.usable-self.used

    def get(self):
        self.login()
        self.access()
        self.trim()
print(__name__)
if __name__ == "__main__":
    y=Ymobile(config.get("PHONE_NUMBER"),config.get("YMOBILE_PASSWORD"))
    y.get()
    print("データ量残量："+str(y.remaining/1000)+"MB/"+str(y.usable/1000)+"MB")