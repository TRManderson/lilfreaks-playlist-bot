import logging
import re
import asyncio
from typing import Any, Callable, Optional, Dict, TypeVar
from discord import Client as DiscordClient, CustomActivity, Intents, Message, PartialEmoji, Reaction
from spotipy import Spotify, SpotifyClientCredentials
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

T = TypeVar('T')


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
logging.getLogger("discord.client").setLevel("DEBUG")

track_regex = re.compile("https://open.spotify.com/track/([a-zA-Z0-9]+)")

intents = Intents.default()
intents.message_content = True
intents.presences = True

class FreaksPlaylistClient(DiscordClient):
    spotify: Spotify
    playlist_id: str

    def __init__(self, **options: Any) -> None:
        super().__init__(intents=intents, **options)

    async def on_ready(self):
        logger.info(f'Logged on as {self.user.display_name}')
        await self.change_presence(activity=CustomActivity(
            name="curating playlists",
            emoji=PartialEmoji(name="notes"),
        ))

    async def on_message(self, message: Message):
        # don't respond to ourselves
        if message.author == self.user:
            return
        
        if message.channel.name != self.channel_name:
            return

        matches = track_regex.findall(message.content)
        if len(matches) == 0:
            return
        logger.info(f"Found {len(matches)} track IDs to add: {matches}")
        
        tracks_resp = await self.run_async(self.spotify.tracks, matches)
        await self.run_async(self.spotify.playlist_add_items, self.playlist_id, matches)
        await message.add_reaction(PartialEmoji(name="🎵"))
        
    
    async def run_async(self, fn: Callable[..., T], *args, **kwargs) -> asyncio.Future[T]:
        return await asyncio.get_running_loop().run_in_executor(self.spotify_executor, lambda: fn(*args, **kwargs))

    def run(
        self,
        discord_token: str,
        spotify_credentials: SpotifyClientCredentials,
        channel_name: str,
        playlist_id: str,
        *,
        discord_client_kwargs: Optional[Dict[str, Any]] = None,
        spotify_client_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        if spotify_client_kwargs is None:
            spotify_client_kwargs = {}
        if discord_client_kwargs is None:
            discord_client_kwargs = {}
        self.playlist_id = playlist_id
        self.channel_name = channel_name
        self.spotify_executor = ThreadPoolExecutor(max_workers=1)
        def set_spotify():
            self.spotify = Spotify(client_credentials_manager=spotify_credentials)
        try:
            self.spotify_executor.submit(set_spotify).result()
        except Exception:
            logger.exception("Error starting Spotify client")
            return
        try:
            return super().run(discord_token, **discord_client_kwargs)
        finally:
            self.spotify_executor.shutdown()
            del self.spotify
