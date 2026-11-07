import discord
from discord.ext import commands
from discord import app_commands
import datetime
import re
import random

class UltraModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Local database to track warnings and user infractions
        self.warnings = {}
        
        # Advanced Regex patterns for Auto-Moderation
        self.invite_regex = re.compile(r'(https?://)?(www\.)?(discord\.(gg|io|me|li|club)|discordapp\.com/invite|discord\.com/invite)/[a-zA-Z0-9]+')
        self.url_regex = re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)')
        self.bad_words = ["scam", "free nitro", "steam nitro", "crypto giveaway", "nigger", "fag", "hack"]

    def generate_case_id(self):
        return f"CASE-#{random.randint(1000, 9999)}"

    # =========================================================================
    # 🤖 REAL-TIME AUTO-MODERATION ENGINE
    # =========================================================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        # Bypass for admins and moderators with manage_messages permission
        if message.author.guild_permissions.manage_messages:
            return

        content_lower = message.content.lower()
        violation = None

        # 1. Discord Invite Link Detection
        if self.invite_regex.search(message.content):
            violation = "Sharing unauthorized Discord server invite links."

        # 2. Phishing & Scam Link Detection
        elif any(scam in content_lower for scam in ["free nitro", "steam gift", "nitro generator", "discord-nitro"]):
            violation = "Posting potential phishing or scam links."

        # 3. Prohibited / Toxic Words Filter
        elif any(word in content_lower for word in self.bad_words):
            violation = "Using prohibited, toxic, or restricted language."

        # Action upon rule violation
        if violation:
            try:
                await message.delete()
            except discord.HTTPException:
                pass

            # Professional warning embed with clean minimalist border
            warning_embed = discord.Embed(
                title="🛡️ Auto-Moderation Security Intercept",
                description=f"{message.author.mention}, your message was automatically removed.",
                color=0xFFFFFF,
                timestamp=datetime.datetime.utcnow()
            )
            warning_embed.add_field(name="Infraction Reason", value=violation, inline=False)
            warning_embed.set_footer(text="Sofiya Security System • Automated Protection")
            
            alert_msg = await message.channel.send(embed=warning_embed)
            await alert_msg.delete(delay=6)
            return

        await self.bot.process_commands(message)

    # =========================================================================
    # ⚔️ ADVANCED MODERATION SLASH COMMANDS
    # =========================================================================

    # 1. KICK COMMAND
    @app_commands.command(name="kick", description="Kick a member from the server with an audit log reason.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("❌ You cannot kick a member with an equal or higher role.", ephemeral=True)
            return

        case_id = self.generate_case_id()
        
        # Try notifying the user via DM
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ You have been kicked from {interaction.guild.name}",
                description=f"**Reason:** {reason}\n**Moderator:** {interaction.user}",
                color=0xFFFFFF
            )
            await member.send(embed=dm_embed)
        except:
            pass

        await member.kick(reason=f"[{case_id}] {reason} | By: {interaction.user}")
        
        embed = discord.Embed(
            title="🔨 Member Kicked Successfully",
            description=f"**Target:** {member.mention} (`{member.id}`)\n**Moderator:** {interaction.user.mention}",
            color=0xFFFFFF,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Case ID: {case_id}")
        await interaction.response.send_message(embed=embed)

    # 2. BAN COMMAND
    @app_commands.command(name="ban", description="Permanently ban a member and optionally purge messages.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: int = 0):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("❌ You cannot ban a member with an equal or higher role.", ephemeral=True)
            return

        case_id = self.generate_case_id()
        await member.ban(reason=f"[{case_id}] {reason} | By: {interaction.user}", delete_message_days=delete_days)
        
        embed = discord.Embed(
            title="⛔ Member Banned Successfully",
            description=f"**Target:** {member.mention} (`{member.id}`)\n**Deleted Messages:** Past {delete_days} day(s)",
            color=0xFFFFFF,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Case ID: {case_id}")
        await interaction.response.send_message(embed=embed)

    # 3. UNBAN COMMAND
    @app_commands.command(name="unban", description="Unban a user using their Discord User ID.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            
            embed = discord.Embed(
                title="🔓 User Unbanned",
                description=f"Successfully unbanned **{user.name}** (`{user.id}`)",
                color=0xFFFFFF,
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Invalid User ID or user not banned. Error: {e}", ephemeral=True)

    # 4. TIMEOUT / MUTE COMMAND
    @app_commands.command(name="timeout", description="Mute a member by applying a temporary timeout.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
            await interaction.response.send_message("❌ You cannot timeout this member.", ephemeral=True)
            return

        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        
        embed = discord.Embed(
            title="⏱️ Member Timed Out",
            description=f"**Target:** {member.mention}\n**Duration:** {minutes} Minute(s)",
            color=0xFFFFFF,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    # 5. WARN SYSTEM COMMAND
    @app_commands.command(name="warn", description="Issue a formal warning to a server member.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        guild_id = interaction.guild.id
        user_id = member.id

        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}
        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = []

        warn_data = {"reason": reason, "moderator": str(interaction.user), "date": str(datetime.datetime.utcnow().date())}
        self.warnings[guild_id][user_id].append(warn_data)

        warn_count = len(self.warnings[guild_id][user_id])

        embed = discord.Embed(
            title="⚠️ Formal Warning Issued",
            description=f"**Target:** {member.mention}\n**Total Warnings:** {warn_count}",
            color=0xFFFFFF,
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    # 6. CHECK WARNINGS COMMAND
    @app_commands.command(name="warnings", description="View active warnings for a member.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings_list(self, interaction: discord.Interaction, member: discord.Member):
        guild_id = interaction.guild.id
        user_id = member.id
        user_warns = self.warnings.get(guild_id, {}).get(user_id, [])

        if not user_warns:
            await interaction.response.send_message(f"✅ {member.mention} has no active warnings.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📋 Warning History for {member.name}", color=0xFFFFFF)
        for idx, w in enumerate(user_warns, 1):
            embed.add_field(name=f"Warning #{idx}", value=f"**Reason:** {w['reason']}\n**Moderator:** {w['moderator']}\n**Date:** {w['date']}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 7. PURGE / CLEAR MESSAGES COMMAND
    @app_commands.command(name="clear", description="Bulk delete messages from a channel (1-100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount <= 0 or amount > 100:
            await interaction.response.send_message("❌ Please provide a number between 1 and 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Successfully cleared **{len(deleted)}** message(s).", ephemeral=True)

    # 8. LOCKDOWN CHANNEL COMMAND
    @app_commands.command(name="lock", description="Lock a channel to prevent members from sending messages.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        await target_channel.set_permissions(interaction.guild.default_role, send_messages=False)
        
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"{target_channel.mention} has been locked down by administration.",
            color=0xFFFFFF
        )
        await interaction.response.send_message(embed=embed)

    # 9. UNLOCK CHANNEL COMMAND
    @app_commands.command(name="unlock", description="Unlock a previously locked channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        await target_channel.set_permissions(interaction.guild.default_role, send_messages=True)
        
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"{target_channel.mention} has been unlocked.",
            color=0xFFFFFF
        )
        await interaction.response.send_message(embed=embed)

    # Permission & Command Error Handler
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("❌ You do not have the required permissions to execute this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UltraModeration(bot))