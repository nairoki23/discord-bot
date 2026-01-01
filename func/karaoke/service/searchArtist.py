import re
from func.karaoke.adapter import dam, joy
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