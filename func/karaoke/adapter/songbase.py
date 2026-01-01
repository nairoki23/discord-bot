from dataclasses import dataclass,field
from typing import Callable
from .brand import Brand
@dataclass
class SongBase:
    title:str
    artist:str
    url:str
    brand:Brand
    exif:dict = field(default_factory=dict)
