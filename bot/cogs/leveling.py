import os
import json
import time
import random
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from bot.utils.card_generator import (
    create_rank_card,
    create_leaderboard_card,
    create_stats_card,
    create_banner_card,
    THEMES,
    TEMPLATES
)

DATA_FILE = "bot/data/levels_v3.json"


class CardCustomizationView(discord.ui.View):
    """Interactive Discord Studio for customizing Template, Theme, Avatar Shape & Blur live."""
    def __init__(self, cog, user_id: int):
        super().__init__(timeout=240)
        self.cog = cog
        self.user_id = user_id

    async def check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This customization studio belongs to another member.", ephemeral=True)
            return False
        return True

    async def refresh_preview(self, interaction: discord.Interaction, status_text: str):
        await interaction.response.defer()
        self.cog.save_data()
        path = await asyncio.to_thread(self.cog.generate_member_card, interaction.guild, interaction.user)
        if path and os.path.exists(path):
            file = discord.File(path, filename="rank_preview.png")
            await interaction.edit_original_response(content=status_text, attachments=[file], view=self)
            os.remove(path)

    @discord.ui.select(
        placeholder="1. Choose Rank Card Template & Size (6 Unique Layouts)...",
        min_values=1,
        max_values=1,
        row=0,
        options=[
            discord.SelectOption(label="Bento Pro Grid (1100x360)", value="bento", description="Classic multi-box Bento layout with dual ring"),
            discord.SelectOption(label="Cyberpunk Hex HUD (1120x340)", value="cyber", description="Right Hexagon avatar, slanted HUD & triangle cuts"),
            discord.SelectOption(label="Triangle Prism Split (1060x370)", value="prism", description="Diagonal triangle split with Diamond avatar"),
            discord.SelectOption(label="Compact Square Box (800x470)", value="square", description="Square card with top banner & 20-block XP bar"),
            discord.SelectOption(label="Ultra-Wide Strip (1200x250)", value="banner", description="Sleek cinematic horizontal banner with watermark"),
            discord.SelectOption(label="Executive Ring Gauge (1080x360)", value="exec", description="Luxury layout with Circular XP Ring Meter")
        ]
    )
    async def select_template(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not await self.check_owner(interaction):
            return
        udata = self.cog.get_user_data(interaction.guild.id, interaction.user.id)
        udata["card_style"] = select.values[0]
        await self.refresh_preview(interaction, f"Template updated to **{TEMPLATES.get(select.values[0])}**!")

    @discord.ui.select(
        placeholder="2. Choose Color Theme (8 Neon & Luxury Palettes)...",
        min_values=1,
        max_values=1,
        row=1,
        options=[
            discord.SelectOption(label="Crimson Rose (Red)", value="crimson"),
            discord.SelectOption(label="Cyber Violet (Purple)", value="neon_violet"),
            discord.SelectOption(label="Emerald Matrix (Green)", value="emerald"),
            discord.SelectOption(label="Royal Gold (Gold)", value="gold"),
            discord.SelectOption(label="Electric Ocean (Blue)", value="ocean"),
            discord.SelectOption(label="Sunset Blaze (Orange)", value="sunset"),
            discord.SelectOption(label="Tokyo Neon (Pink)", value="cyber_pink"),
            discord.SelectOption(label="Arctic Frost (Cyan)", value="ice_cyan")
        ]
    )
    async def select_theme(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not await self.check_owner(interaction):
            return
        udata = self.cog.get_user_data(interaction.guild.id, interaction.user.id)
        udata["custom_theme"] = select.values[0]
        await self.refresh_preview(interaction, f"Color theme updated to **{THEMES[select.values[0]]['name']}**!")

    @discord.ui.select(
        placeholder="3. Choose Avatar Geometric Shape...",
        min_values=1,
        max_values=1,
        row=2,
        options=[
            discord.SelectOption(label="Auto (Match Template Default)", value="auto"),
            discord.SelectOption(label="Circle (Dual Gradient Ring)", value="circle"),
            discord.SelectOption(label="Hexagon (Cyber Polygon)", value="hexagon"),
            discord.SelectOption(label="Diamond (Prism Rhombus)", value="diamond"),
            discord.SelectOption(label="Square (Sharp Brutalist)", value="square"),
            discord.SelectOption(label="Rounded Squircle", value="rounded")
        ]
    )
    async def select_avatar_shape(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not await self.check_owner(interaction):
            return
        udata = self.cog.get_user_data(interaction.guild.id, interaction.user.id)
        udata["avatar_shape"] = select.values[0]
        await self.refresh_preview(interaction, f"Avatar shape set to **{select.values[0].upper()}**!")

    @discord.ui.button(label="Toggle BG Blur (Sharp/Soft)", style=discord.ButtonStyle.secondary, row=3)
    async def toggle_blur(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_owner(interaction):
            return
        udata = self.cog.get_user_data(interaction.guild.id, interaction.user.id)
        cur = udata.get("bg_blur", 3)
        udata["bg_blur"] = 0 if cur > 0 else 4
        mode = "Sharp (0 Blur)" if udata["bg_blur"] == 0 else "Soft Glass Blur"
        await self.refresh_preview(interaction, f"Background image mode set to **{mode}**!")

    @discord.ui.button(label="Reset Customizations", style=discord.ButtonStyle.danger, row=3)
    async def reset_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.check_owner(interaction):
            return
        udata = self.cog.get_user_data(interaction.guild.id, interaction.user.id)
        udata["card_style"] = "bento"
        udata["custom_theme"] = None
        udata["custom_bg"] = None
        udata["avatar_shape"] = "auto"
        udata["bg_blur"] = 3
        await self.refresh_preview(interaction, "All card customizations have been reset to server defaults!")


class LeaderboardView(discord.ui.View):
    def __init__(self, cog, guild: discord.Guild):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild = guild
        self.sort_by = "xp"
        self.page = 0

    def generate_card(self) -> str:
        gdata = self.cog.get_guild_data(self.guild.id)
        users = gdata["users"]

        if self.sort_by == "voice":
            sorted_list = sorted(users.items(), key=lambda x: x[1].get("voice_minutes", 0), reverse=True)
            mode_title = "Top Voice Activity"
        elif self.sort_by == "messages":
            sorted_list = sorted(users.items(), key=lambda x: x[1].get("messages", 0), reverse=True)
            mode_title = "Top Chatters"
        else:
            sorted_list = sorted(
                users.items(),
                key=lambda x: (x[1].get("prestige", 0), x[1].get("level", 0), x[1].get("xp", 0)),
                reverse=True
            )
            mode_title = "Top Level & XP"

        per_page = 6
        max_pages = max(1, (len(sorted_list) + per_page - 1) // per_page)
        self.page = max(0, min(self.page, max_pages - 1))

        start = self.page * per_page
        chunk = sorted_list[start:start + per_page]

        entries = []
        for idx, (uid, u) in enumerate(chunk, start=start + 1):
            member = self.guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid[:6]}"
            lvl = u.get("level", 0)
            entries.append({
                "rank": idx,
                "name": name,
                "level": lvl,
                "xp": u.get("xp", 0),
                "max_xp": self.cog.get_max_xp(lvl),
                "messages": u.get("messages", 0),
                "voice": u.get("voice_minutes", 0),
                "prestige": u.get("prestige", 0)
            })

        return create_leaderboard_card(
            guild_name=self.guild.name,
            mode_title=mode_title,
            entries=entries,
            page=self.page + 1,
            max_pages=max_pages,
            multiplier=float(gdata.get("multiplier", 1.0)),
            theme_name=gdata.get("theme", "crimson"),
            bg_url=gdata.get("bg_url")
        )

    async def update_card_message(self, interaction: discord.Interaction):
        await interaction.response.defer()
        card_path = await asyncio.to_thread(self.generate_card)
        if card_path and os.path.exists(card_path):
            file = discord.File(card_path, filename="leaderboard.png")
            await interaction.edit_original_response(attachments=[file], view=self)
            os.remove(card_path)

    @discord.ui.button(label="Top XP", style=discord.ButtonStyle.danger)
    async def sort_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_by = "xp"
        self.page = 0
        await self.update_card_message(interaction)

    @discord.ui.button(label="Top Messages", style=discord.ButtonStyle.secondary)
    async def sort_msgs(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_by = "messages"
        self.page = 0
        await self.update_card_message(interaction)

    @discord.ui.button(label="Top Voice", style=discord.ButtonStyle.secondary)
    async def sort_voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_by = "voice"
        self.page = 0
        await self.update_card_message(interaction)

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await self.update_card_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await self.update_card_message(interaction)


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.text_cooldowns = {}
        self.voice_join_times = {}
        self.data = {"guilds": {}}
        self.last_mtime = 0.0
        self.load_data()

    def sync_from_disk_if_modified(self):
        """Ensures changes made via the Website Dashboard are immediately loaded into the bot."""
        if os.path.exists(DATA_FILE):
            try:
                mtime = os.path.getmtime(DATA_FILE)
                if mtime > self.last_mtime:
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict) and "guilds" in loaded:
                            self.data = loaded
                            self.last_mtime = mtime
            except Exception:
                pass

    def load_data(self):
        os.makedirs("bot/data", exist_ok=True)
        if os.path.exists(DATA_FILE):
            self.sync_from_disk_if_modified()
        else:
            self.save_data()

    def save_data(self):
        os.makedirs("bot/data", exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
        if os.path.exists(DATA_FILE):
            self.last_mtime = os.path.getmtime(DATA_FILE)

    def get_guild_data(self, guild_id: int) -> dict:
        self.sync_from_disk_if_modified()
        gid = str(guild_id)
        if gid not in self.data["guilds"]:
            self.data["guilds"][gid] = {
                "name": "",
                "theme": "crimson",
                "bg_url": None,
                "multiplier": 1.0,
                "level_channel": None,
                "ignored_channels": [],
                "role_rewards": {},
                "users": {}
            }
        return self.data["guilds"][gid]

    def get_user_data(self, guild_id: int, user_id: int, member_name: str = None) -> dict:
        gdata = self.get_guild_data(guild_id)
        uid = str(user_id)
        defaults = {
            "name": member_name or f"User {uid[:6]}",
            "xp": 0,
            "level": 0,
            "total_xp": 0,
            "messages": 0,
            "voice_minutes": 0,
            "streak": 0,
            "last_daily": 0,
            "prestige": 0,
            "bio": "Active Server Member",
            "custom_theme": None,
            "custom_bg": None,
            "card_style": "bento",
            "avatar_shape": "auto",
            "bg_blur": 3,
            "bg_dim": 190
        }
        if uid not in gdata["users"]:
            gdata["users"][uid] = defaults
            self.save_data()
        else:
            for k, v in defaults.items():
                if k not in gdata["users"][uid]:
                    gdata["users"][uid][k] = v
            if member_name:
                gdata["users"][uid]["name"] = member_name
        return gdata["users"][uid]

    @staticmethod
    def get_max_xp(level: int) -> int:
        return 100 + (level * 150)

    def calculate_rank(self, guild_id: int, user_id: int) -> int:
        gdata = self.get_guild_data(guild_id)
        users = gdata["users"]
        uid = str(user_id)
        if uid not in users:
            return len(users) + 1
        sorted_uids = sorted(
            users.keys(),
            key=lambda u: (
                users[u].get("prestige", 0),
                users[u].get("level", 0),
                users[u].get("xp", 0),
                users[u].get("total_xp", 0)
            ),
            reverse=True
        )
        return sorted_uids.index(uid) + 1

    async def send_card_interaction(
        self,
        interaction: discord.Interaction,
        card_path: str,
        filename: str = "card.png",
        content: str = None,
        view: discord.ui.View = None,
        ephemeral: bool = False
    ):
        if card_path and os.path.exists(card_path):
            file = discord.File(card_path, filename=filename)
            kwargs = {"file": file, "ephemeral": ephemeral}
            if content is not None:
                kwargs["content"] = content
            if view is not None:
                kwargs["view"] = view

            if interaction.response.is_done():
                await interaction.followup.send(**kwargs)
            else:
                await interaction.response.send_message(**kwargs)
            try:
                os.remove(card_path)
            except Exception:
                pass
        else:
            msg = "Failed to generate visual card."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    async def check_and_apply_levelup(self, guild: discord.Guild, member: discord.Member, channel: discord.abc.Messageable, udata: dict):
        gdata = self.get_guild_data(guild.id)
        leveled_up = False

        while udata["xp"] >= self.get_max_xp(udata["level"]):
            udata["xp"] -= self.get_max_xp(udata["level"])
            udata["level"] += 1
            leveled_up = True

        if leveled_up:
            unlocked_role_name = "None"
            rewards = gdata.get("role_rewards", {})
            for req_lvl_str, role_id in rewards.items():
                if udata["level"] >= int(req_lvl_str):
                    role = guild.get_role(int(role_id))
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role, reason=f"Reached Level {udata['level']}")
                            unlocked_role_name = role.name
                        except Exception:
                            pass

            target_chan = channel
            if gdata.get("level_channel"):
                custom_ch = guild.get_channel(int(gdata["level_channel"]))
                if custom_ch:
                    target_chan = custom_ch

            if target_chan:
                try:
                    theme = udata.get("custom_theme") or gdata.get("theme", "crimson")
                    bg = udata.get("custom_bg") or gdata.get("bg_url")
                    rank_pos = self.calculate_rank(guild.id, member.id)
                    card_path = await asyncio.to_thread(
                        create_banner_card,
                        title="LEVEL UP ACHIEVED!",
                        subtitle=f"{member.display_name} just advanced to a higher level!",
                        highlights=[
                            ("NEW LEVEL", f"LEVEL {udata['level']}"),
                            ("SERVER RANK", f"#{rank_pos}"),
                            ("ROLE UNLOCKED", unlocked_role_name[:16])
                        ],
                        footer=f"{guild.name} • Keep chatting to unlock more rewards",
                        avatar_url=str(member.display_avatar.url),
                        theme_name=theme,
                        bg_url=bg
                    )
                    if card_path and os.path.exists(card_path):
                        await target_chan.send(
                            content=f"GG {member.mention}!",
                            file=discord.File(card_path, filename="levelup.png")
                        )
                        os.remove(card_path)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(("!", "/")):
            return

        gdata = self.get_guild_data(message.guild.id)
        gdata["name"] = message.guild.name
        if message.channel.id in gdata.get("ignored_channels", []):
            return

        key = f"{message.guild.id}_{message.author.id}"
        now = time.time()
        if key in self.text_cooldowns and now - self.text_cooldowns[key] < 5:
            return
        self.text_cooldowns[key] = now

        udata = self.get_user_data(message.guild.id, message.author.id, message.author.display_name)
        udata["messages"] += 1

        mult = float(gdata.get("multiplier", 1.0)) + (udata.get("prestige", 0) * 0.1)
        xp_gain = int(random.randint(15, 25) * mult)

        udata["xp"] += xp_gain
        udata["total_xp"] += xp_gain

        await self.check_and_apply_levelup(message.guild, message.author, message.channel, udata)
        self.save_data()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or not member.guild:
            return
        key = f"{member.guild.id}_{member.id}"
        now = time.time()

        if before.channel is None and after.channel is not None:
            self.voice_join_times[key] = now
        elif before.channel is not None and after.channel is None:
            if key in self.voice_join_times:
                joined_at = self.voice_join_times.pop(key)
                minutes = int((now - joined_at) // 60)
                if minutes > 0:
                    udata = self.get_user_data(member.guild.id, member.id, member.display_name)
                    udata["voice_minutes"] = udata.get("voice_minutes", 0) + minutes
                    voice_xp = minutes * 10
                    udata["xp"] += voice_xp
                    udata["total_xp"] += voice_xp
                    await self.check_and_apply_levelup(member.guild, member, None, udata)
                    self.save_data()

    def generate_member_card(self, guild: discord.Guild, member: discord.Member) -> str:
        gdata = self.get_guild_data(guild.id)
        gdata["name"] = guild.name
        udata = self.get_user_data(guild.id, member.id, member.display_name)
        rank_pos = self.calculate_rank(guild.id, member.id)
        max_xp = self.get_max_xp(udata.get("level", 0))

        theme = udata.get("custom_theme") or gdata.get("theme", "crimson")
        bg_url = udata.get("custom_bg") or gdata.get("bg_url")
        card_style = udata.get("card_style") or "bento"
        avatar_shape = udata.get("avatar_shape") or "auto"
        bg_blur = int(udata.get("bg_blur", 3))
        bg_dim = int(udata.get("bg_dim", 190))

        status_str = str(getattr(member, "status", "online"))
        if status_str == "offline":
            status_str = "online"

        return create_rank_card(
            display_name=member.display_name,
            username=member.name,
            level=udata.get("level", 0),
            current_xp=udata.get("xp", 0),
            max_xp=max_xp,
            rank_pos=rank_pos,
            total_xp=udata.get("total_xp", 0),
            messages_count=udata.get("messages", 0),
            voice_minutes=udata.get("voice_minutes", 0),
            streak=udata.get("streak", 0),
            prestige=udata.get("prestige", 0),
            bio=udata.get("bio", "Active Server Member"),
            avatar_url=str(member.display_avatar.url),
            status=status_str,
            bg_url=bg_url,
            theme_name=theme,
            card_style=card_style,
            avatar_shape=avatar_shape,
            bg_blur=bg_blur,
            bg_dim=bg_dim
        )

    # 1. /rank & !rank
    @commands.command(name="rank", help="View your Multi-Style Rank Card.")
    async def rank_prefix(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        path = await asyncio.to_thread(self.generate_member_card, ctx.guild, target)
        if path and os.path.exists(path):
            await ctx.send(file=discord.File(path, filename="rank.png"))
            os.remove(path)

    @app_commands.command(name="rank", description="View your or another member's Custom Rank Card.")
    @app_commands.describe(member="Select a member to check their rank card")
    async def rank_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        await interaction.response.defer()
        try:
            path = await asyncio.to_thread(self.generate_member_card, interaction.guild, target)
            await self.send_card_interaction(interaction, path, "rank.png")
        except Exception as e:
            await interaction.followup.send(f"Error generating rank card: `{e}`", ephemeral=True)

    # 2. /leaderboard & !lb
    @commands.command(name="leaderboard", aliases=["lb", "top"], help="View the graphical server leaderboard.")
    async def lb_prefix(self, ctx: commands.Context):
        view = LeaderboardView(self, ctx.guild)
        path = await asyncio.to_thread(view.generate_card)
        if path and os.path.exists(path):
            await ctx.send(file=discord.File(path, filename="leaderboard.png"), view=view)
            os.remove(path)

    @app_commands.command(name="leaderboard", description="View the interactive graphical server leaderboard.")
    async def lb_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = LeaderboardView(self, interaction.guild)
        path = await asyncio.to_thread(view.generate_card)
        await self.send_card_interaction(interaction, path, "leaderboard.png", view=view)

    # 3. /daily
    @app_commands.command(name="daily", description="Claim your daily bonus XP card and build your daily streak!")
    async def daily_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        udata = self.get_user_data(interaction.guild.id, interaction.user.id, interaction.user.display_name)
        theme = udata.get("custom_theme") or gdata.get("theme", "crimson")
        bg = udata.get("custom_bg") or gdata.get("bg_url")

        now = time.time()
        elapsed = now - udata.get("last_daily", 0)

        if elapsed < 86400:
            rem = int(86400 - elapsed)
            hours, rem = divmod(rem, 3600)
            mins = rem // 60
            card_path = await asyncio.to_thread(
                create_banner_card,
                title="DAILY REWARD COOLDOWN",
                subtitle=f"You have already claimed your daily bonus today, {interaction.user.display_name}!",
                highlights=[
                    ("NEXT CLAIM IN", f"{hours}h {mins}m"),
                    ("CURRENT STREAK", f"{udata.get('streak', 0)} DAYS"),
                    ("CURRENT LEVEL", f"LEVEL {udata['level']}")
                ],
                footer="Come back tomorrow to keep your streak alive",
                avatar_url=str(interaction.user.display_avatar.url),
                theme_name=theme,
                bg_url=bg
            )
            await self.send_card_interaction(interaction, card_path, "daily_cooldown.png")
            return

        if elapsed < 172800:
            udata["streak"] = udata.get("streak", 0) + 1
        else:
            udata["streak"] = 1

        bonus_xp = 50 + min(udata["streak"] * 15, 150)
        udata["last_daily"] = now
        udata["xp"] += bonus_xp
        udata["total_xp"] += bonus_xp

        await self.check_and_apply_levelup(interaction.guild, interaction.user, interaction.channel, udata)
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="DAILY BONUS CLAIMED!",
            subtitle=f"{interaction.user.display_name} claimed today's daily activity reward!",
            highlights=[
                ("XP EARNED", f"+{bonus_xp} XP"),
                ("ACTIVE STREAK", f"{udata['streak']} DAYS"),
                ("TOTAL XP", f"{udata['total_xp']} XP")
            ],
            footer="Claim every 24 hours to increase your streak bonus",
            avatar_url=str(interaction.user.display_avatar.url),
            theme_name=theme,
            bg_url=bg
        )
        await self.send_card_interaction(interaction, card_path, "daily.png")

    # 4. /prestige
    @app_commands.command(name="prestige", description="Ascend to the next Prestige tier (Requires Level 10+).")
    async def prestige_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        udata = self.get_user_data(interaction.guild.id, interaction.user.id, interaction.user.display_name)
        theme = udata.get("custom_theme") or gdata.get("theme", "crimson")
        bg = udata.get("custom_bg") or gdata.get("bg_url")

        if udata["level"] < 10:
            card_path = await asyncio.to_thread(
                create_banner_card,
                title="PRESTIGE LOCKED",
                subtitle="You must reach at least Level 10 before ascending to Prestige!",
                highlights=[
                    ("YOUR LEVEL", f"LEVEL {udata['level']}"),
                    ("REQUIRED", "LEVEL 10"),
                    ("CURRENT TIER", f"PRESTIGE {udata.get('prestige', 0)}")
                ],
                footer="Keep chatting and earning XP to unlock Prestige",
                avatar_url=str(interaction.user.display_avatar.url),
                theme_name=theme,
                bg_url=bg
            )
            await self.send_card_interaction(interaction, card_path, "prestige_locked.png")
            return

        udata["prestige"] = udata.get("prestige", 0) + 1
        udata["level"] = 0
        udata["xp"] = 0
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="PRESTIGE ASCENSION!",
            subtitle=f"{interaction.user.display_name} ascended to Prestige Tier {udata['prestige']}!",
            highlights=[
                ("NEW TIER", f"PRESTIGE {udata['prestige']}"),
                ("PERMANENT BOOST", f"+{udata['prestige'] * 10}% XP"),
                ("LEVEL RESET", "LEVEL 0")
            ],
            footer="Enjoy your permanent XP multiplier and profile badge",
            avatar_url=str(interaction.user.display_avatar.url),
            theme_name="gold",
            bg_url=bg
        )
        await self.send_card_interaction(interaction, card_path, "prestige.png")

    # 5. /mycard (Full Interactive Studio + Direct Parameters)
    @app_commands.command(name="mycard", description="Open the interactive Rank Card Studio or set your template, theme, shape, bio & background!")
    @app_commands.choices(
        theme=[
            app_commands.Choice(name="Crimson Rose (Red)", value="crimson"),
            app_commands.Choice(name="Cyber Violet (Purple)", value="neon_violet"),
            app_commands.Choice(name="Emerald Matrix (Green)", value="emerald"),
            app_commands.Choice(name="Royal Gold (Gold)", value="gold"),
            app_commands.Choice(name="Electric Ocean (Blue)", value="ocean"),
            app_commands.Choice(name="Sunset Blaze (Orange/Red)", value="sunset"),
            app_commands.Choice(name="Tokyo Neon (Pink)", value="cyber_pink"),
            app_commands.Choice(name="Arctic Frost (Cyan)", value="ice_cyan"),
        ],
        style=[
            app_commands.Choice(name="Bento Pro Grid (1100x360)", value="bento"),
            app_commands.Choice(name="Cyberpunk Hex HUD (1120x340)", value="cyber"),
            app_commands.Choice(name="Triangle Prism Split (1060x370)", value="prism"),
            app_commands.Choice(name="Compact Square Box (800x470)", value="square"),
            app_commands.Choice(name="Ultra-Wide Strip (1200x250)", value="banner"),
            app_commands.Choice(name="Executive Ring Gauge (1080x360)", value="exec"),
        ],
        avatar_shape=[
            app_commands.Choice(name="Auto (Template Default)", value="auto"),
            app_commands.Choice(name="Circle (Gradient Ring)", value="circle"),
            app_commands.Choice(name="Hexagon (Cyber Polygon)", value="hexagon"),
            app_commands.Choice(name="Diamond (Prism Rhombus)", value="diamond"),
            app_commands.Choice(name="Square (Sharp Brutalist)", value="square"),
            app_commands.Choice(name="Rounded Squircle", value="rounded"),
        ]
    )
    async def mycard_slash(
        self,
        interaction: discord.Interaction,
        style: app_commands.Choice[str] = None,
        theme: app_commands.Choice[str] = None,
        avatar_shape: app_commands.Choice[str] = None,
        bio: str = None,
        bg_url: str = None
    ):
        await interaction.response.defer()
        udata = self.get_user_data(interaction.guild.id, interaction.user.id, interaction.user.display_name)

        if style:
            udata["card_style"] = style.value
        if theme:
            udata["custom_theme"] = theme.value
        if avatar_shape:
            udata["avatar_shape"] = avatar_shape.value
        if bio:
            udata["bio"] = bio[:42]
        if bg_url:
            udata["custom_bg"] = None if bg_url.lower() in ["none", "reset", "clear"] else bg_url

        self.save_data()
        path = await asyncio.to_thread(self.generate_member_card, interaction.guild, interaction.user)
        view = CardCustomizationView(self, interaction.user.id)
        await self.send_card_interaction(
            interaction,
            path,
            "mycard_studio.png",
            content="**Rank Card Customization Studio** — Select a template, color theme, or avatar shape below:",
            view=view
        )

    # 6. /xpstats
    @app_commands.command(name="xpstats", description="View a graphical analytics dashboard of your leveling stats.")
    async def xpstats_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        udata = self.get_user_data(interaction.guild.id, target.id, target.display_name)
        rank_pos = self.calculate_rank(interaction.guild.id, target.id)
        max_xp = self.get_max_xp(udata["level"])
        mult = float(gdata.get("multiplier", 1.0)) + (udata.get("prestige", 0) * 0.1)

        theme = udata.get("custom_theme") or gdata.get("theme", "crimson")
        bg = udata.get("custom_bg") or gdata.get("bg_url")
        ratio = udata["xp"] / max(max_xp, 1)

        stats_grid = [
            ("SERVER RANK", f"#{rank_pos}"),
            ("CURRENT LEVEL", f"LEVEL {udata['level']}"),
            ("PRESTIGE TIER", f"TIER {udata.get('prestige', 0)}"),
            ("LEVEL PROGRESS", f"{udata['xp']}/{max_xp} XP"),
            ("LIFETIME XP", f"{udata['total_xp']:,} XP"),
            ("ACTIVE BOOST", f"{mult:.1f}x BOOST"),
            ("TOTAL MESSAGES", f"{udata['messages']:,} MSGS"),
            ("VOICE ACTIVITY", f"{udata.get('voice_minutes', 0)} MINS")
        ]

        card_path = await asyncio.to_thread(
            create_stats_card,
            display_name=target.display_name,
            username=target.name,
            avatar_url=str(target.display_avatar.url),
            stats_grid=stats_grid,
            theme_name=theme,
            bg_url=bg,
            progress_ratio=ratio
        )
        await self.send_card_interaction(interaction, card_path, "xpstats.png")

    # 7. /rewards
    @app_commands.command(name="rewards", description="View all automatic level-up role rewards on this server.")
    async def rewards_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        rewards = gdata.get("role_rewards", {})

        highlights = []
        for lvl_str, rid in sorted(rewards.items(), key=lambda x: int(x[0]))[:4]:
            role = interaction.guild.get_role(int(rid))
            r_name = f"@{role.name[:14]}" if role else "Deleted Role"
            highlights.append((f"LEVEL {lvl_str}", r_name))

        if not highlights:
            highlights = [("STATUS", "NO REWARDS SET"), ("HOW TO ADD", "/ROLEREWARD")]

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="SERVER ROLE REWARDS",
            subtitle=f"Unlock exclusive roles automatically by leveling up in {interaction.guild.name}!",
            highlights=highlights,
            footer="Chat in text or voice channels to level up",
            avatar_url=str(interaction.guild.icon.url) if interaction.guild.icon else None,
            theme_name=gdata.get("theme", "crimson"),
            bg_url=gdata.get("bg_url")
        )
        await self.send_card_interaction(interaction, card_path, "rewards.png")

    # ADMIN COMMANDS
    @app_commands.command(name="givexp", description="[Admin] Give bonus XP to a member.")
    @app_commands.checks.has_permissions(administrator=True)
    async def givexp_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await interaction.response.defer()
        udata = self.get_user_data(interaction.guild.id, member.id, member.display_name)
        added = max(1, amount)
        udata["xp"] += added
        udata["total_xp"] += added
        await self.check_and_apply_levelup(interaction.guild, member, interaction.channel, udata)
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="ADMIN XP GRANTED",
            subtitle=f"Added bonus XP to {member.display_name}'s account!",
            highlights=[
                ("XP ADDED", f"+{added} XP"),
                ("NEW LEVEL", f"LEVEL {udata['level']}"),
                ("TOTAL XP", f"{udata['total_xp']} XP")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            avatar_url=str(member.display_avatar.url),
            theme_name="emerald"
        )
        await self.send_card_interaction(interaction, card_path, "givexp.png")

    @app_commands.command(name="removexp", description="[Admin] Remove XP from a member.")
    @app_commands.checks.has_permissions(administrator=True)
    async def removexp_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        await interaction.response.defer()
        udata = self.get_user_data(interaction.guild.id, member.id, member.display_name)
        removed = max(1, amount)
        udata["xp"] = max(0, udata["xp"] - removed)
        udata["total_xp"] = max(0, udata["total_xp"] - removed)
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="ADMIN XP DEDUCTED",
            subtitle=f"Removed XP from {member.display_name}'s account.",
            highlights=[
                ("XP REMOVED", f"-{removed} XP"),
                ("CURRENT XP", f"{udata['xp']} XP"),
                ("LEVEL", f"LEVEL {udata['level']}")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            avatar_url=str(member.display_avatar.url),
            theme_name="crimson"
        )
        await self.send_card_interaction(interaction, card_path, "removexp.png")

    @app_commands.command(name="setlevel", description="[Admin] Set a member's exact level (Starts from 0).")
    @app_commands.checks.has_permissions(administrator=True)
    async def setlevel_slash(self, interaction: discord.Interaction, member: discord.Member, level: int):
        await interaction.response.defer()
        udata = self.get_user_data(interaction.guild.id, member.id, member.display_name)
        udata["level"] = max(0, level)
        udata["xp"] = 0
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="MEMBER LEVEL UPDATED",
            subtitle=f"{member.display_name}'s level has been manually updated!",
            highlights=[
                ("NEW LEVEL", f"LEVEL {udata['level']}"),
                ("CURRENT XP", "0 XP"),
                ("REQUIRED XP", f"{self.get_max_xp(udata['level'])} XP")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            avatar_url=str(member.display_avatar.url),
            theme_name="ocean"
        )
        await self.send_card_interaction(interaction, card_path, "setlevel.png")

    @app_commands.command(name="resetxp", description="[Admin] Reset a member or the entire server back to Level 0 (0 XP).")
    @app_commands.checks.has_permissions(administrator=True)
    async def resetxp_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        if member:
            gdata["users"].pop(str(member.id), None)
            self.get_user_data(interaction.guild.id, member.id, member.display_name)
            target_title = "MEMBER XP RESET"
            target_sub = f"{member.display_name}'s leveling data has been reset to Level 0 (0 XP)."
            scope_val = member.display_name[:16]
        else:
            gdata["users"] = {}
            self.save_data()
            target_title = "FULL SERVER XP RESET"
            target_sub = "All server members have been reset to Level 0 (0 XP)."
            scope_val = "ENTIRE SERVER"

        card_path = await asyncio.to_thread(
            create_banner_card,
            title=target_title,
            subtitle=target_sub,
            highlights=[
                ("SCOPE", scope_val),
                ("STARTING LEVEL", "LEVEL 0"),
                ("STARTING XP", "0 / 100 XP")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            avatar_url=str(interaction.user.display_avatar.url),
            theme_name="crimson"
        )
        await self.send_card_interaction(interaction, card_path, "resetxp.png")

    @app_commands.command(name="rolereward", description="[Admin] Add or remove an automatic role reward for a specific level.")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add / Update Role Reward", value="add"),
        app_commands.Choice(name="Remove Role Reward", value="remove")
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def rolereward_slash(self, interaction: discord.Interaction, action: app_commands.Choice[str], level: int, role: discord.Role = None):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        if action.value == "add":
            if not role:
                await interaction.followup.send("Please select a role when adding a role reward.", ephemeral=True)
                return
            gdata["role_rewards"][str(level)] = role.id
            self.save_data()
            act_txt = "REWARD ADDED"
            r_txt = f"@{role.name[:16]}"
        else:
            gdata["role_rewards"].pop(str(level), None)
            self.save_data()
            act_txt = "REWARD REMOVED"
            r_txt = "NONE"

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="ROLE REWARD CONFIGURED",
            subtitle=f"Updated automatic level-up role reward configuration for Level {level}.",
            highlights=[
                ("STATUS", act_txt),
                ("TARGET LEVEL", f"LEVEL {level}"),
                ("ROLE", r_txt)
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            theme_name="gold"
        )
        await self.send_card_interaction(interaction, card_path, "rolereward.png")

    @app_commands.command(name="xpmultiplier", description="[Admin] Set server-wide XP boost multiplier (e.g. 1.0, 2.0, 3.0).")
    @app_commands.checks.has_permissions(administrator=True)
    async def xpmultiplier_slash(self, interaction: discord.Interaction, rate: float):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        gdata["multiplier"] = max(0.5, min(rate, 10.0))
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="SERVER XP MULTIPLIER UPDATED",
            subtitle=f"Global XP gain rate has been set to {gdata['multiplier']:.1f}x for all members!",
            highlights=[
                ("ACTIVE BOOST", f"{gdata['multiplier']:.1f}X XP"),
                ("TEXT XP", "BOOSTED"),
                ("STATUS", "ONLINE")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            theme_name="neon_violet"
        )
        await self.send_card_interaction(interaction, card_path, "multiplier.png")

    @app_commands.command(name="levelchannel", description="[Admin] Set the channel for level-up announcements (leave empty to reset).")
    @app_commands.checks.has_permissions(administrator=True)
    async def levelchannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        if channel:
            gdata["level_channel"] = channel.id
            ch_name = f"#{channel.name[:16]}"
        else:
            gdata["level_channel"] = None
            ch_name = "CURRENT CHANNEL"
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="LEVEL-UP CHANNEL UPDATED",
            subtitle="Configured where level-up announcement cards will be sent.",
            highlights=[
                ("TARGET CHANNEL", ch_name),
                ("CARD ALERTS", "ENABLED")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            theme_name="ocean"
        )
        await self.send_card_interaction(interaction, card_path, "levelchannel.png")

    @app_commands.command(name="ignorechannel", description="[Admin] Toggle XP gain on/off in a specific channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ignorechannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        ignored = gdata.get("ignored_channels", [])
        if channel.id in ignored:
            ignored.remove(channel.id)
            state_str = "XP ENABLED"
        else:
            ignored.append(channel.id)
            gdata["ignored_channels"] = ignored
            state_str = "XP DISABLED"
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="CHANNEL XP FILTER UPDATED",
            subtitle=f"Updated XP gain settings for #{channel.name}.",
            highlights=[
                ("CHANNEL", f"#{channel.name[:16]}"),
                ("XP STATUS", state_str)
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            theme_name="sunset"
        )
        await self.send_card_interaction(interaction, card_path, "ignorechannel.png")

    @app_commands.command(name="servercard", description="[Admin] Set default Rank Card theme and background for the server.")
    @app_commands.choices(theme=[
        app_commands.Choice(name="Crimson Rose (Red)", value="crimson"),
        app_commands.Choice(name="Cyber Violet (Purple)", value="neon_violet"),
        app_commands.Choice(name="Emerald Matrix (Green)", value="emerald"),
        app_commands.Choice(name="Royal Gold (Gold)", value="gold"),
        app_commands.Choice(name="Electric Ocean (Blue)", value="ocean"),
        app_commands.Choice(name="Sunset Blaze (Orange/Red)", value="sunset"),
        app_commands.Choice(name="Tokyo Neon (Pink)", value="cyber_pink"),
        app_commands.Choice(name="Arctic Frost (Cyan)", value="ice_cyan"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def servercard_slash(
        self,
        interaction: discord.Interaction,
        theme: app_commands.Choice[str] = None,
        bg_url: str = None
    ):
        await interaction.response.defer()
        gdata = self.get_guild_data(interaction.guild.id)
        if theme:
            gdata["theme"] = theme.value
        if bg_url:
            gdata["bg_url"] = None if bg_url.lower() in ["none", "reset", "clear"] else bg_url
        self.save_data()

        card_path = await asyncio.to_thread(
            create_banner_card,
            title="SERVER CARD THEME UPDATED",
            subtitle="Updated the default visual theme and background for all server cards!",
            highlights=[
                ("ACTIVE THEME", gdata.get("theme", "crimson").upper()),
                ("CUSTOM BG", "SET" if gdata.get("bg_url") else "DEFAULT GLOW")
            ],
            footer=f"Authorized by Admin: {interaction.user.display_name}",
            theme_name=gdata.get("theme", "crimson"),
            bg_url=gdata.get("bg_url")
        )
        await self.send_card_interaction(interaction, card_path, "servercard.png")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))