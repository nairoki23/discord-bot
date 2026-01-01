from dataclasses import dataclass,field
from typing import Callable
@dataclass
class SongBase:
    title:str
    artist:str
    url:str
    brand:utils.Brand
    exif:dict = field(default_factory=dict)
