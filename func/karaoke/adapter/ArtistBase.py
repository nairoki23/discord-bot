from dataclasses import dataclass,field
from typing import Callable
@dataclass
class RawArtist:
    artist:str
    code:int
    brand:utils.Brand
    url:str
    getSong:Callable[[],str]
    exif:dict = field(default_factory=dict)