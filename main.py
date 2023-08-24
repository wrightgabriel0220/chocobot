import asyncio
from sys import stderr
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

DISCORD_TOKEN = os.getenv("discord_token")
COMMAND_PREFIX = os.getenv("command_prefix")
VISIBLE_QUEUE_LENGTH = os.getenv("visible_queue_length")
IN_LOBBY_ROLE_ID = int(os.getenv("in_lobby_role_id"))
OUT_LOBBY_ROLE_ID = int(os.getenv("out_lobby_role_id"))


# Setting the intents. These should match the intents on the Discord Developer Portal
intents = discord.Intents.all()


# Connecting to an individual client of Chocobot
client = discord.Client(intents = intents)
bot = commands.Bot(command_prefix = COMMAND_PREFIX, intents = intents)

# ytdl configuration
yt_dlp.utils.bug_reports_message = lambda: 'There was an error!'
ytdl_format_options: yt_dlp = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': True,
    'quiet': True,
    'simulate': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
    'force-ipv4': True,
    'cachedir': False,
}

ffmpeg_options = {
    'options': '-vn'
}


# Initializing our ytdl client
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume = 0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop = None, stream = False):
        loop = loop if loop else asyncio.get_event_loop()
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

        super().append(new_audio)
        self.current_song = self[len(self) - 1]

    def get_queue_report(self):
        newline = "\n"

        return f"""
            -> Now playing: {self[0]['title']} <-

            {newline.join([f"{i + 1}: {self[i]['title']}" for i in range(len(self)) if i > 0])}
        """

song_queue = RadioQueue()

def _log_error(err: Exception, tag: str = None):
    stderr.write(
        f"""[CHOCOBOT] There was an error at {tag}...
        {err}
        """
    )

@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    # TODO: Implement role creation when bot joins server if needed roles are not already present
    pass

@bot.event
async def on_voice_state_update(member: discord.Member, _, after: discord.VoiceState) -> None:
    out_lobby_role = member.guild.get_role(OUT_LOBBY_ROLE_ID)
    in_lobby_role = member.guild.get_role(IN_LOBBY_ROLE_ID)

    if after.channel and out_lobby_role:
        await member.add_roles(in_lobby_role)
        await member.remove_roles(out_lobby_role)
    elif not after.channel and in_lobby_role:
        await member.add_roles(out_lobby_role)
        await member.remove_roles(in_lobby_role)

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

@bot.command(name = 'play', help = 'To play a new song, paused song, or paused queue')
async def play(ctx: commands.Context, url = None):
        voice_client = ctx.message.guild.voice_client

        if url is not None:
            song_queue.append(url)
        
        if voice_client.is_paused():
            voice_client.resume()
        elif not voice_client.is_playing():
            voice_client.play(discord.FFmpegPCMAudio(
                executable = "ffmpeg.exe",
                source = ytdl.prepare_filename(song_queue.current_song),
                options = ffmpeg_options
            ))
            await ctx.send(f"**-> Now Playing: {song_queue[len(song_queue) - 1].title} <-**")

@play.error
async def on_play_error(ctx: commands.Context, err: Exception) -> None:
    if not ctx.message.guild.voice_client:
        await ctx.send(f"The bot is not connected to a voice channel. Use {COMMAND_PREFIX}join to invite the bot to a channel and try again!")
    else:
        _log_error(err, "_on_play_error")

@bot.command(name = 'add_song', help = 'To add a song to the front of the queue')
async def add_song(ctx: commands.Context, url: str) -> None:
    await song_queue.append(url)

    await ctx.send(song_queue.get_queue_report())

@add_song.error
async def on_add_song_error(_, error: Exception):
    _log_error(error, "on_add_song_error")

@bot.command(name = 'pause', help='Pauses the song currently playing if there is one')
async def pause(ctx: commands.Context) -> None:
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name = "queue", help="Display the current queue of songs up the visible queue limit")
async def queue(ctx: commands.Context) -> None:
    await ctx.send(song_queue.get_queue_report())

@bot.command(name = "skip", help = "Skip the current song and begin playing the next song in the queue")
async def skip(ctx: commands.Context) -> None:
    if len(song_queue) > 1:
        await ctx.send("Skipping " + song_queue.current_song["title"])

        if ctx.message.guild.voice_client.is_playing():
            song_queue.remove(0)
            await play(ctx)
        else:
            song_queue.pop()
    else:
        await ctx.send("There's nothing in the queue to skip.")
    
@bot.command(name = "join_lobby", help = """
             Join the server LFG 'lobby'. LFG lobbies are just a way to indicate to other folks that you're looking
             to join a call or play something without having to just sit in call. When somebody joins the lobby while you're
             in it, the bot will ping you to let you know.
             """)
async def join_lobby(ctx: commands.Context) -> None:
    out_lobby_role = ctx.guild.get_role(OUT_LOBBY_ROLE_ID)
    in_lobby_role = ctx.guild.get_role(IN_LOBBY_ROLE_ID)

    if in_lobby_role:
        await ctx.send("You're already in the lobby.")
        return
    
    await ctx.author.remove_roles(out_lobby_role)
    await ctx.author.add_roles(in_lobby_role)

    await ctx.send(f"{ctx.author.mention} has joined the lobby! <@{IN_LOBBY_ROLE_ID}>")

@join_lobby.error
async def on_join_lobby_error(_, err: Exception) -> None:
    _log_error(err, "_on_join_lobby_error")

@bot.command(name = "leave_lobby", help = """
            Leave the server LFG 'lobby'. LFG lobbies are just a way to indicate to other folks that you're looking
            to join a call or play something without having to just sit in call.
            """)
async def leave_lobby(ctx: commands.Context) -> None:
    in_lobby_role = ctx.guild.get_role(IN_LOBBY_ROLE_ID)
    out_lobby_role = ctx.guild.get_role(OUT_LOBBY_ROLE_ID)

    if out_lobby_role:
        await ctx.send(f"{ctx.author.mention} is not in the lobby.")
        return

    await ctx.author.remove_roles(in_lobby_role)
    await ctx.author.add_roles(out_lobby_role)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)