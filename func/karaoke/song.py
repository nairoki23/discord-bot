from dataclasses import dataclass,field
import utils
import artist
@dataclass
class RawSong:
    title:str
    artist:str
    url:str
    brand:utils.Brand
    exif:dict = field(default_factory=dict)

@dataclass
class Song:
    title:str
    artist:artist.Artist
    dam:RawSong
    joy:RawSong
    exif:dict = field(default_factory=dict)