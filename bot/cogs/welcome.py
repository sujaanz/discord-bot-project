import discord
from discord.ext import commands
from discord import app_commands
import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import json
import os
import random

# =========================================================================
# 📁 DEFAULT SERVER CONFIGURATION SCHEMA (Website & Bot Compatible)
# =========================================================================
DEFAULT_GUILD_CONFIG = {
    "welcome_enabled": True,
    "welcome_channel": None,
    "auto_roles": [],
    "dm_enabled": False,
    "dm_message": "Hey {user_name}, welcome to **{server}**! Glad to have you with us.",
    
    # Message & Embed Mode Settings
    # Modes: "outside" (Default: Text + Card outside), "inside_embed" (Text + Card inside White Embed),
    #        "both_separate" (Text + White Embed + Card outside), "text_only", "embed_only"
    "display_mode": "outside",
    "card_enabled": True,
    "embed_enabled": False,  # False by default so message & card stay OUTSIDE embed initially!
    
    # Text Content (Outside Embed)
    "content_text": "Hey {user}, welcome to **{server}**! 🎉",
    
    # Embed Settings (Used when embed_enabled is True or display_mode uses embed)
    "embed_title": "✨ Welcome to {server}!",
    "embed_description": "Welcome {user}! You are our **#{count}** member. Make sure to check out the channels!",
    "embed_footer": "{server} • Member #{count}",
    "embed_color": "#FFFFFF",  # Always pure white sidebar by default
    "embed_thumbnail": True,
    
    # Welcome Card Image Customization
    "card_template": "minimal",  # Options: "minimal" (Red/Gradient style), "soul" (Night/Spooky style), "glass" (Modern Glass)
    "card_bg_url": "",           # Optional custom background URL from website or Discord
    "card_accent_color": "#E63946",  # Default crimson/coral or orange (#FF8C00)
    "card_title": "{user_name}",
    "card_subtitle": "Welcome to {server}!",
    "card_badge": "MEMBER #{count}",
    "card_show_badge": True,

    # Goodbye System Settings
    "goodbye_enabled": True,
    "goodbye_channel": None,
    "goodbye_display_mode": "outside",
    "goodbye_card_enabled": True,
    "goodbye_content_text": "**{user_name}** just left the server. 👋",
    "goodbye_embed_title": "👋 Member Departure",
    "goodbye_embed_description": "**{user_name}** has left **{server}**. We now have **{count}** members.",
    "goodbye_card_title": "GOODBYE, {user_name}",
    "goodbye_card_subtitle": "A soul has departed from {server}",
    "goodbye_card_badge": "SOUL #{count}"
}


# =========================================================================
# 🖥️ INTERACTIVE MODALS (POP-UP FORMS FOR USER-FRIENDLY EDITING)
# =========================================================================
class MessageEditModal(discord.ui.Modal, title="Edit Welcome Text & Embed"):
    def __init__(self, cog, guild_id: str):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        cfg = self.cog.get_guild_config(guild_id)

        self.content_input = discord.ui.TextInput(
            label="Outside Plain Text Message",
            style=discord.TextStyle.paragraph,
            default=cfg.get("content_text", ""),
            placeholder="e.g. Hey {user}, welcome to **{server}**!",
            required=False,
            max_length=1000
        )
        self.embed_title_input = discord.ui.TextInput(
            label="Embed Title (If Embed is ON)",
            style=discord.TextStyle.short,
            default=cfg.get("embed_title", ""),
            placeholder="e.g. ✨ Welcome to {server}!",
            required=False,
            max_length=256
        )
        self.embed_desc_input = discord.ui.TextInput(
            label="Embed Description (If Embed is ON)",
            style=discord.TextStyle.paragraph,
            default=cfg.get("embed_description", ""),
            placeholder="Variables: {user}, {user_name}, {server}, {count}",
            required=False,
            max_length=2000
        )
        self.embed_footer_input = discord.ui.TextInput(
            label="Embed Footer Text",
            style=discord.TextStyle.short,
            default=cfg.get("embed_footer", ""),
            required=False,
            max_length=256
        )

        self.add_item(self.content_input)
        self.add_item(self.embed_title_input)
        self.add_item(self.embed_desc_input)
        self.add_item(self.embed_footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = self.cog.get_guild_config(self.guild_id)
        cfg["content_text"] = self.content_input.value
        cfg["embed_title"] = self.embed_title_input.value
        cfg["embed_description"] = self.embed_desc_input.value
        cfg["embed_footer"] = self.embed_footer_input.value
        self.cog.save_guild_config(self.guild_id, cfg)

        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)


