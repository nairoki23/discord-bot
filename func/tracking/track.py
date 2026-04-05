from pprint import pprint

from .model.brand import Brand
from .fetch.yamato import fetch_yamato
from .fetch.sagawa import fetch_sagawa
from .fetch.jp import fetch_jp
from .model.pack import Pack
from service.container  import get_timer
from datetime import datetime, timedelta
from nanoid import generate
from .model.state import State
import asyncio
from urllib.parse import urlparse,parse_qs


FETCH_DELTA=timedelta(minutes=20)
FETCH_JITTER=timedelta(minutes=10)
class Tracking:
    def __init__(self,tracking_num:str,brand:Brand,name:str):
        self.latest_pack:Pack|None=None
        self.tracking_num:str=tracking_num
        self.brand:Brand=brand
        self.cb={}
        self.job_id=""
        self.name=name

    async def fetch_pack(self) -> Pack|None:
        pack=None
        if self.brand==Brand.yamato:
            pack= await fetch_yamato(self.tracking_num)
        elif self.brand == Brand.sagawa:
            pack= await fetch_sagawa(self.tracking_num)
        elif self.brand==Brand.jp:
            pack= await fetch_jp(self.tracking_num)
        else:
            return None
        pack.name=self.name

        return pack
    async def set_track(self):
        self.latest_pack=await self.fetch_pack()
        self.job_id=get_timer().schedule(datetime.now()+FETCH_DELTA,self.timer_cb,FETCH_JITTER)
        return self.latest_pack

    def set_cb(self,cb):
        cb_id=""
        while True:
            cb_id=str(generate(size=8))
            if cb_id not in self.cb:
                break

        self.cb[cb_id] = cb
        return cb_id

    def del_cb(self, cb_id):
        if cb_id not in self.cb:
            return False
        del self.cb[cb_id]
        return True

    async def timer_cb(self):
        now_pack=await self.fetch_pack()
        pprint(now_pack)
        if now_pack:
            if (self.latest_pack is None) or (len(now_pack.details)!=len(self.latest_pack.details)) or (now_pack.details[-1].title!=self.latest_pack.details[-1].title) or (now_pack.state_title!=self.latest_pack.state_title) or (now_pack.state_type)==State.arrival:
                for cb in self.cb.values():
                    result=cb(self.latest_pack)
                    if asyncio.iscoroutine(result):
                        await result
                    continue
            if now_pack.state_type==State.arrival:
                return None
        self.latest_pack=now_pack
        return datetime.now()+FETCH_DELTA



class Track:
    def __init__(self):
        self.trackings={
            Brand.yamato:{},
            Brand.sagawa: {},
            Brand.jp: {},
        }

    def parse_tracking(self,url_or_number: str,carrier:Brand|None=None):
        def is_url(s: str) -> bool:
            try:
                result = urlparse(s)
                return all([result.scheme, result.netloc])
            except:
                return False

        def extract_tracking_number(url: str) -> str | None:
            query = parse_qs(urlparse(url).query)

            # 日本郵便
            if "requestNo1" in query:
                return query["requestNo1"][0]
            # ヤマト
            if "no01" in query:
                return query["no01"][0]

            return None

        def detect_carrier_from_url(url: str) -> Brand|None:
            host = urlparse(url).netloc
            if "japanpost.jp" in host:
                return Brand("jp")
            if "kuronekoyamato.co.jp" in host:
                return Brand("yamato")
            if "sagawa-exp.co.jp" in host:
                return Brand("sagawa")

            return None

        if not is_url(url_or_number):
            return carrier,url_or_number
        carrier = detect_carrier_from_url(url_or_number)
        number = extract_tracking_number(url_or_number)
        return carrier,number


    async def fetch_pack(self,tracking_num:str,brand:Brand,name):
        return await Tracking(tracking_num,brand,name).fetch_pack()

    async def start_track(self,tracking_num,brand,name,cb):
        if tracking_num in self.trackings[brand]:
            return None
        try:
            self.trackings[brand][tracking_num]=Tracking(tracking_num,brand,name)
            cb_id=self.trackings[brand][tracking_num].set_cb(cb)
            await self.trackings[brand][tracking_num].set_track()
            #await self.trackings[brand][tracking_num].timer_cb()
        except Exception as e:
            print(e)
        return cb_id

    async def add_cb(self,tracking_num,brand,cb):
        if tracking_num not in self.trackings[brand]:
            return None
        cb_id = self.trackings[brand][tracking_num].set_cb(cb)
        return cb_id

    async def remove_cb(self,tracking_num,brand,cb):
        if tracking_num not in self.trackings[brand]:
            return False
        return self.trackings[brand][tracking_num].del_cb(cb)


_track=Track()

def get_track()->Track:
    global _track
    return _track
