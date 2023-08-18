import asyncio
from queue import Queue
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

# Get the API token from the .env file
DISCORD_TOKEN = os.getenv("discord_token")
COMMAND_PREFIX = os.getenv("command_prefix")
VISIBLE_QUEUE_LENGTH = os.getenv("visible_queue_length")


# Setting the intents. These should match the intents on the Discord Developer Portal
intents = discord.Intents.all()


# Connecting to an individual client of Chocobot
client = discord.Client(intents = intents)
# Creates a reference to our new Chocobot client
bot = commands.Bot(command_prefix = COMMAND_PREFIX, intents = intents)

# ytdl configuration
yt_dlp.utils.bug_reports_message = lambda: 'There was an error!'
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

# ffmpeg configuration
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
            # take first item from a playlist
            data = data["entries"][0]
        return data

class RadioQueue(list):
    current_song: YTDLSource

    def __init__(self):
        super().__init__(self)

    async def append(self, url: str):
        super().append(await YTDLSource.from_url(url))
        self.current_song = self[len(self) - 1]

    def get_queue_report(self):
        newline = "\n"

        return f"""
            -> Now playing: {self[0]['title']} <-

            {newline.join([f"{i + 1}: {self[i]['title']}" for i in range(len(self)) if i > 0])}
        """

song_queue = RadioQueue()

# ctx in all of these methods refers to the command context. https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.Context
@bot.command(name = 'join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.message.author.name} is not connected to a voice channel')
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name = 'leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send('The bot is not connected to a voice channel.')

@bot.command(name = 'play', help = 'To play a new song, paused song, or paused queue')
async def play(ctx, url = None):
        voice_client = ctx.message.guild.voice_client

        # Add the current song to the queue if a song url was provided
        if url is not None:
            song_queue.append(url)
        
        # Start the queue if it's not already playing
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
async def play_error(ctx, error):
    if not ctx.message.guild.voice_client:
        await ctx.send(f"The bot is not connected to a voice channel. Use {COMMAND_PREFIX}join to invite the bot to a channel and try again!")

@bot.command(name = 'add_song', help = 'To add a song to the front of the queue')
async def add_song(ctx, url):
    await song_queue.append(url)

    await ctx.send(song_queue.get_queue_report())

@bot.command(name = 'pause', help='Pauses the song currently playing if there is one')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name = "queue", help="Display the current queue of songs up the visible queue limit")
async def queue(ctx):
    await ctx.send(song_queue.get_queue_report())


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)