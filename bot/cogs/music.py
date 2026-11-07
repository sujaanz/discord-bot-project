import os
import asyncio
import random
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
from bot.utils.music_card import create_music_player_card

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'False', 'quiet': True}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)

class SafeVoiceClient(discord.VoiceClient):
    """Bypasses PyNaCl/Davey checks completely for modern Python environments."""
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        super().__init__(client, channel)

    async def connect_to(self, address: str, *, reconnect: bool = False):
        await super().connect_to(address, reconnect=reconnect)


class YTDLSource(discord.AudioSource):
    def __init__(self, source, *, data, volume=0.5):
        self.source = discord.PCMVolumeTransformer(source, volume=volume)
        self.data = data
        self.title = data.get('title', 'Unknown Title')
        self.url = data.get('url', '')
        self.artist = data.get('uploader', 'Unknown Artist')
        self.duration = data.get('duration_string', 'Live')
        self.thumbnail = data.get('thumbnail')

    def read(self):
        return self.source.read()

    def cleanup(self):
        self.source.cleanup()

    @property
    def volume(self):
        return self.source.volume

    @volume.setter
    def volume(self, value):
        self.source.volume = value

    @classmethod
    async def create_source(cls, search: str, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        is_url = search.startswith("http://") or search.startswith("https://")
        query = search if is_url else f"ytsearch:{search}"
        
        to_run = lambda: ytdl.extract_info(query, download=False)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url']
        audio_source = discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS)
        return cls(audio_source, data=data)


