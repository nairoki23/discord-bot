@dataclass
class RawSong:
    title:str
    artist:str
    url:str
    brand:Brand
    exif:dict = field(default_factory=dict)

@dataclass
class Song:
    title:str
    artist:str
    damUrl:str=""
    joyUrl:str=""
    exif:dict = field(default_factory=dict)