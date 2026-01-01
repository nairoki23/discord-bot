from dataclasses import dataclass,field
import utils
import Adapter
@dataclass
class Song:
    title:str
    artist:artist.Artist
    dam:adapter.songbase.SongBase
    joy:adapter.songbase.SongBase
    exif:dict = field(default_factory=dict)