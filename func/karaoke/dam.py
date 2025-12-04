import json
import requests
from bs4 import BeautifulSoup as bs
headers = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "content-type": "application/json",
}
URL="https://www.clubdam.com/dkwebsys/search-api/"

"""
data = {
    "modelTypeCode": "1",
    "serialNo": "BA000001",#機種名。とりあえずWao向けの値で問題ない
    "keyword": "理芽",
    "compId": "1",
    "authKey": "2/Qb9R@8s*",#本番環境なら全部これ。決してAPIKey流出ではない。
    "sort": "2",
    "dispCount": "100",
    "pageNo": "1"
}
"""

def artistList():
    #https://www.clubdam.com/dkwebsys/search-api/SearchArtistByKeywordApi
    # fetch の body を Python の辞書に変換
    data = {
        "modelTypeCode": "1",
        "serialNo": "BA000001",
        "keyword": "理芽",
        "compId": "1",
        "authKey": "2/Qb9R@8s*",
        "sort": "2",
        "dispCount": "100",
        "pageNo": "1"
    }
    # POST リクエスト
    response = requests.post(URL+"SearchArtistByKeywordApi", headers=headers, json=data)

    # JSON を辞書に変換してインデント付きで表示
    data_dict = response.json()
    print(json.dumps(data_dict, indent=2, ensure_ascii=False))

def songList():
    #https://www.clubdam.com/dkwebsys/search-api/SearchMusicByKeywordApi
    data={
        "modelTypeCode":"1",
        "serialNo":"BA000001",
        "keyword":"理芽",
        "compId":"1",
        "authKey":"2/Qb9R@8s*",
        "sort":"2",
        "dispCount":"100",
        "pageNo":"1"
    }
    response = requests.post(URL+"SearchMusicByKeywordApi", headers=headers, json=data)
    # JSON を辞書に変換してインデント付きで表示
    data_dict = response.json()
    print(json.dumps(data_dict, indent=2, ensure_ascii=False))

def artistInfo():
    #https://www.clubdam.com/dkwebsys/search-api/GetMusicListByArtistApi
    data={
        "modelTypeCode":"1",
        "serialNo":"BA000001",
        "artistCode":"150623",
        #"contentsCode":null,
        #"damTomoMovieFlag":null,
        #"damTomoRecordingFlag":null,
        "compId":"1",
        "authKey":"2/Qb9R@8s*",
        "sort":"1",
        "dispCount":"100",
        "pageNo":"1"
    }

    response = requests.post(URL+"GetMusicListByArtistApi", headers=headers, json=data)
    # JSON を辞書に変換してインデント付きで表示
    data_dict = response.json()
    print(json.dumps(data_dict, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    dam_artistInfo()