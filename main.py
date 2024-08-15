import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import youtube_dl

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Set up the bot with the command prefix !
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Set up the youtube_dl options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'noplaylist': True,
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or bot.loop
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}.')


@bot.command(name='play', help='Plays audio from a given URL.')
async def play(ctx, url):
    if not ctx.message.author.voice:
        await ctx.send(f'{ctx.message.author.name}, you are not connected to a voice channel.')
        return

    channel = ctx.message.author.voice.channel

    if ctx.voice_client is None:
        await channel.connect()

    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    await ctx.send(f'Now playing: {player.title}')


@bot.command(name='stop', help='Stops the audio and leaves the voice channel.')
async def stop(ctx):
    await ctx.voice_client.disconnect()


bot.run(TOKEN)
