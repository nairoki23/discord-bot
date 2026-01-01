from func.karaoke.adapter.songbase import SongBase
from func.karaoke.model.song import SongData as Song
import func.karaoke.utils as utils


def merge_songs(dam_list: list[SongBase], joy_list: list[SongBase]) -> list[Song]:
    result = []
    used_dam = set()
    used_joy = set()
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
                result.append(Song(
                    title=joy_song.title,
                    artist=joy_song.artist,
                    dam=dam_song,
                    joy=joy_song,
                    exif={**dam_song.exif, **joy_song.exif}  # exif を統合
                ))
                used_dam.add(i)
                used_joy.add(j)
                found = True
                break

        if not found:
            # dam_list 単独
            result.append(Song(
                title=dam_song.title,
                artist=dam_song.artist,
                dam=dam_song,
                exif=dam_song.exif.copy()
            ))
            used_dam.add(i)

    # joy_list に残った単独の曲
    for j, joy_song in enumerate(joy_list):
        if j not in used_joy:
            joy_title = utils.t_process(joy_song.title)
            joy_artist = utils.t_process(joy_song.artist)
            result.append(Song(
                title=joy_song.title,
                artist=joy_song.artist,
                joy=joy_song,
                exif=joy_song.exif.copy()
            ))

    return result