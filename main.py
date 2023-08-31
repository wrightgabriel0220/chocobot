import asyncio
from functools import wraps
import json
from sys import stderr
from typing import Callable, Coroutine
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import jsonpickle
import yt_dlp

load_dotenv()

DISCORD_TOKEN = os.getenv("discord_token")
COMMAND_PREFIX = os.getenv("command_prefix")
VISIBLE_QUEUE_LENGTH = os.getenv("visible_queue_length")
IN_LOBBY_ROLE_ID = int(os.getenv("in_lobby_role_id"))

# Setting the intents. These should match the intents on the Discord Developer Portal
intents = discord.Intents.all()

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume = 0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop = None, stream = False):
        loop = loop if loop is not None else asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download = not stream))
        if "entries" in data:
            data = data["entries"][0]

        return data

class RadioQueue(list):
    current_song: YTDLSource

    def __init__(self):
        super().__init__(self)

    async def append(self, url: str):
        new_audio: YTDLSource

        try:
            new_audio = await YTDLSource.from_url(url)
        except Exception as err:
            _log_error(err, "RadioQueue.append")
        finally:
            super().append(new_audio)

        self.current_song = self[len(self) - 1]

    def get_queue_report(self):
        if len(self) == 0:
            return "There's nothing in the queue! Use !add_song <url> to add a song"

        newline = "\n"

        return newline.join([f"{i + 1}: {self[i]['title']}" for i in range(len(self))])
    
class ChocobotGuildRecord(discord.Guild):
    """A set of environmental variables storing state specific to each guild the bot is connected to"""
    def __init__(self, guild: discord.Guild, bot_command_channel: discord.abc.GuildChannel, in_lobby_role: discord.Role) -> None:
        self.name: str = guild.name
        self.guild: discord.Guild = guild
        self.bot_command_channel: discord.abc.GuildChannel = bot_command_channel
        self.song_queue: RadioQueue = RadioQueue()
        self.in_lobby_role: discord.Role = in_lobby_role
    
    def to_json(self) -> str:
        return jsonpickle.encode({
            "name": self.name,
            "bot_command_channel": self.bot_command_channel.name
        }, keys=True)
    
    @classmethod
    async def generate_record(cls, guild: discord.Guild, bot_command_channel: discord.ChannelType):
        fetched_in_lobby_role = discord.utils.get(guild.roles, name="In Server Lobby")
        in_lobby_role = fetched_in_lobby_role if fetched_in_lobby_role is not None else (
            await guild.create_role(name="In Server Lobby", hoist=True, mentionable=True, color=discord.Color.green())
        )

        return ChocobotGuildRecord(guild=guild, bot_command_channel=bot_command_channel, in_lobby_role=in_lobby_role)

    @classmethod
    def get_matching_guild_record(cls, target_guild: discord.Guild):
        return next((guild_record for guild_record in guild_registry if guild_record.guild.id == target_guild.id), None)

def bot_command_with_registry(name: str, help: str) -> Callable:
    def decorator(func: Coroutine):
        @wraps(func)
        @bot.command(name=name, help=help)
        async def inner(ctx, *args, **kwargs):
            guild_record = ChocobotGuildRecord.get_matching_guild_record(ctx.guild)

            if guild_record is not None:
                await func(ctx, guild_record, *args, **kwargs)
            else:
                await ctx.send("This command requires that you first register your guild. It'll only take a few seconds! Just use the !register command to get set up!")

        return inner
    return decorator

def bot_event_with_registry(func: Callable):
    @bot.event
    async def inner(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState, *args, **kwargs):
        guild_record = ChocobotGuildRecord.get_matching_guild_record(member.guild)

        if guild_record is not None:
            func(member, before, after, guild_record, *args, **kwargs)

        func(member, before, after)

    return inner

guild_registry: list[ChocobotGuildRecord] = []

def run_wakeup_protocol():
    with open("guild_archive.json") as guild_archive:
        _guild_registry: list[ChocobotGuildRecord] = jsonpickle.decode(guild_archive.read(), classes=ChocobotGuildRecord)
        for guild_record in _guild_registry:
            guild_registry.append(guild_record) 

bot = commands.Bot(command_prefix = COMMAND_PREFIX, intents = intents)


# ytdl configuration
yt_dlp.utils.bug_reports_message = lambda: 'There was an error!'
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': True,
    'quiet': False,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    'force-ipv4': True,
    'cachedir': False,
    'nokeepfragments': True
}

ffmpeg_options = {
    'options': '-vn'
}

# Initializing our ytdl client
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

def _log_error(err: Exception, tag: str = None):
    stderr.write(
        f"""[CHOCOBOT] There was an error at {tag}...
        {err}
        """
    )

@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    print(f"active guilds: {guild_registry}")

@bot_event_with_registry
async def on_voice_state_update(member: discord.Member, _, after: discord.VoiceState, guild_record: ChocobotGuildRecord) -> None:
    is_in_lobby = member.get_role(IN_LOBBY_ROLE_ID) is not None
    
    if not discord.utils.get(member.roles, name = "Chocobot"):
        if after.channel and not is_in_lobby:
            await member.add_roles(guild_record.in_lobby_role)
            await guild_record.bot_command_channel.send(f"{member.mention} has joined the lobby! {guild_record.in_lobby_role.mention}")
        elif not after.channel and is_in_lobby:
            await member.remove_roles(guild_record.in_lobby_role)

