from dataclasses import dataclass,field
from enum import IntEnum
from datetime import datetime,date,timedelta
class Brand(IntEnum):
    yamato=1
    jp=2
    sagawa=3

@dataclass
class Detail:
    title:str
    place_name:str
    time:datetime
    place_url:str=""

@dataclass
class Pack:
    brand:Brand
    num:str
    state_title:str
    state_summary:str=""
    state_note:str=""
    type:str=""
    name:str=""
    est_date:date=None
    details:list[Detail]=field(default_factory=list)

def adjust_year(dt):
    """
    datetime または date の年越しを補正する
    """
    today = datetime.now().date()
    
    if isinstance(dt, datetime):
        d = dt.date()
        is_dt = True
    elif isinstance(dt, date):
        d = dt
        is_dt = False
    else:
        raise TypeError("datetime または date を渡してください")

    # 半年以上前なら翌年
    if d < today - timedelta(days=180):
        new_y = d.year + 1
        dt = dt.replace(year=new_y)

    return dt