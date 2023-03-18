from . import FreaksPlaylistClient
from typing import TypedDict
from spotipy import SpotifyClientCredentials, SpotifyOAuth
import os

class Config(TypedDict):
    discord_token: str
    spotify_credentials: SpotifyOAuth
    channel_name: str
    playlist_id: str


client = FreaksPlaylistClient()

def load_config() -> Config:
    auth = SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
        redirect_uri="BROKEN",
        scope="playlist-modify-public"
    )
    return {
        "discord_token": os.environ.get("DISCORD_TOKEN"),
        "spotify_credentials": auth,
        "channel_name": os.environ.get("CHANNEL_NAME"),
        "playlist_id": os.environ.get("PLAYLIST_ID"),
    }

if __name__ == "__main__":
    client.run(**load_config())