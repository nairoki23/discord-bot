from func.karaoke.service.artist import Artist
from func.karaoke.adapter import dam,joy
from func.karaoke.builder.mergeartist import merge_artists

def search_artist(name:str,varios:bool=False) -> None|Artist|list[Artist]:
    merged_artists = merge_artists(joy.artistSearch(name),dam.artistSearch(name))
    if varios:
        return list(merged_artists.values())
    else:
        return merged_artists.get(name)
    
if __name__ == "__main__":
    まるばつ={True:"◯",False:"✕"}
    a=search_artist(input(),varios=False)
    for s in a.getSong():
        print(s.title+"|"+s.artist+"\t"+まるばつ[s.dam is not None]+"|"+まるばつ[s.joy is not None ])