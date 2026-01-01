from dataclasses import dataclass,field
from typing import Callable
from .brand import Brand
@dataclass
class ArtistBase:
    artist:str
    code:int
    brand:Brand
    url:str
    getSong:Callable[[],str]
    exif:dict = field(default_factory=dict)