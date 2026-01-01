from dataclasses import dataclass,field

from func.karaoke.adapter.artistbase import ArtistBase

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass    


@dataclass
class ArtistData:
    artist:str
    dam:list[ArtistBase]=field(default_factory=list)
    joy:list[ArtistBase]=field(default_factory=list)
    exif:dict = field(default_factory=dict)