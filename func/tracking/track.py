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
FETCH_JITTER=timedelta(minutes=5)
# 連続でこの回数取得に失敗したら追跡を打ち切る
MAX_FETCH_FAILURES=3


class AlreadyTrackingError(Exception):
    pass


class NotOwnerError(Exception):
    pass


def is_updated(old:Pack|None,new:Pack)->bool:
    if old is None:
        return True
    if new.state_title!=old.state_title:
        return True
    if len(new.details)!=len(old.details):
        return True
    if new.details and new.details[-1].title!=old.details[-1].title:
        return True
    return new.state_type==State.arrival


class Tracking:
    """
    荷物1件の追跡。
    cb は cb(pack) の形で呼ばれる。pack は更新後の Pack、
    取得失敗が続いて追跡を打ち切るときだけ None。
    """
    def __init__(self,tracking_num:str,brand:Brand,name:str,on_finish=None,owner_id:int|None=None):
        self.latest_pack:Pack|None=None
        # 追跡を依頼したユーザー。停止できるのはこのユーザーだけ
        self.owner_id:int|None=owner_id
        self.tracking_num:str=tracking_num
        self.brand:Brand=brand
        self.cb={}
        self.job_id=""
        self.name=name
        self.fail_count=0
        self.on_finish=on_finish

    async def fetch_pack(self) -> Pack|None:
        fetcher={
            Brand.yamato:fetch_yamato,
            Brand.sagawa:fetch_sagawa,
            Brand.jp:fetch_jp,
        }.get(self.brand)
        if fetcher is None:
            return None
        try:
            pack=await fetcher(self.tracking_num)
        except Exception as e:
            print(f"[tracking] {self.brand.value} {self.tracking_num} の取得に失敗: {e!r}")
            return None
        if pack is None:
            return None
        pack.name=self.name
        return pack

    async def set_track(self) -> Pack|None:
        """
        初回取得をして、配達完了でなければ定期取得を予約する。
        伝票番号が未登録などで初回取得に失敗しても、定期取得は予約する（None を返す）。
        """
        pack=await self.fetch_pack()
        self.latest_pack=pack
        if pack is None or pack.state_type!=State.arrival:
            self.job_id=get_timer().schedule(datetime.now()+FETCH_DELTA,self.timer_cb,FETCH_JITTER)
        return pack

    def cancel(self):
        if self.job_id:
            get_timer().cancel(self.job_id)
            self.job_id=""

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

    async def notify(self,pack:Pack|None):
        for cb in list(self.cb.values()):
            try:
                result=cb(pack)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"[tracking] {self.brand.value} {self.tracking_num} の通知に失敗: {e!r}")

    def finish(self):
        # timer_cb の中から呼ばれるので job の cancel はしない（None を返せば終了する）
        self.job_id=""
        if self.on_finish:
            self.on_finish(self)

    async def timer_cb(self):
        now_pack=await self.fetch_pack()
        if now_pack is None:
            self.fail_count+=1
            if self.fail_count>=MAX_FETCH_FAILURES:
                await self.notify(None)
                self.finish()
                return None
            return datetime.now()+FETCH_DELTA
        self.fail_count=0

        if is_updated(self.latest_pack,now_pack):
            await self.notify(now_pack)
        self.latest_pack=now_pack

        if now_pack.state_type==State.arrival:
            self.finish()
            return None
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
            elif "reqCodeNo1" in query:
                return query["reqCodeNo1"][0]
            # ヤマト
            if "no01" in query:
                return query["no01"][0]
            # 佐川
            if "okurijoNo" in query:
                return query["okurijoNo"][0]

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


    async def fetch_pack(self,tracking_num:str,brand:Brand,name) -> Pack|None:
        return await Tracking(tracking_num,brand,name).fetch_pack()

    async def start_track(self,tracking_num,brand,name,cb,owner_id:int|None=None) -> tuple[str,Pack|None]:
        """
        追跡を開始して (cb_id, 現在の Pack) を返す。
        既に追跡中なら AlreadyTrackingError。
        初回取得に失敗した場合（伝票番号が未登録など）も追跡は続け、Pack は None。
        既に配達完了なら通知は予約せず、追跡対象にも残さない。
        """
        if tracking_num in self.trackings[brand]:
            raise AlreadyTrackingError(tracking_num)
        tracking=Tracking(tracking_num,brand,name,on_finish=self._remove,owner_id=owner_id)
        cb_id=tracking.set_cb(cb)
        self.trackings[brand][tracking_num]=tracking
        try:
            pack=await tracking.set_track()
        except Exception:
            self._remove(tracking)
            raise
        if pack is not None and pack.state_type==State.arrival:
            self._remove(tracking)
        return cb_id,pack

    def stop_track(self,tracking_num,brand,requester_id:int|None=None) -> bool:
        """
        追跡を止める。追跡していなければ False。
        依頼者が決まっている追跡を別のユーザーが止めようとしたら NotOwnerError。
        """
        tracking=self.trackings[brand].get(tracking_num)
        if tracking is None:
            return False
        if tracking.owner_id is not None and tracking.owner_id!=requester_id:
            raise NotOwnerError(tracking_num)
        tracking.cancel()
        self._remove(tracking)
        return True

    def list_tracks(self) -> list[Tracking]:
        return [t for b in self.trackings.values() for t in b.values()]

    def _remove(self,tracking:Tracking):
        if self.trackings[tracking.brand].get(tracking.tracking_num) is tracking:
            del self.trackings[tracking.brand][tracking.tracking_num]

    async def add_cb(self,tracking_num,brand,cb):
        if tracking_num not in self.trackings[brand]:
            return None
        cb_id = self.trackings[brand][tracking_num].set_cb(cb)
        return cb_id

    async def remove_cb(self,tracking_num,brand,cb_id):
        if tracking_num not in self.trackings[brand]:
            return False
        return self.trackings[brand][tracking_num].del_cb(cb_id)


_track=Track()

def get_track()->Track:
    global _track
    return _track
