from dataclasses import dataclass,field
from typing import Callable
import utils
import re
import dam, joy
import song as s
@dataclass
class RawArtist:
    artist:str
    code:int
    brand:utils.Brand
    url:str
    getSong:Callable[[],str]
    exif:dict = field(default_factory=dict)

@dataclass
class Artist:
    artist:str
    dam:list[RawArtist]=field(default_factory=list)
    joy:list[RawArtist]=field(default_factory=list)
    exif:dict = field(default_factory=dict)

    def getSong(self):
        def merge_songs(dam_list: list[s.RawSong], joy_list: list[s.RawSong]) -> list[s.Song]:
            result = []
            used_dam = set()
            used_joy = set()
            print(dam_list)
            # 全組み合わせで比較
            for i, dam_song in enumerate(dam_list):
                dam_title = utils.t_process(dam_song.title)
                dam_artist = utils.t_process(dam_song.artist)
                found = False

                for j, joy_song in enumerate(joy_list):
                    if j in used_joy:
                        continue
                    joy_title = utils.t_process(joy_song.title)
                    joy_artist = utils.t_process(joy_song.artist)

                    if dam_title == joy_title and dam_artist == joy_artist:
                        # 一致したので Song を作成
                        result.append(utils.Song(
                            title=joy_song.title,
                            artist=joy_song.artist,
                            damUrl=dam_song.url,
                            joyUrl=joy_song.url,
                            exif={**dam_song.exif, **joy_song.exif}  # exif を統合
                        ))
                        used_dam.add(i)
                        used_joy.add(j)
                        found = True
                        break

                if not found:
                    # dam_list 単独
                    result.append(utils.Song(
                        title=dam_song.title,
                        artist=dam_song.artist,
                        damUrl=dam_song.url,
                        exif=dam_song.exif.copy()
                    ))
                    used_dam.add(i)

            # joy_list に残った単独の曲
            for j, joy_song in enumerate(joy_list):
                if j not in used_joy:
                    joy_title = utils.t_process(joy_song.title)
                    joy_artist = utils.t_process(joy_song.artist)
                    result.append(utils.Song(
                        title=joy_song.title,
                        artist=joy_song.artist,
                        joyUrl=joy_song.url,
                        exif=joy_song.exif.copy()
                    ))

            return result
        print(self.dam)
        return merge_songs(
            [a.getSong() for a in self.dam],
            [a.getSong() for a in self.joy]
        )


def search_artist(name:str,varios:bool=False) -> None|Artist|list[Artist]:
    def merge_artists(joy_list: list[RawArtist], dam_list: list[RawArtist]) -> dict[str, Artist]:
        def split_artist_name(name: str) -> list[str]:
            separators = ["&", "／", "/", "、", "・", "＋", "+", "と", ",", "×", "x", " and ","feat.", "feat", "-"]
            pattern = "|".join([re.escape(s) for s in separators])
            parts = [p.strip() for p in re.split(pattern, name, flags=re.IGNORECASE)]
            return [p for p in parts if p]
        res={}
        for a in joy_list:
            for sa in split_artist_name(a.artist):
                if sa not in res:
                    res[sa]=Artist(artist=sa,joy=[a],exif=a.exif.copy())
                else:
                    res[sa].joy.append(a)#将来的Artistを辞書でメモリにずっと置いとくなら重複チェックを入れる
        for a in dam_list:
            for sa in split_artist_name(a.artist):
                if sa not in res:
                    res[sa]=Artist(artist=sa,dam=[a],exif=a.exif.copy())
                else:
                    res[sa].dam.append(a)#将来的Artistを辞書でメモリにずっと置いとくなら重複チェックを入れる
        return res
    merged_artists = merge_artists(joy.artistSearch(name),dam.artistSearch(name))
    if varios:
        return list(merged_artists.values())
    else:
        return merged_artists.get(name)
    
if __name__ == "__main__":
    まるばつ={True:"◯",False:"✕"}
    for s in search_artist(input(),varios=False).getSong():
        print(s.title+"|"+s.artist+"\t"+まるばつ[s.dam.url!=""]+"|"+まるばつ[s.joy.url!=""])