class CardDesignModal(discord.ui.Modal, title="Customize Welcome Card Image"):
    def __init__(self, cog, guild_id: str):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        cfg = self.cog.get_guild_config(guild_id)

        self.card_title_input = discord.ui.TextInput(
            label="Card Main Title",
            style=discord.TextStyle.short,
            default=cfg.get("card_title", "{user_name}"),
            placeholder="e.g. {user_name} or WELCOME, {user_name}",
            required=True,
            max_length=100
        )
        self.card_sub_input = discord.ui.TextInput(
            label="Card Subtitle Text",
            style=discord.TextStyle.short,
            default=cfg.get("card_subtitle", "Welcome to {server}!"),
            placeholder="e.g. {server} has a new soul tonight",
            required=True,
            max_length=150
        )
        self.card_badge_input = discord.ui.TextInput(
            label="Bottom Badge Text (Leave blank to hide)",
            style=discord.TextStyle.short,
            default=cfg.get("card_badge", "MEMBER #{count}"),
            placeholder="e.g. SOUL #{count} or MEMBER #{count}",
            required=False,
            max_length=50
        )
        self.accent_color_input = discord.ui.TextInput(
            label="Theme / Accent Hex Color",
            style=discord.TextStyle.short,
            default=cfg.get("card_accent_color", "#E63946"),
            placeholder="e.g. #E63946 (Red), #FF8C00 (Orange), #FFFFFF",
            required=True,
            max_length=7
        )
        self.bg_url_input = discord.ui.TextInput(
            label="Custom Background Image URL (Optional)",
            style=discord.TextStyle.short,
            default=cfg.get("card_bg_url", ""),
            placeholder="Paste direct PNG/JPG link or leave empty for template",
            required=False,
            max_length=500
        )

        self.add_item(self.card_title_input)
        self.add_item(self.card_sub_input)
        self.add_item(self.card_badge_input)
        self.add_item(self.accent_color_input)
        self.add_item(self.bg_url_input)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = self.cog.get_guild_config(self.guild_id)
        cfg["card_title"] = self.card_title_input.value
        cfg["card_subtitle"] = self.card_sub_input.value
        cfg["card_badge"] = self.card_badge_input.value.strip()
        cfg["card_show_badge"] = bool(self.card_badge_input.value.strip())
        cfg["card_accent_color"] = self.accent_color_input.value.strip() or "#E63946"
        cfg["card_bg_url"] = self.bg_url_input.value.strip()
        self.cog.save_guild_config(self.guild_id, cfg)

        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)


class GoodbyeEditModal(discord.ui.Modal, title="Customize Goodbye System"):
    def __init__(self, cog, guild_id: str):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        cfg = self.cog.get_guild_config(guild_id)

        self.goodbye_text_input = discord.ui.TextInput(
            label="Goodbye Plain Text Message",
            style=discord.TextStyle.paragraph,
            default=cfg.get("goodbye_content_text", ""),
            placeholder="e.g. **{user_name}** just left the server. 👋",
            required=False,
            max_length=1000
        )
        self.card_title_input = discord.ui.TextInput(
            label="Goodbye Card Title",
            style=discord.TextStyle.short,
            default=cfg.get("goodbye_card_title", "GOODBYE, {user_name}"),
            required=True,
            max_length=100
        )
        self.card_sub_input = discord.ui.TextInput(
            label="Goodbye Card Subtitle",
            style=discord.TextStyle.short,
            default=cfg.get("goodbye_card_subtitle", "A soul has departed from {server}"),
            required=True,
            max_length=150
        )
        self.card_badge_input = discord.ui.TextInput(
            label="Goodbye Card Badge",
            style=discord.TextStyle.short,
            default=cfg.get("goodbye_card_badge", "SOUL #{count}"),
            required=False,
            max_length=50
        )

        self.add_item(self.goodbye_text_input)
        self.add_item(self.card_title_input)
        self.add_item(self.card_sub_input)
        self.add_item(self.card_badge_input)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = self.cog.get_guild_config(self.guild_id)
        cfg["goodbye_content_text"] = self.goodbye_text_input.value
        cfg["goodbye_card_title"] = self.card_title_input.value
        cfg["goodbye_card_subtitle"] = self.card_sub_input.value
        cfg["goodbye_card_badge"] = self.card_badge_input.value.strip()
        self.cog.save_guild_config(self.guild_id, cfg)

        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)


