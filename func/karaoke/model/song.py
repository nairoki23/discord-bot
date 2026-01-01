from dataclasses import dataclass,field
from func.karaoke.adapter import artistbase, songbase
@dataclass
class SongData:
    title:str
    artist:artistbase.ArtistBase
    dam:songbase.SongBase|None = None
    joy:songbase.SongBase|None = None
    exif:dict = field(default_factory=dict)