class MusicControlView(discord.ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="Pause/Resume", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Music playback paused.", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Music playback resumed.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped current track successfully.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop_track(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            state = self.cog.get_guild_state(self.guild_id)
            state["queue"] = []
            state["loop"] = "OFF"
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Music stopped and bot disconnected.", ephemeral=True)

    @discord.ui.button(label="Loop", style=discord.ButtonStyle.success, emoji="🔁")
    async def toggle_loop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = self.cog.get_guild_state(self.guild_id)
        if state["loop"] == "OFF":
            state["loop"] = "TRACK"
            await interaction.response.send_message("🔁 Loop mode set to **TRACK**.", ephemeral=True)
        elif state["loop"] == "TRACK":
            state["loop"] = "QUEUE"
            await interaction.response.send_message("🔁 Loop mode set to **QUEUE**.", ephemeral=True)
        else:
            state["loop"] = "OFF"
            await interaction.response.send_message("🔁 Loop mode turned **OFF**.", ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild_states = {}

    def get_guild_state(self, guild_id: int):
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = {
                "queue": [],
                "current": None,
                "loop": "OFF",
                "volume": 50,
                "history": []
            }
        return self.guild_states[guild_id]

    async def play_next(self, ctx_or_interaction, guild: discord.Guild):
        state = self.get_guild_state(guild.id)
        vc = guild.voice_client

        if not vc or not vc.is_connected():
            return

        if state["loop"] == "TRACK" and state["current"]:
            player = state["current"]
        elif len(state["queue"]) > 0:
            player = state["queue"].pop(0)
            if state["loop"] == "QUEUE":
                state["queue"].append(state["current"])
            state["current"] = player
            state["history"].insert(0, player)
            if len(state["history"]) > 10:
                state["history"].pop()
        else:
            state["current"] = None
            return

        def after_playing(error):
            if error:
                print(f"Player error: {error}")
            fut = asyncio.run_coroutine_threadsafe(self.play_next(None, guild), self.bot.loop)
            try:
                fut.result()
            except Exception:
                pass

        vc.play(player, after=after_playing)
        player.volume = state["volume"] / 100.0

        card_path = create_music_player_card(
            title=player.title,
            artist=player.artist,
            duration=player.duration,
            requester=str(guild.me.display_name),
            thumbnail_url=player.thumbnail,
            status="NOW PLAYING",
            volume=state["volume"],
            loop_mode=state["loop"]
        )

        view = MusicControlView(self, guild.id)
        if card_path and os.path.exists(card_path):
            file = discord.File(card_path, filename="music.png")
            try:
                if ctx_or_interaction and hasattr(ctx_or_interaction, 'channel'):
                    await ctx_or_interaction.channel.send(file=file, view=view)
                elif ctx_or_interaction and hasattr(ctx_or_interaction, 'followup'):
                    await ctx_or_interaction.followup.send(file=file, view=view)
                os.remove(card_path)
            except Exception:
                pass

    @app_commands.command(name="play", description="Play a song or playlist from YouTube with a visual card.")
    @app_commands.describe(query="Song name or YouTube URL")
    async def play_slash(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ You need to join a voice channel first!", ephemeral=True)
            return

        await interaction.response.defer()

        voice_channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client

        if not vc:
            try:
                vc = await voice_channel.connect(cls=SafeVoiceClient)
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to connect to voice channel: {e}")
                return
        elif vc.channel != voice_channel:
            await vc.move_to(voice_channel)

        try:
            player = await YTDLSource.create_source(query, loop=self.bot.loop)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to load audio source: {e}")
            return

        state = self.get_guild_state(interaction.guild_id)
        state["queue"].append(player)

        if not vc.is_playing() and not vc.is_paused():
            await self.play_next(interaction, interaction.guild)
        else:
            card_path = create_music_player_card(
                title=player.title,
                artist=player.artist,
                duration=player.duration,
                requester=interaction.user.display_name,
                thumbnail_url=player.thumbnail,
                status="ADDED TO QUEUE",
                volume=state["volume"],
                loop_mode=state["loop"]
            )
            if card_path and os.path.exists(card_path):
                file = discord.File(card_path, filename="queue.png")
                await interaction.followup.send(file=file)
                os.remove(card_path)

    @app_commands.command(name="skip", description="Skip the currently playing track.")
    async def skip_slash(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped current track successfully.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing right now.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop music, clear queue and disconnect bot.")
    async def stop_slash(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            state = self.get_guild_state(interaction.guild_id)
            state["queue"] = []
            state["loop"] = "OFF"
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Music stopped and bot disconnected.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot is not connected to any voice channel.", ephemeral=True)

    @app_commands.command(name="pause", description="Pause the current song.")
    async def pause_slash(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Music playback paused.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No music is currently playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume the paused song.")
    async def resume_slash(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Music playback resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Music is not paused.", ephemeral=True)

    @app_commands.command(name="volume", description="Adjust the music player volume (0 - 100).")
    @app_commands.describe(volume="Volume level from 0 to 100")
    async def volume_slash(self, interaction: discord.Interaction, volume: int):
        if not 0 <= volume <= 100:
            await interaction.response.send_message("❌ Volume must be between 0 and 100.", ephemeral=True)
            return
        state = self.get_guild_state(interaction.guild_id)
        state["volume"] = volume
        vc = interaction.guild.voice_client
        if vc and vc.source:
            vc.source.volume = volume / 100.0
        await interaction.response.send_message(f"🔊 Volume adjusted to **{volume}%**.", ephemeral=True)

    @app_commands.command(name="queue", description="View the current song playback queue.")
    async def queue_slash(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        if not state["current"] and not state["queue"]:
            await interaction.response.send_message("📭 The music queue is currently empty.", ephemeral=True)
            return

        lines = []
        if state["current"]:
            lines.append(f"▶️ **Now Playing:** {state['current'].title} (`{state['current'].duration}`)")
        
        for idx, song in enumerate(state["queue"][:10], start=1):
            lines.append(f"`#{idx}` {song.title} (`{song.duration}`)")

        embed = discord.Embed(
            title=f"🎶 {interaction.guild.name} — Music Queue",
            description="\n".join(lines),
            color=discord.Color.from_rgb(244, 63, 94)
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show details of the currently playing song.")
    async def nowplaying_slash(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        if not state["current"]:
            await interaction.response.send_message("❌ Nothing is playing right now.", ephemeral=True)
            return
        
        player = state["current"]
        card_path = create_music_player_card(
            title=player.title,
            artist=player.artist,
            duration=player.duration,
            requester=interaction.user.display_name,
            thumbnail_url=player.thumbnail,
            status="NOW PLAYING",
            volume=state["volume"],
            loop_mode=state["loop"]
        )
        if card_path and os.path.exists(card_path):
            file = discord.File(card_path, filename="np.png")
            await interaction.response.send_message(file=file)
            os.remove(card_path)

    @app_commands.command(name="loop", description="Toggle loop mode: OFF, TRACK, or QUEUE.")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value="OFF"),
        app_commands.Choice(name="Current Track", value="TRACK"),
        app_commands.Choice(name="Full Queue", value="QUEUE")
    ])
    async def loop_slash(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        state = self.get_guild_state(interaction.guild_id)
        state["loop"] = mode.value
        await interaction.response.send_message(f"🔁 Loop mode updated to: **{mode.name}**", ephemeral=True)

    @app_commands.command(name="shuffle", description="Randomize the order of songs in the queue.")
    async def shuffle_slash(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        if len(state["queue"]) < 2:
            await interaction.response.send_message("❌ Not enough songs in queue to shuffle.", ephemeral=True)
            return
        random.shuffle(state["queue"])
        await interaction.response.send_message("🔀 Music queue has been shuffled successfully!", ephemeral=True)

    @app_commands.command(name="history", description="View recently played tracks history.")
    async def history_slash(self, interaction: discord.Interaction):
        state = self.get_guild_state(interaction.guild_id)
        if not state["history"]:
            await interaction.response.send_message("📭 No song history available yet.", ephemeral=True)
            return

        lines = [f"`{idx}.` {song.title} (`{song.duration}`)" for idx, song in enumerate(state["history"][:10], start=1)]
        embed = discord.Embed(
            title="📜 Recently Played History",
            description="\n".join(lines),
            color=discord.Color.from_rgb(56, 189, 248)
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))