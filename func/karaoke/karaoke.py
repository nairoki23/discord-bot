import dam
import joy
import utils
import re
from typing import List


def feat_process(title: str) -> str:
    """
    - 'feat.' 以降を削除
    - 前後の空白を削除
    - 曲名内の連続する空白も 1 つにまとめる
    """
    # 'feat.' 以降を削除（大文字・小文字対応）
    title = re.split(r"\s*feat\..*", title, flags=re.IGNORECASE)[0]
    
    # 前後の空白削除 & 連続する空白を 1 つにまとめる
    title = re.sub(r"\s+", " ", title.strip())
    
    return title

def is_NG(title:str) ->str:
    NG=("[サビカラ]","TV-Size","[生音]")
    for n in NG:
        if n in title:
            return 1
    return 0

def merge_songs(dam_list: List[utils.RawSong], joy_list: List[utils.RawSong]) -> List[utils.Song]:
    result = []
    used_dam = set()
    used_joy = set()

    # 全組み合わせで比較
    for i, dam_song in enumerate(dam_list):
        dam_title = feat_process(dam_song.title)
        dam_artist = feat_process(dam_song.artist)
        found = False

        for j, joy_song in enumerate(joy_list):
            if j in used_joy:
                continue
            joy_title = feat_process(joy_song.title)
            joy_artist = feat_process(joy_song.artist)

            if dam_title == joy_title and dam_artist == joy_artist:
                # 一致したので Song を作成
                result.append(utils.Song(
                    title=dam_title,
                    artist=dam_artist,
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
                title=dam_title,
                artist=dam_artist,
                damUrl=dam_song.url,
                exif=dam_song.exif.copy()
            ))
            used_dam.add(i)

    # joy_list に残った単独の曲
    for j, joy_song in enumerate(joy_list):
        if j not in used_joy:
            joy_title = feat_process(joy_song.title)
            joy_artist = feat_process(joy_song.artist)
            result.append(utils.Song(
                title=joy_title,
                artist=joy_artist,
                joyUrl=joy_song.url,
                exif=joy_song.exif.copy()
            ))

    return result




def songMargeAndContinue(j_raw_list,d_raw_list):
    res=[]
    for _ in range(len(j_raw_list)):
        j_raw=j_raw_list.pop()
        if is_NG(j_raw.title):
            continue
        i=0
        for _ in range(len(d_raw_list)):
            d_raw=d_raw_list[i]
            if is_NG(d_raw.title):
                del d_raw_list[i]
                continue
            if feat_process(j_raw.title)==feat_process(d_raw.title) and feat_process(j_raw.artist)==feat_process(d_raw.artist):
                res.append(utils.Song(
                    title=feat_process(d_raw.title),
                    artist=feat_process(d_raw.artist),
                    damUrl=d_raw.url,
                    joyUrl=j_raw.url
                ))
                break
            i+=1
        else:
            res.append(utils.Song(
                title=feat_process(j_raw.title),
                artist=feat_process(j_raw.artist),
                joyUrl=j_raw.url
            ))
            break
        del d_raw_list[i]
    for a in d_raw_list:
        res.append(utils.Song(
            title=feat_process(a.title),
            artist=feat_process(a.artist),
            damUrl=a.url))
    return res

def merge_artists(raw_list: List[utils.RawArtist]) -> List[utils.Artist]:
    """
    RawArtist のリストをまとめて Artist のリストにする
    """
    processed_map = {}  # feat_process した名前 → Artist
    for raw in raw_list:
        processed_name = feat_process(raw.artist)
        if processed_name not in processed_map:
            # 新規に Artist を作成
            processed_map[processed_name] = utils.Artist(
                artist=processed_name,
                code=[raw.code],
                brand=raw.brand,
                exif=raw.exif.copy()
            )
        else:
            # 既存の Artist に code を追加
            processed_map[processed_name].code.append(raw.code)

    return list(processed_map.values())


def find_song(name):
    j_raw_list=joy.songList(name)
    d_raw_list=dam.songList(name)
    return songMargeAndContinue(d_raw_list,j_raw_list)


def find_artist_song(name):
    j_song=[]
    d_song=[]
    for a in merge_artists(joy.artistList(name)):
        if a.artist!=name:
            continue
        for c in a.code:
            j_song+=joy.artistInfo(c)
    for a in merge_artists(dam.artistList(name)):
        if a.artist!=name:
            continue
        for c in a.code:
            d_song+=dam.artistInfo(c)
    return merge_songs(d_song,j_song)
    
まるばつ={True:"◯",False:"✕"}


if __name__=="__main__":
    for s in find_artist_song(input()):
        print(s.title+"|"+s.artist+"\t"+まるばつ[s.damUrl!=""]+"|"+まるばつ[s.joyUrl!=""])