import requests	
from bs4 import BeautifulSoup as bs
from datetime import datetime
import discord
from dotenv import dotenv_values
from discord.ext import commands
# .env読み込み
config = dotenv_values(".env")
GB_TO_MB = 1024


class Ymobile():
    def __init__(self,_PhoneNumber,_PassWord):
        self.PhoneNumber=_PhoneNumber
        self.PassWord=_PassWord
        self.s = requests.Session()
        
        #単位はmb
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
            return int(float(s.replace("GB", "")) * GB_TO_MB)
        ds=self.res.find(class_="list-toggle-content js-toggle-content m-top-20").find_all("table")
        self.kurikoshi=get_mb(ds[0].find("tbody").find("td").get_text(strip=True))
        self.base=get_mb(ds[1].find("tbody").find_all("tr")[1].find("td").get_text(strip=True))
        self.charged=get_mb(ds[2].find("tbody").find("tr").find("td").get_text(strip=True))
        self.usable=self.kurikoshi+self.base+self.charged
        self.used=get_mb(ds[3].find("tbody").find("tr").find("td").get_text(strip=True))
        self.remaining=self.usable-self.used

    def get(self):
        self.login()
        self.access()
        self.trim()

class DataUsage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.y=Ymobile(config.get("PHONE_NUMBER"),config.get("YMOBILE_PASSWORD"))
        self.users=[]
        for s in config.get("USER").split(","):
            self.users.append(int(s))
    # Slash Command の定義
    @discord.app_commands.command(name="usage", description="スマホの残りデータ容量確認")
    async def usage(self, interaction: discord.Interaction):
        if(interaction.user.id not in self.users):
            await interaction.response.send_message("これはお前には見せることができません。",ephemeral=True)
            return
        await interaction.response.defer()
        self.y.get()
        print("ああ")
        text = "ご利用状況をご案内します :bulb:\n\nデータ量残量："+str(self.y.remaining/GB_TO_MB)+"GB/"+str(self.y.usable/GB_TO_MB)+"GB"
        embed = discord.Embed(title="データ量", description=text)
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(DataUsage(bot))
