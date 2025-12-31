:ffrom enum import IntEnum
from typing import List
class Brand(IntEnum):
    DAM=1
    JOY=2

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

@dataclass
class RawArtist:
    artist:str
    code:int
    brand:Brand
    exif:dict = field(default_factory=dict)

@dataclass
class Artist:
    artists: List[str]
    damCode:list=field(default_factory=list)
    joyCode:list=field(default_factory=list)
    exif:dict = field(default_factory=dict)




def hira_to_kata(text: str) -> str:
    """
    文字列中のひらがなをカタカナに変換する
    漢字・記号・数字はそのまま
    """
    # ひらがな Unicode: ぁ(0x3041)～ゖ(0x3096)
    # カタカナ Unicode: ァ(0x30A1)～ヶ(0x30F6)
    hira_chars = "".join([chr(i) for i in range(0x3041, 0x3097)])
    kata_chars = "".join([chr(i) for i in range(0x30A1, 0x30F7)])
    return text.translate(str.maketrans(hira_chars, kata_chars))