# =========================================================================
# 🎛️ INTERACTIVE CONTROL PANEL VIEW (BUTTONS & DROPDOWNS)
# =========================================================================
class WelcomeDashboardView(discord.ui.View):
    def __init__(self, cog, guild_id: str):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.select(
        placeholder="📌 Choose Message & Embed Position Mode...",
        options=[
            discord.SelectOption(
                label="Outside Embed: Plain Text + Card (Default)",
                value="outside",
                description="Sends normal text + standalone card image outside (Like MEE6/ProBot)",
                emoji="🌐"
            ),
            discord.SelectOption(
                label="Inside White Embed: Embed + Card Inside",
                value="inside_embed",
                description="Sends a clean #FFFFFF white-sidebar Embed with the card inside it",
                emoji="🖼️"
            ),
            discord.SelectOption(
                label="Hybrid: White Embed + Card Outside Below",
                value="both_separate",
                description="Sends a #FFFFFF white Embed AND attaches the card outside",
                emoji="✨"
            ),
            discord.SelectOption(
                label="Plain Text Only (No Card, No Embed)",
                value="text_only",
                description="Sends only a clean text message without any image or embed",
                emoji="📝"
            ),
            discord.SelectOption(
                label="White Embed Only (No Card Image)",
                value="embed_only",
                description="Sends only a #FFFFFF white-sidebar Embed without the card",
                emoji="📋"
            ),
        ],
        row=0
    )
    async def select_display_mode(self, interaction: discord.Interaction, select: discord.ui.Select):
        cfg = self.cog.get_guild_config(self.guild_id)
        mode = select.values[0]
        cfg["display_mode"] = mode

        if mode == "outside":
            cfg["embed_enabled"] = False
            cfg["card_enabled"] = True
        elif mode == "inside_embed":
            cfg["embed_enabled"] = True
            cfg["card_enabled"] = True
        elif mode == "both_separate":
            cfg["embed_enabled"] = True
            cfg["card_enabled"] = True
        elif mode == "text_only":
            cfg["embed_enabled"] = False
            cfg["card_enabled"] = False
        elif mode == "embed_only":
            cfg["embed_enabled"] = True
            cfg["card_enabled"] = False

        self.cog.save_guild_config(self.guild_id, cfg)
        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.select(
        placeholder="🎨 Choose Welcome Card Visual Template...",
        options=[
            discord.SelectOption(
                label="Template 1: Minimalist Gradient (Clean Style)",
                value="minimal",
                description="Smooth gradient, white avatar ring, clean centered bold text",
                emoji="🔴"
            ),
            discord.SelectOption(
                label="Template 2: Night Soul Theme (Spooky / Dark)",
                value="soul",
                description="Night sky, glowing moon, orange ring & SOUL # badge pill",
                emoji="🌙"
            ),
            discord.SelectOption(
                label="Template 3: Modern Frosted Glass (White Accent)",
                value="glass",
                description="Sleek dark carbon card with pure white glassmorphism border",
                emoji="💎"
            ),
        ],
        row=1
    )
    async def select_template(self, interaction: discord.Interaction, select: discord.ui.Select):
        cfg = self.cog.get_guild_config(self.guild_id)
        template = select.values[0]
        cfg["card_template"] = template

        # Set matching smart defaults when switching template
        if template == "minimal":
            cfg["card_accent_color"] = "#E63946"
            cfg["card_title"] = "{user_name}"
            cfg["card_subtitle"] = "Welcome to {server} 🪦!"
            cfg["card_show_badge"] = False
        elif template == "soul":
            cfg["card_accent_color"] = "#FF8C00"
            cfg["card_title"] = "WELCOME, {user_name}"
            cfg["card_subtitle"] = "{server} 🪦 has a new soul tonight"
            cfg["card_badge"] = "SOUL #{count}"
            cfg["card_show_badge"] = True
        elif template == "glass":
            cfg["card_accent_color"] = "#FFFFFF"
            cfg["card_title"] = "WELCOME, {user_name}"
            cfg["card_subtitle"] = "Welcome to {server} • Enjoy your stay"
            cfg["card_badge"] = "MEMBER #{count}"
            cfg["card_show_badge"] = True

        self.cog.save_guild_config(self.guild_id, cfg)
        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Edit Text & Embed", style=discord.ButtonStyle.secondary, emoji="📝", row=2)
    async def btn_edit_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MessageEditModal(self.cog, self.guild_id))

    @discord.ui.button(label="Customize Card", style=discord.ButtonStyle.secondary, emoji="🎨", row=2)
    async def btn_edit_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CardDesignModal(self.cog, self.guild_id))

    @discord.ui.button(label="Edit Goodbye", style=discord.ButtonStyle.secondary, emoji="👋", row=2)
    async def btn_edit_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GoodbyeEditModal(self.cog, self.guild_id))

    @discord.ui.button(label="Toggle Card ON/OFF", style=discord.ButtonStyle.primary, emoji="🖼️", row=3)
    async def btn_toggle_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = self.cog.get_guild_config(self.guild_id)
        cfg["card_enabled"] = not cfg.get("card_enabled", True)
        self.cog.save_guild_config(self.guild_id, cfg)
        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Toggle Embed ON/OFF", style=discord.ButtonStyle.primary, emoji="📦", row=3)
    async def btn_toggle_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = self.cog.get_guild_config(self.guild_id)
        cfg["embed_enabled"] = not cfg.get("embed_enabled", False)
        if cfg["embed_enabled"] and cfg["display_mode"] == "outside":
            cfg["display_mode"] = "inside_embed"
        elif not cfg["embed_enabled"] and cfg["display_mode"] in ("inside_embed", "embed_only"):
            cfg["display_mode"] = "outside"
        self.cog.save_guild_config(self.guild_id, cfg)
        embed = self.cog.build_dashboard_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Test Live Welcome", style=discord.ButtonStyle.success, emoji="🧪", row=3)
    async def btn_test_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.dispatch_welcome_or_goodbye(interaction.user, event_type="welcome", test_channel=interaction.channel)
        await interaction.followup.send("✅ Sent a live test welcome message to this channel!", ephemeral=True)


