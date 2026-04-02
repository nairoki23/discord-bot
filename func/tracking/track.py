from html5lib.treewalkers import pprint
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


FETCH_DELTA=timedelta(minutes=20)
FETCH_JITTER=timedelta(minutes=5)
class Tracking:
    def __init__(self,tracking_num:str,brand:Brand,name:str):
        self.latest_pack:Pack|None=None
        self.tracking_num:str=tracking_num
        self.brand:Brand=brand
        self.cb={}
        self.job_id=""
        self.name=name

    def fetch_pack(self) -> Pack|None:
        pack=None
        try:
            if self.brand=="yamato":
                pack= fetch_yamato(self.tracking_num)
            elif self.brand == "sagawa":
                pack= fetch_sagawa(self.tracking_num)
            elif self.brand=="jp":
                pack= fetch_jp(self.tracking_num)
            else:
                return None
        except Exception as e:
            print(e)
        pack.name=self.name
        pprint(pack)

        return pack
    def set_track(self):
        self.latest_pack=self.fetch_pack()
        self.job_id=get_timer().schedule(datetime.now()+FETCH_DELTA,self.timer_cb,FETCH_JITTER)
        return self.latest_pack

    def set_cb(self,cb):
        cb_id=""
        while True:
            cb_id=str(generate(size=8))
            if cb_id not in self.cb:
                break
        self.cb[cb_id] = cb
        return True

    def del_cb(self, cb_id):
        if cb_id not in self.cb:
            return False
        del self.cb[cb_id]
        return True

    async def timer_cb(self):
        now_pack=self.fetch_pack()
        if now_pack:
            if (self.latest_pack is None) or (len(now_pack.details)!=len(self.latest_pack.details)) or (now_pack.details[-1]!=self.latest_pack.details[-1]) or (now_pack.state_title!=self.latest_pack.state_title):
                for cb in self.cb.values():
                    result=cb(now_pack)
                    if asyncio.iscoroutine(result):
                        await result
                    continue
            if now_pack.state_type==State.arrival:
                return None
        return datetime.now()+FETCH_DELTA



class Track:
    def __init__(self):
        self.trackings=[]
    def fetch_pack(self,tracking_num,brand,name):
        return Tracking(tracking_num,brand,name).fetch_pack()
    def start_track(self,tracking_num,brand,sender):
        self.fetch_pack(tracking_num,brand)


_track=Track()

def get_track()->Track:
    global _track
    return _track