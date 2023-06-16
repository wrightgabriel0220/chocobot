import asyncio
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import youtube_dl
import yt_dlp

load_dotenv()

# Get the API token from the .env file
DISCORD_TOKEN = os.getenv("discord_token")
COMMAND_PREFIX = os.getenv("command_prefix")


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
    'logtostderr': False,
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
        print(f'url: {url}')
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download = not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename
    
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
        await ctx.send('The bot is connected to a voice channel.')


@bot.command(name = 'play_song', help='!play [song-url] - plays a single song given a valid Youtube URL')
async def play(ctx, url):
    try:
        server = ctx.message.guild
        print("server: ", server)
        voice_channel = server.voice_client

        async with ctx.typing():
            filename = await YTDLSource.from_url(url, loop = bot.loop)
            voice_channel.play(discord.FFmpegPCMAudio(executable = "ffmpeg.exe", source = filename, options = ffmpeg_options))
        await ctx.send(f'**Now playing:** {filename}')
    except (RuntimeError, TypeError, NameError):
        print(f"The bot is not connected to a voice channel. RuntimeError: {RuntimeError | 'N/A'} - TypeError: {TypeError | 'N/A'} - NameError: {NameError | 'N/A'}")


@bot.command(name = 'pause', help='Pauses the song currently playing if there is one')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)