import logging
import re
import asyncio
from typing import Any, Callable, List, Optional, Dict, TypeVar
from discord import Client as DiscordClient, CustomActivity, Intents, Message, PartialEmoji, Reaction
from spotipy import Spotify, SpotifyClientCredentials
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import aiohttp

T = TypeVar('T')


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
logging.getLogger("discord.client").setLevel("DEBUG")

track_regex = re.compile("https://open.spotify.com/track/([a-zA-Z0-9]+)")
spotify_link_regex = re.compile("https://spotify.link/[a-zA-Z0-9]+")

intents = Intents.default()
intents.message_content = True
intents.presences = True

async def find_tracks(message: str) -> List[str]:
    tracks = track_regex.findall(message)
    links = spotify_link_regex.findall(message)
    link_tracks = []
    cookie_jar = aiohttp.DummyCookieJar() # no cookies pls
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        reqs = [
            asyncio.ensure_future(session.head(link, allow_redirects=False))
            for link in links
        ]
        for req in reqs:
            resp = await req
            if 300 <= resp.status < 400:
                redirect = resp.headers['Location']
                track = track_regex.findall(redirect)
                if track:
                    link_tracks.extend(track)
    return tracks + link_tracks


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

        matches = await find_tracks(message.content)
        if len(matches) == 0:
            return
        logger.info(f"Found {len(matches)} track IDs to add: {matches}")
        
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
