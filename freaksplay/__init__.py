from ast import Dict
from ctypes import Union
import logging
import re
import asyncio
from typing import Any, Callable, Optional, Type, TypeVar
from discord.client import Client as DiscordClient, Message
from spotipy import Spotify, SpotifyClientCredentials
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')


logger = logging.getLogger(__name__)
logger.setLevel("INFO")

track_regex = re.compile("https://open.spotify.com/track/([a-zA-Z0-9]+)")

class FreaksPlaylistclient(DiscordClient):
    spotify: Spotify
    playlist_id: str

    def __init__(self, *, intents: Intents, **options: Any) -> None:
        super().__init__(self, intents=intents, **options)

    async def on_ready(self):
        logger.info('Logged on as', self.user)

    async def on_message(self, message: Message):
        # don't respond to ourselves
        if message.author == self.user:
            return
        
        if message.channel.name != self.channel_name:
            return

        matches = track_regex.findall(message.content)
        if len(matches) == 0:
            return
        logger.info(f"Found {len(matches)} track IDs to add")
        await message.channel.send("Adding " + ("one track" if len(matches) == 1 else f"{len(matches)} tracks") + " to playlist")
        
        tracks = await self.run_async(self.spotify.tracks, matches)
        print(tracks)
        await self.run_async(self.spotify.playlist_add_items, self.playlist_id, matches)
        await message.channel.send(f"Added {len(tracks)} item(s) to playlist")
            
        
    async def __aenter__(self) -> 'FreaksPlaylistclient':
        return await super().__aenter__()

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        try:
            return await super().__aexit__(exc_type, exc_value, traceback)
        finally:
            self.spotify.stop()
    
    async def run_async(self, fn: Callable[..., T], *args, **kwargs) -> asyncio.Future[T]:
        return asyncio.get_running_loop().run_in_executor(self.spotify_executor, lambda: fn(*args, **kwargs))

    def run(
        self,
        discord_token: str,
        spotify_credentials: SpotifyClientCredentials,
        channel_name: str,
        playlist_id: str,
        *,
        discord_client_kwargs=Dict[str, Any],
        spotify_client_kwargs=Dict[str, Any],

    ) -> None:
        if spotify_client_kwargs is None:
            spotify_client_kwargs = {}
        if discord_client_kwargs is None:
            discord_client_kwargs = {}
        self.playlist_id = playlist_id
        self.channel_name = channel_name
        self.spotify_executor = ThreadPoolExecutor(max_workers=1)
        def set_spotify():
            self.spotify = Spotify(spotify_credentials)
        try:
            self.spotify_executor.submit(set_spotify).result()
        except Exception:
            logger.exception("Error starting Spotify client")
            return
        return super().run(discord_token, **discord_client_kwargs)
