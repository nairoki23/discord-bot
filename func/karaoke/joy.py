import requests				# HTTP通信ライブラリ
from bs4 import BeautifulSoup as bs
import json
#魔法のHeaders
headers = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    "x-jsp-app-name": "0000800",
}
URL="https://mspxy.joysound.com/Common/ContentsList"
s=requests.Session()#セッション

"""
data = {
    "format": "artist",#all,artist
    "kindCnt": "1",
    "kind1": "artist",#song,artist,selArtist
    "word1": word,#検索ワード、selArtistの場合は
    "match1": "partial",#部分一致:partial,完全一致:exact,前方一致:front
    "start": "1",
    "count": "20",#省くと無制限
    "sort": "popular",
    "order": "desc",
    "apiVer": "1.0"
}


"""
def songList(word):
    data = {
        "format": "all",
        "kindCnt": "1",
        "kind1": "song",
        "word1": word,
        "match1": "partial",
        "start": "1",
        "count": "20",
        "sort": "popular",
        "order": "desc",
        "apiVer": "1.0"
    }
    r=s.post(URL,data=data,headers=headers)
    data_dict = r.json()
    #print(json.dumps(data_dict, indent=2, ensure_ascii=False))
    return data_dict["contentsList"]

def artistList(word):
    data = {
        "format": "artist",
        "kindCnt": "1",
        "kind1": "artist",
        "word1": word,
        "match1": "partial",
        "start": "1",
        "count": "20",
        "sort": "popular",
        "order": "desc",
        "apiVer": "1.0"
    }

    r=s.post(URL,data=data,headers=headers)
    data_dict = r.json()
    #print(json.dumps(data_dict, indent=2, ensure_ascii=False))
    return data_dict["artistList"]

def artistInfo(word):
    data = {
        "format": "all",
        "kindCnt": "1",
        "kind1": "selArtist",
        "word1": word,
        "match1": "exact",
        "start": "1",
        "count": "20",
        "sort": "popular",
        "order": "desc",
        "apiVer": "1.0"
    }

    r=s.post(URL,data=data,headers=headers)
    data_dict = r.json()
    #print(json.dumps(data_dict, indent=2, ensure_ascii=False))
    return data_dict


if __name__ == "__main__":
    print(json.dumps(joy_artistInfo("401003"), indent=2, ensure_ascii=False))