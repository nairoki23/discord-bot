from enum import IntEnum
from typing import List
from dataclasses import dataclass,field
import re
def t_process(title: str) -> str:
    """
    - 'feat.' 以降を削除
    - 前後の空白を削除
    - 曲名内の連続する空白も 1 つにまとめる
    """
    # 'feat.' 以降を削除（大文字・小文字対応）
    title = title.replace("!", "！")
    title = re.split(r"\s*feat\..*", title, flags=re.IGNORECASE)[0]
    
    # 前後の空白削除 & 連続する空白を 1 つにまとめる
    title = re.sub(r"\s+", " ", title.strip())
    
    return title
"""
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
"""



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
