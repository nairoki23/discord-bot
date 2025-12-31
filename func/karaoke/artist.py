class RawArtist:
    artist:str
    code:int
    brand:Brand
    exif:dict = field(default_factory=dict)
class JoyArtist:
class DamArtist:
class Artist:
    artist:str
    brand:Brand
    joy:list[JoyArtist]=field(default_factory=list)
    dam:list[DamArtist]=field(default_factory=list)
    exif:dict = field(default_factory=dict)