# =========================================================================
# 🚀 MAIN WELCOME & GOODBYE COG
# =========================================================================
class UltimateWelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "welcome_settings.json")
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

    # Always read fresh from disk so Website Dashboard edits sync in real-time!
    def load_all_settings(self) -> dict:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_guild_config(self, guild_id: str) -> dict:
        all_data = self.load_all_settings()
        guild_str = str(guild_id)
        cfg = DEFAULT_GUILD_CONFIG.copy()
        if guild_str in all_data:
            cfg.update(all_data[guild_str])
        return cfg

    def save_guild_config(self, guild_id: str, cfg: dict):
        all_data = self.load_all_settings()
        all_data[str(guild_id)] = cfg
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)

    # Format dynamic placeholders
    def format_text(self, text: str, member: discord.Member, upper_name: bool = False) -> str:
        if not text:
            return ""
        u_name = member.name.upper() if upper_name else member.name
        return (
            text.replace("{user}", member.mention)
            .replace("{member}", member.mention)
            .replace("{user_name}", u_name)
            .replace("{name}", u_name)
            .replace("{display_name}", member.display_name)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count or len(member.guild.members)))
        )

    def hex_to_rgb(self, hex_str: str, default=(230, 57, 70)):
        try:
            h = hex_str.lstrip("#")
            if len(h) == 6:
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            pass
        return default

    def get_font(self, size: int, bold: bool = True):
        font_candidates = [
            "arialbd.ttf" if bold else "arial.ttf",
            "segoeuib.ttf" if bold else "segoeui.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "arial.ttf"
        ]
        for font_name in font_candidates:
            try:
                return ImageFont.truetype(font_name, size)
            except IOError:
                continue
        return ImageFont.load_default()

    def draw_centered_text(self, draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text((x - text_w // 2, y - text_h // 2), text, font=font, fill=fill)

    # =========================================================================
    # 🎨 NEXT-GEN PIL CARD RENDERING ENGINE (3 TEMPLATES + CUSTOM BG)
    # =========================================================================
    async def create_card(self, member: discord.Member, event_type: str = "welcome") -> BytesIO:
        width, height = 1000, 480
        cfg = self.get_guild_config(str(member.guild.id))
        template = cfg.get("card_template", "minimal")
        accent_rgb = self.hex_to_rgb(cfg.get("card_accent_color", "#E63946"))
        bg_url = cfg.get("card_bg_url", "").strip()

        card = None
        # 1. Load Custom Background if set via Website or Discord
        if bg_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(bg_url, timeout=8) as resp:
                        if resp.status == 200:
                            bg_bytes = await resp.read()
                            bg_img = Image.open(BytesIO(bg_bytes)).convert("RGBA")
                            card = bg_img.resize((width, height), Image.Resampling.LANCZOS)
                            # Subtle dark overlay for text readability
                            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 95))
                            card = Image.alpha_composite(card, overlay)
            except Exception:
                card = None

        # 2. Generate Procedural Template Background if no custom image
        if not card:
            card = Image.new("RGBA", (width, height), (20, 15, 35, 255))
            draw = ImageDraw.Draw(card)

            if template == "minimal":
                # Smooth diagonal-style gradient (Matches Screenshot 1: Red/Coral Clean Theme)
                r1, g1, b1 = accent_rgb
                r2, g2, b2 = max(0, r1 - 55), max(0, g1 - 35), max(0, b1 - 35)
                for y in range(height):
                    ratio = y / height
                    r = int(r1 * (1 - ratio) + r2 * ratio)
                    g = int(g1 * (1 - ratio) + g2 * ratio)
                    b = int(b1 * (1 - ratio) + b2 * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

            elif template == "soul":
                # Spooky / Night Sky Theme (Matches Screenshot 2: Dark Purple Sky, Moon, Stars, Horizon)
                for y in range(height):
                    ratio = y / height
                    r = int(20 * (1 - ratio) + 48 * ratio)
                    g = int(14 * (1 - ratio) + 25 * ratio)
                    b = int(42 * (1 - ratio) + 75 * ratio)
                    draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

                # Twinkling Stars
                star_coords = [(85, 65), (185, 130), (325, 45), (140, 220), (680, 60), (920, 240)]
                for sx, sy in star_coords:
                    draw.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 250, 220, 210))

                # Glowing Full Moon on top right
                draw.ellipse([755, 40, 915, 200], fill=(254, 249, 215, 255))
                draw.ellipse([775, 70, 810, 105], fill=(242, 233, 184, 255))
                draw.ellipse([825, 135, 850, 160], fill=(242, 233, 184, 255))

                # Dark rolling bottom hills
                draw.ellipse([-150, 390, 600, 560], fill=(12, 9, 24, 255))
                draw.ellipse([450, 395, 1150, 560], fill=(12, 9, 24, 255))

            else:  # "glass" template
                card = Image.new("RGBA", (width, height), (14, 16, 22, 255))
                draw = ImageDraw.Draw(card)
                # Frosted inner panel with pure white minimalist border
                draw.rounded_rectangle([35, 35, width - 35, height - 35], radius=24, fill=(24, 28, 38, 255), outline=(255, 255, 255, 90), width=2)

        draw = ImageDraw.Draw(card)

        # 3. Fetch & Render Circular Member Avatar with Ring
        avatar_size = 190
        avatar_x = (width - avatar_size) // 2
        avatar_y = 50

        avatar_url = member.display_avatar.with_size(256).url
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url, timeout=8) as resp:
                    if resp.status == 200:
                        av_bytes = await resp.read()
                        av_img = Image.open(BytesIO(av_bytes)).convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)

                        # Circular mask
                        mask = Image.new("L", (avatar_size, avatar_size), 0)
                        ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)

                        # Outer Ring Color (White for minimal/glass, Orange/Accent for soul)
                        ring_color = (255, 255, 255, 255) if template == "minimal" else (*accent_rgb, 255)
                        ring_pad = 8
                        ring_size = avatar_size + ring_pad * 2
                        ring_img = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
                        ImageDraw.Draw(ring_img).ellipse((0, 0, ring_size - 1, ring_size - 1), fill=ring_color)

                        card.paste(ring_img, (avatar_x - ring_pad, avatar_y - ring_pad), ring_img)
                        card.paste(av_img, (avatar_x, avatar_y), mask)
        except Exception:
            pass

        # 4. Render Centered Typography & Bottom Pill Badge
        title_font = self.get_font(54, bold=True)
        sub_font = self.get_font(30, bold=True)
        badge_font = self.get_font(20, bold=True)

        is_upper = (template in ("soul", "glass")) or (event_type == "goodbye")
        if event_type == "welcome":
            raw_title = cfg.get("card_title", "{user_name}")
            raw_sub = cfg.get("card_subtitle", "Welcome to {server}!")
            raw_badge = cfg.get("card_badge", "MEMBER #{count}")
            show_badge = cfg.get("card_show_badge", template != "minimal")
        else:
            raw_title = cfg.get("goodbye_card_title", "GOODBYE, {user_name}")
            raw_sub = cfg.get("goodbye_card_subtitle", "A soul has departed from {server}")
            raw_badge = cfg.get("goodbye_card_badge", "SOUL #{count}")
            show_badge = True

        main_text = self.format_text(raw_title, member, upper_name=is_upper)
        sub_text = self.format_text(raw_sub, member, upper_name=False)
        badge_text = self.format_text(raw_badge, member, upper_name=True)

        title_fill = (255, 255, 255, 255) if template == "minimal" else (*accent_rgb, 255)
        self.draw_centered_text(draw, width // 2, 300, main_text, title_font, title_fill)
        self.draw_centered_text(draw, width // 2, 365, sub_text, sub_font, (245, 245, 245, 255))

        if show_badge and badge_text:
            bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
            bw = (bbox[2] - bbox[0]) + 48
            bh = 40
            bx = (width - bw) // 2
            by = 412
            pill_fill = (*accent_rgb, 255) if template != "glass" else (255, 255, 255, 235)
            pill_text_fill = (15, 15, 20, 255) if template == "glass" else (20, 15, 25, 255)
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=20, fill=pill_fill)
            self.draw_centered_text(draw, width // 2, by + bh // 2 - 2, badge_text, badge_font, pill_text_fill)

        buffer = BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    # =========================================================================
    # 📨 UNIFIED DISPATCHER (HANDLES OUTSIDE EMBED, INSIDE EMBED, TEXT, CARD)
    # =========================================================================
    async def dispatch_welcome_or_goodbye(self, member: discord.Member, event_type: str = "welcome", test_channel: discord.TextChannel = None):
        cfg = self.get_guild_config(str(member.guild.id))

        if event_type == "welcome" and not cfg.get("welcome_enabled", True) and not test_channel:
            return
        if event_type == "goodbye" and not cfg.get("goodbye_enabled", True) and not test_channel:
            return

        # Determine target channel
        if test_channel:
            target_channel = test_channel
        else:
            chan_key = "welcome_channel" if event_type == "welcome" else "goodbye_channel"
            chan_id = cfg.get(chan_key)
            target_channel = member.guild.get_channel(int(chan_id)) if chan_id else None
            if not target_channel:
                fallback_name = "welcome" if event_type == "welcome" else "goodbye"
                target_channel = discord.utils.get(member.guild.text_channels, name=fallback_name) or member.guild.system_channel

        if not target_channel:
            return

        # Mode & Content Selection
        mode = cfg.get("display_mode", "outside") if event_type == "welcome" else cfg.get("goodbye_display_mode", "outside")
        card_enabled = cfg.get("card_enabled", True) if event_type == "welcome" else cfg.get("goodbye_card_enabled", True)
        embed_enabled = cfg.get("embed_enabled", False)

        raw_content = cfg.get("content_text", "") if event_type == "welcome" else cfg.get("goodbye_content_text", "")
        content_msg = self.format_text(raw_content, member) if raw_content else None

        # Generate Card File if enabled
        file = None
        filename = f"{event_type}_card.png"
        if card_enabled and mode != "text_only" and mode != "embed_only":
            card_buffer = await self.create_card(member, event_type=event_type)
            file = discord.File(fp=card_buffer, filename=filename)

        # Build Pure White (#FFFFFF) Sidebar Embed if Embed Mode is active
        embed = None
        if embed_enabled or mode in ("inside_embed", "both_separate", "embed_only"):
            e_title = cfg.get("embed_title", "") if event_type == "welcome" else cfg.get("goodbye_embed_title", "")
            e_desc = cfg.get("embed_description", "") if event_type == "welcome" else cfg.get("goodbye_embed_description", "")
            e_footer = cfg.get("embed_footer", "{server} • Member #{count}")

            embed = discord.Embed(
                title=self.format_text(e_title, member),
                description=self.format_text(e_desc, member),
                color=0xFFFFFF,  # Strictly Pure White sidebar
                timestamp=datetime.datetime.utcnow()
            )
            if cfg.get("embed_thumbnail", True):
                embed.set_thumbnail(url=member.display_avatar.url)
            if e_footer:
                embed.set_footer(text=self.format_text(e_footer, member))

            # Only attach card INSIDE embed if mode is specifically "inside_embed"
            if file and mode == "inside_embed":
                embed.set_image(url=f"attachment://{filename}")

        # Dispatch according to user's selected mode
        if mode == "outside":
            # DEFAULT: Plain text + Standalone Card Image OUTSIDE any embed!
            await target_channel.send(content=content_msg, file=file)
        elif mode == "inside_embed":
            await target_channel.send(content=content_msg, embed=embed, file=file)
        elif mode == "both_separate":
            # Sends White Embed first, and Card Image outside right below it
            await target_channel.send(content=content_msg, embed=embed)
            if file:
                await target_channel.send(file=file)
        elif mode == "text_only":
            await target_channel.send(content=content_msg or f"Welcome {member.mention}!")
        elif mode == "embed_only":
            await target_channel.send(content=content_msg, embed=embed)

    # =========================================================================
    # 🔔 DISCORD EVENTS (JOIN & LEAVE)
    # =========================================================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = self.get_guild_config(str(member.guild.id))

        # 1. Auto-Roles Assignment
        auto_roles = cfg.get("auto_roles", [])
        for r_id in auto_roles:
            role = member.guild.get_role(int(r_id))
            if role:
                try:
                    await member.add_roles(role, reason="Automated Welcome Role")
                except Exception:
                    pass

        # 2. Optional Private DM Welcome
        if cfg.get("dm_enabled", False) and cfg.get("dm_message"):
            try:
                await member.send(self.format_text(cfg["dm_message"], member))
            except Exception:
                pass

        # 3. Dispatch Welcome Message & Card
        await self.dispatch_welcome_or_goodbye(member, event_type="welcome")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.dispatch_welcome_or_goodbye(member, event_type="goodbye")

    # =========================================================================
    # 📊 DASHBOARD EMBED BUILDER
    # =========================================================================
    def build_dashboard_embed(self, guild: discord.Guild) -> discord.Embed:
        cfg = self.get_guild_config(str(guild.id))
        w_chan = guild.get_channel(int(cfg["welcome_channel"])) if cfg.get("welcome_channel") else None
        g_chan = guild.get_channel(int(cfg["goodbye_channel"])) if cfg.get("goodbye_channel") else None

        mode_names = {
            "outside": "🌐 Outside Embed (Plain Text + Card) [Default]",
            "inside_embed": "🖼️ Inside White Embed (Embed + Card)",
            "both_separate": "✨ Hybrid (White Embed + Outside Card)",
            "text_only": "📝 Plain Text Only",
            "embed_only": "📋 White Embed Only"
        }

        embed = discord.Embed(
            title=f"⚙️ {guild.name} — Welcome & Goodbye Control Center",
            description=(
                "Customize everything interactively below or via the **Web Dashboard**.\n"
                "All changes sync automatically with `welcome_settings.json`."
            ),
            color=0xFFFFFF
        )
        embed.add_field(
            name="📌 System Channels & Status",
            value=(
                f"**Welcome:** {'🟢 ON' if cfg.get('welcome_enabled', True) else '🔴 OFF'} ({w_chan.mention if w_chan else '`Auto-detect`'})\n"
                f"**Goodbye:** {'🟢 ON' if cfg.get('goodbye_enabled', True) else '🔴 OFF'} ({g_chan.mention if g_chan else '`Auto-detect`'})\n"
                f"**DM Welcome:** {'🟢 ON' if cfg.get('dm_enabled', False) else '🔴 OFF'}"
            ),
            inline=False
        )
        embed.add_field(
            name="🎨 Display & Card Mode",
            value=(
                f"**Position Mode:** {mode_names.get(cfg.get('display_mode', 'outside'))}\n"
                f"**Welcome Card:** {'✅ Enabled' if cfg.get('card_enabled', True) else '❌ Disabled'}\n"
                f"**White Embed (`#FFFFFF`):** {'✅ Enabled' if cfg.get('embed_enabled', False) else '❌ Disabled (Outside Mode)'}\n"
                f"**Card Template:** `{cfg.get('card_template', 'minimal').upper()}` | **Accent:** `{cfg.get('card_accent_color')}`"
            ),
            inline=False
        )
        embed.add_field(
            name="💬 Active Message Preview",
            value=f"**Plain Text:** {cfg.get('content_text') or '`None`'}\n**Card Text:** `{cfg.get('card_title')}` — `{cfg.get('card_subtitle')}`",
            inline=False
        )
        embed.set_footer(text="Variables: {user}, {user_name}, {server}, {count} • Pure White Theme")
        return embed

    # =========================================================================
    # ⚡ SLASH COMMANDS (CLEAN & USER-FRIENDLY)
    # =========================================================================
    welcome_group = app_commands.Group(name="welcome", description="Interactive Welcome & Goodbye Control Suite")

    @welcome_group.command(name="panel", description="Open the interactive Welcome & Goodbye Control Panel (Buttons & Forms).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def open_panel(self, interaction: discord.Interaction):
        embed = self.build_dashboard_embed(interaction.guild)
        view = WelcomeDashboardView(self, str(interaction.guild.id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @welcome_group.command(name="channel", description="Set the welcome channel and/or goodbye channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channels(
        self,
        interaction: discord.Interaction,
        welcome_channel: discord.TextChannel = None,
        goodbye_channel: discord.TextChannel = None
    ):
        cfg = self.get_guild_config(str(interaction.guild.id))
        if welcome_channel:
            cfg["welcome_channel"] = welcome_channel.id
        if goodbye_channel:
            cfg["goodbye_channel"] = goodbye_channel.id
        self.save_guild_config(str(interaction.guild.id), cfg)

        embed = discord.Embed(
            title="✅ Channels Updated",
            description=(
                f"**Welcome Channel:** {welcome_channel.mention if welcome_channel else 'Unchanged'}\n"
                f"**Goodbye Channel:** {goodbye_channel.mention if goodbye_channel else 'Unchanged'}"
            ),
            color=0xFFFFFF
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="autorole", description="Add or remove an automatic role for new members.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def manage_autorole(self, interaction: discord.Interaction, role: discord.Role):
        cfg = self.get_guild_config(str(interaction.guild.id))
        roles = cfg.get("auto_roles", [])
        if role.id in roles:
            roles.remove(role.id)
            action = f"Removed {role.mention} from Auto-Roles."
        else:
            roles.append(role.id)
            action = f"Added {role.mention} to Auto-Roles."
        cfg["auto_roles"] = roles
        self.save_guild_config(str(interaction.guild.id), cfg)

        embed = discord.Embed(title="✅ Auto-Role Updated", description=action, color=0xFFFFFF)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="dm", description="Toggle and customize the private DM message sent to new members.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def configure_dm(self, interaction: discord.Interaction, enabled: bool, message: str = None):
        cfg = self.get_guild_config(str(interaction.guild.id))
        cfg["dm_enabled"] = enabled
        if message:
            cfg["dm_message"] = message
        self.save_guild_config(str(interaction.guild.id), cfg)

        embed = discord.Embed(
            title="✅ Welcome DM Updated",
            description=f"**Status:** {'🟢 Enabled' if enabled else '🔴 Disabled'}\n**Message:** {cfg['dm_message']}",
            color=0xFFFFFF
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @welcome_group.command(name="test", description="Send a live test of your current Welcome or Goodbye setup.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(event=[
        app_commands.Choice(name="Welcome Event", value="welcome"),
        app_commands.Choice(name="Goodbye Event", value="goodbye")
    ])
    async def test_event(self, interaction: discord.Interaction, event: str = "welcome"):
        await interaction.response.defer(ephemeral=True)
        await self.dispatch_welcome_or_goodbye(interaction.user, event_type=event, test_channel=interaction.channel)
        await interaction.followup.send(f"🧪 Dispatched live **{event}** test in {interaction.channel.mention}!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UltimateWelcomeSystem(bot))