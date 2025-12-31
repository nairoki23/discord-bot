from dataclasses import dataclass,field
@dataclass
class RawArtist:
    artist:str
    code:int
    brand:Brand
    url:str
    getSong:Callable[[],str]
    exif:dict = field(default_factory=dict)

@dataclass
class Artist:
    artist:str
    raw:list[RawArtist]=field(default_factory=list)
    exif:dict = field(default_factory=dict)

    def getSong(self):
        return [a.getSong() for a in self.raw]
            
def search_artist() -> None|Artist|Artist[]:

