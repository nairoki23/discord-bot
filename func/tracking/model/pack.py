from .brand import Brand
from dataclasses import dataclass,field
from datetime import date
from .detail import Detail
from .state import State
@dataclass
class Pack:
    brand:Brand
    num:str
    state_title:str
    state_type: State
    state_summary:str=""
    state_note:str=""
    name:str=""
    type:str=""
    est_date:date=None
    details:list[Detail]=field(default_factory=list)