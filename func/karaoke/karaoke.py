import dam
import joy
import utils
import re
from typing import List
import time

def feat_process(title: str) -> str:
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
    # 区切り文字の配列（必要に応じて追加してください）
    separators = ["&", "／", "/", "、", "・", "＋", "+", "と", ",", "×", "x", " and ", "feat", "-"]
    pattern = "|".join([re.escape(s) for s in separators])

    # キーは分割後のアーティスト名集合（ソートしたタプル）にすることで順序差を吸収
    processed_map = {}  # key: tuple(sorted(parts)) -> utils.Artist

    for raw in raw_list:
        parts = [p.strip() for p in re.split(pattern, raw.artist, flags=re.IGNORECASE)]
        parts = [feat_process(p) for p in parts if p]
        if not parts:
            continue
        key = tuple(sorted(parts))
        artists_list = list(key)
        if key not in processed_map:
            processed_map[key] = utils.Artist(
                artists=artists_list,
                code=[raw.code],
                brand=raw.brand,
                exif=raw.exif.copy()
            )
        else:
            processed_map[key].code.append(raw.code)

    return list(processed_map.values())


def find_song(name):
    j_raw_list=joy.songList(name)
    d_raw_list=dam.songList(name)
    return songMargeAndContinue(d_raw_list,j_raw_list)


def find_artist_song(name):
    search_key = feat_process(name)
    joy_artists = merge_artists(joy.artistList(name))
    dam_artists = merge_artists(dam.artistList(name))

    j_codes =  []
    d_codes = []
    for a in joy_artists:
        if search_key in a.artists:
            j_codes.append(a.code)
    for a in dam_artists:
        if search_key in a.artists:
            d_codes.append(a.code)

    j_songs = []
    d_songs = []
    for c in j_codes:
        time.sleep(0.5)
        j_songs += joy.artistInfo(c)

    for c in d_codes:
        time.sleep(0.5)
        d_songs += dam.artistInfo(c)

    # merge_songs は DAM, JOY のリストを受け取る
    
    return merge_songs(d_songs, j_songs)
    
まるばつ={True:"◯",False:"✕"}


if __name__=="__main__":
    for s in find_artist_song(input()):
        print(s.title+"|"+s.artist+"\t"+まるばつ[s.damUrl!=""]+"|"+まるばつ[s.joyUrl!=""])