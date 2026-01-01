from func.karaoke.model.artist import ArtistData
from func.karaoke.builder.mergesong import merge_songs
class Artist(ArtistData):
    def getSong(self):
        return merge_songs(
            dam_list=[s for a in self.dam for s in a.getSong()],
            joy_list=[s for a in self.joy for s in a.getSong()]
        )