@bot.command(name = 'register', help = 'Sets initial, permanent configurations for the bot specific to this server')
async def register(ctx: commands.Context) -> None:
    REGISTER_TIMEOUT = 7000

    channel_names: [str] = [channel.name for channel in ctx.guild.channels]

    await ctx.send("Please type the *specific* name of your preferred bot commands channel, hyphens, etc... and all.")
    response: discord.Message = await bot.wait_for("message", check=lambda msg: msg.content in channel_names, timeout=REGISTER_TIMEOUT)
    bot_command_channel = discord.utils.get(ctx.guild.channels, name=response.content)
    
    await ctx.send(f"Registration for {ctx.guild.name} is complete. Enjoy!")
    guild_registry.append(await ChocobotGuildRecord.generate_record(bot_command_channel=bot_command_channel, guild=ctx.guild))
    with open("guild_archive.json", "w") as guild_archive:
        pickled_json_registry: str = jsonpickle.encode([guild_record.to_json() for guild_record in guild_registry])
        guild_archive.write(pickled_json_registry)

@bot.command(name = 'join', help = 'Tells the bot to join the voice channel')
async def join(ctx: commands.Context) -> None:
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.message.author.name} is not connected to a voice channel')
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name = 'leave', help = 'To make the bot leave the voice channel')
async def leave(ctx: commands.Context) -> None:
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send('The bot is not connected to a voice channel.')

@bot_command_with_registry(name = 'play', help = 'To play a new song, paused song, or paused queue')
async def play(ctx: commands.Context, guild_record: ChocobotGuildRecord, url: str = None) -> None:
    voice_client = ctx.message.guild.voice_client

    if url is not None:
        guild_record.song_queue.append(url)

    if voice_client.is_paused():
        voice_client.resume()
    elif not voice_client.is_playing():
        track = discord.FFmpegPCMAudio(
            executable = "ffmpeg.exe",
            source = ytdl.prepare_filename(guild_record.song_queue.current_song),
            options = ffmpeg_options,
        )

        def advance_queue(_):
            guild_record.song_queue.pop()

            if len(guild_record.song_queue) > 0:
                voice_client.play(track, after=advance_queue)

        voice_client.play(track, after=advance_queue)

@play.error
async def on_play_error(ctx: commands.Context, err: Exception) -> None:
    if not ctx.message.guild.voice_client:
        await ctx.send(f"The bot is not connected to a voice channel. Use {COMMAND_PREFIX}join to invite the bot to a channel and try again!")
    else:
        _log_error(err, "_on_play_error")

@bot_command_with_registry(name = 'add_song', help = 'To add a song to the front of the queue')
async def add_song(ctx: commands.Context, guild_record: ChocobotGuildRecord, url: str) -> None:
    await guild_record.song_queue.append(url)

    await ctx.send(guild_record.song_queue.get_queue_report())

@add_song.error
async def on_add_song_error(_, error: Exception):
    _log_error(error, "on_add_song_error")

@bot_command_with_registry(name = 'pause', help='Pauses the song currently playing if there is one')
async def pause(ctx: commands.Context, guild_record: ChocobotGuildRecord) -> None:
    if guild_record.guild.voice_client.is_playing():
        await guild_record.guild.voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot_command_with_registry(name = "queue", help="Display the current queue of songs up the visible queue limit")
async def queue(ctx: commands.Context, guild_record: ChocobotGuildRecord) -> None:
    await ctx.send(guild_record.song_queue.get_queue_report())

@bot_command_with_registry(name = "skip", help = "Skip the current song and begin playing the next song in the queue")
async def skip(ctx: commands.Context, guild_record: ChocobotGuildRecord) -> None:
    if len(guild_record.song_queue) > 1:
        await ctx.send("Skipping " + guild_record.song_queue.current_song["title"])

        if ctx.message.guild.voice_client.is_playing():
            guild_record.song_queue.remove(0)
            await play(ctx)
        else:
            guild_record.song_queue.pop()
    else:
        await ctx.send("There's nothing in the queue to skip.")

@bot_command_with_registry(name = "join_lobby", help = """
             Join the server LFG 'lobby'. LFG lobbies are just a way to indicate to other folks that you're looking
             to join a call or play something without having to just sit in call. When somebody joins the lobby while you're
             in it, the bot will ping you to let you know.
             """)
async def join_lobby(ctx: commands.Context, guild_record: ChocobotGuildRecord) -> None:
    is_in_lobby = ctx.author.get_role(IN_LOBBY_ROLE_ID) is not None

    if is_in_lobby:
        await ctx.send("You're already in the lobby.")
        return
    
    await ctx.author.add_roles(guild_record.in_lobby_role)

    await ctx.send(f"{ctx.author.mention} has joined the lobby! {guild_record.in_lobby_role.mention}")

@join_lobby.error
async def on_join_lobby_error(_, err: Exception) -> None:
    _log_error(err, "_on_join_lobby_error")

@bot_command_with_registry(name = "leave_lobby", help = """
            Leave the server LFG 'lobby'. LFG lobbies are just a way to indicate to other folks that you're looking
            to join a call or play something without having to just sit in call.
            """)
async def leave_lobby(ctx: commands.Context, guild_record: ChocobotGuildRecord) -> None:
    is_in_lobby = ctx.author.get_role(IN_LOBBY_ROLE_ID) is not None

    if not is_in_lobby:
        await ctx.send(f"{ctx.author.mention} is not in the lobby.")
        return

    await ctx.author.remove_roles(guild_record.in_lobby_role)

if __name__ == "__main__":
    run_wakeup_protocol()
    print(f"Guild Registry: {[guild_record.guild.name for guild_record in guild_registry]}")
    bot.run(DISCORD_TOKEN)