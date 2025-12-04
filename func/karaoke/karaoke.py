import dam
import joy
import utils
import re
from itertools import permutations


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
    NG=("[サビカラ]")
    for n in NG:
        if n in title:
            return 1
    return 0

def find_song(name):
    j_raw_list=joy.songList(name)
    d_raw_list=dam.songList(name)
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




if __name__=="__main__":
    for s in find_song(input()):
        print(s.title+"|"+s.artist+"\t"+s.damUrl+"|"+s.joyUrl)