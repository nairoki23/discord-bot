import re
from func.karaoke.service.artist import Artist
from func.karaoke.adapter.artistbase import ArtistBase
def split_artist_name(name: str) -> list[str]:
    separators = ["&", "／", "/", "、", ",", "×", "x", " and ","feat.", "feat",]
    pattern = "|".join([re.escape(s) for s in separators])
    parts = [p.strip() for p in re.split(pattern, name, flags=re.IGNORECASE)]
    return [p for p in parts if p]

def merge_artists(joy_list: list[ArtistBase], dam_list: list[ArtistBase]) -> dict[str, Artist]:
    res={}
    for a in joy_list:
        for sa in split_artist_name(a.artist):
            if sa not in res:
                res[sa]=Artist(artist=sa,joy=[a],dam=[],exif=a.exif.copy())
            else:
                res[sa].joy.append(a)#将来的Artistを辞書でメモリにずっと置いとくなら重複チェックを入れる
    for a in dam_list:
        for sa in split_artist_name(a.artist):
            if sa not in res:
                res[sa]=Artist(artist=sa,dam=[a],joy=[],exif=a.exif.copy())
            else:
                res[sa].dam.append(a)#将来的Artistを辞書でメモリにずっと置いとくなら重複チェックを入れる
    return res