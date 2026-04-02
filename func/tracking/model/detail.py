from dataclasses import dataclass

from datetime import datetime


@dataclass
class Detail:
    title:str
    place_name:str
    time:datetime
    place_url:str=""
