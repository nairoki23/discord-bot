from datetime import datetime
from .model.state import State


def nearest_datetime(month:int,day:int,hour:int=0,minute:int=0,now:datetime|None=None)->datetime:
    """
    年のない月日（と時刻）に、now に最も近くなる年を補う。
    過去の履歴（1月に12月の履歴を見る）と未来の予定（12月に1月の予定を見る）の
    どちらの年越しにも対応する。
    """
    now=now or datetime.now()
    candidates=[]
    for year in (now.year-1,now.year,now.year+1):
        try:
            candidates.append(datetime(year,month,day,hour,minute))
        except ValueError:
            # 2/29 が存在しない年
            continue
    return min(candidates,key=lambda dt:abs(dt-now))


def text_of(el,strip:bool=False)->str:
    """要素がなければ空文字を返す get_text。"""
    if el is None:
        return ""
    return el.get_text(strip=strip)


def state_changer(dic,state):
    if state in dic:
        return dic[state]
    else:
        return State("other")
