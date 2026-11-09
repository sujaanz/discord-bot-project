import os
import time
import json
import requests
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from jinja2 import TemplateNotFound
from dotenv import load_dotenv

# Support running both as `python -m web.app` from root or `python web/app.py`
try:
    from web.auth import auth_bp, CLIENT_ID as AUTH_CLIENT_ID
except ImportError:
    try:
        from auth import auth_bp, CLIENT_ID as AUTH_CLIENT_ID
    except ImportError:
        from auth import auth_bp
        AUTH_CLIENT_ID = "1267928727833149592"

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "sofiya_maki_exact_master_key_2026")

app.register_blueprint(auth_bp, url_prefix='/auth')

SETTINGS_FILE = 'web/server_settings.json'
LEVELS_FILE = 'bot/data/levels_v3.json'
STATUS_CONFIG_FILE = 'web/bot_status.json'
DISCORD_API_BASE = 'https://discord.com/api/v10'
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", AUTH_CLIENT_ID or "1267928727833149592")

# In-memory cache for bot guild presence to avoid Discord API rate limits
_BOT_GUILDS_CACHE = {
    "guild_ids": set(),
    "timestamp": 0.0,
    "token_valid": False
}

# Customizable Status Bar & Global Bot Telemetry Defaults (Auto-saved to web/bot_status.json)
DEFAULT_BOT_STATUS_CONFIG = {
    "bot_name": "Sofiya",
    "status_bar_text": "Online • 28 Modules Ready",
    "connected_status_prefix": "Connected as",
    "cluster_name": "Cluster #01 (India/Global)",
    "default_ping_ms": 16,
    "uptime_percent": "99.98%",
    "promo_badge": "DISCOUNT",
    "promo_text": "Save 30% on Premium Pro",
    "premium_price": "$3.50",
    "use_live_bot_guild_count": True,
    "fallback_server_count_display": "1,600,000+",
    "custom_server_count_override": None
}

# All 28 Modules Default State (Matches index.html & manage.html 28 cards)
DEFAULT_MODULES_STATE = {
    "customiser": True,
    "welcomer": True,
    "level": True,
    "economy": True,
    "music": True,
    "moderation": True,
    "logs": True,
    "giveaways": True,
    "tickets": True,
    "reaction_roles": True,
    "sticky_roles": True,
    "counters": True,
    "starboard": True,
    "suggestions": True,
    "birthdays": True,
    "embeds": True,
    "timers": True,
    "sticky_messages": True,
    "notifications": True,
    "automations": True,
    "custom_commands": True,
    "temp_channels": True,
    "roleplay": True,
    "analytics": True,
    "connect": True,
    "verify": True,
    "invite_tracker": True,
    "polls": True
}

# Per-Module Dedicated Bot Cog Mapping (Links all 28 modules to their respective Bot Cogs)
MODULE_COG_MAP = {
    "customiser": {"cog": "BrandingCog", "db_namespace": "branding_config"},
    "welcomer": {"cog": "WelcomerCog", "db_namespace": "welcomer_config"},
    "level": {"cog": "LevelingCog", "db_namespace": "levels_v3"},
    "economy": {"cog": "EconomyCog", "db_namespace": "economy_config"},
    "music": {"cog": "MusicAudioCog", "db_namespace": "music_config"},
    "moderation": {"cog": "ModerationCog", "db_namespace": "automod_config"},
    "logs": {"cog": "AuditLogsCog", "db_namespace": "audit_logs_config"},
    "giveaways": {"cog": "GiveawaysCog", "db_namespace": "giveaways_config"},
    "tickets": {"cog": "TicketsCog", "db_namespace": "tickets_config"},
    "reaction_roles": {"cog": "RoleSelectCog", "db_namespace": "reaction_roles_config"},
    "sticky_roles": {"cog": "StickyRolesCog", "db_namespace": "sticky_roles_config"},
    "counters": {"cog": "CountersCog", "db_namespace": "counters_config"},
    "starboard": {"cog": "StarboardCog", "db_namespace": "starboard_config"},
    "suggestions": {"cog": "SuggestionsCog", "db_namespace": "suggestions_config"},
    "birthdays": {"cog": "BirthdaysCog", "db_namespace": "birthdays_config"},
    "embeds": {"cog": "EmbedBuilderCog", "db_namespace": "embeds_config"},
    "timers": {"cog": "TimersCog", "db_namespace": "timers_config"},
    "sticky_messages": {"cog": "StickyMsgCog", "db_namespace": "sticky_msg_config"},
    "notifications": {"cog": "SocialAlertsCog", "db_namespace": "social_alerts_config"},
    "automations": {"cog": "AutomationsCog", "db_namespace": "automations_config"},
    "custom_commands": {"cog": "CustomCmdsCog", "db_namespace": "custom_cmds_config"},
    "temp_channels": {"cog": "TempVoiceCog", "db_namespace": "temp_voice_config"},
    "roleplay": {"cog": "RoleplayCog", "db_namespace": "roleplay_config"},
    "analytics": {"cog": "AnalyticsCog", "db_namespace": "analytics_config"},
    "connect": {"cog": "WebhooksApiCog", "db_namespace": "connect_api_config"},
    "verify": {"cog": "VerificationCog", "db_namespace": "verification_config"},
    "invite_tracker": {"cog": "InviteTrackerCog", "db_namespace": "invite_tracker_config"},
    "polls": {"cog": "PollsVotingCog", "db_namespace": "polls_voting_config"}
}

DEFAULT_LEVEL_CONFIG = {
    "name": "Discord Guild",
    "enabled": True,
    "theme": "crimson",
    "default_card_style": "bento",
    "default_avatar_shape": "auto",
    "bg_url": None,
    "levelup_bg_url": None,
    "multiplier": 1.0,
    "notify_mode": "current",
    "level_channel": None,
    "levelup_message": "GG {user.mention}, you just advanced to **Level {level}**!",
    "send_text": True,
    "send_card": True,
    "xp_text": True,
    "xp_voice": True,
    "xp_threads": True,
    "min_xp": 15,
    "max_xp": 25,
    "cooldown_seconds": 5,
    "voice_xp_per_min": 10,
    "ignored_channels": [],
    "ignored_roles": [],
    "boosted_channels": [],
    "role_rewards": {},
    "stack_roles": True,
    "role_multipliers": {},
    "command_toggles": {
        "rank": True,
        "leaderboard": True,
        "daily": True,
        "prestige": True,
        "mycard": True,
        "xpstats": True,
        "rewards": True
    },
    "users": {}
}


# =====================================================================
# CUSTOMIZABLE STATUS BAR & GLOBAL BOT CONFIG HELPER (web/bot_status.json)
# =====================================================================

def load_bot_status_config() -> dict:
    """
    Loads customizable status bar & telemetry settings from `web/bot_status.json`.
    Automatically creates the file if it doesn't exist so you can edit it anytime!
    """
    os.makedirs(os.path.dirname(STATUS_CONFIG_FILE), exist_ok=True)
    if not os.path.exists(STATUS_CONFIG_FILE):
        try:
            with open(STATUS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_BOT_STATUS_CONFIG, f, indent=4)
        except Exception:
            pass
        return dict(DEFAULT_BOT_STATUS_CONFIG)

    try:
        with open(STATUS_CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return dict(DEFAULT_BOT_STATUS_CONFIG)
            changed = False
            for k, v in DEFAULT_BOT_STATUS_CONFIG.items():
                if k not in data:
                    data[k] = v
                    changed = True
            if changed:
                save_bot_status_config(data)
            return data
    except Exception:
        return dict(DEFAULT_BOT_STATUS_CONFIG)


def save_bot_status_config(data: dict):
    """Save updated status bar configuration back to `web/bot_status.json`."""
    os.makedirs(os.path.dirname(STATUS_CONFIG_FILE), exist_ok=True)
    with open(STATUS_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


# =====================================================================
# DATABASE / JSON STORAGE HELPERS (SHARED WITH DISCORD BOT)
# =====================================================================

def load_settings():
    """Load general server settings from JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    """Save general server settings to JSON file."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def ensure_guild_settings(all_settings: dict, guild_id: str, guild_name: str = "Discord Guild") -> dict:
    """Ensure a guild has complete default settings and all 28 module & cog states initialized."""
    gid = str(guild_id)
    if gid not in all_settings or not isinstance(all_settings[gid], dict):
        all_settings[gid] = {}

    defaults = {
        'name': guild_name,
        'prefix': '!',
        'is_premium': False,
        'premium_plan': 'Free',
        'leveling_enabled': True,
        'theme': 'crimson',
        'bg_url': '',
        'multiplier': 1.0,
        'economy_enabled': True,
        'currency_name': 'Coins',
        'starting_balance': 1000,
        'automod_enabled': True,
        'welcome_enabled': True,
        'welcome_msg': 'Welcome to the server!',
        'bot_nickname': 'Sofiya',
        'bot_avatar': '',
        'bot_banner': '',
        'bot_bio': f'One Discord app for {guild_name}, built to grow with you.',
        'bot_status': f'Watching over {guild_name}',
        'modules': json.loads(json.dumps(DEFAULT_MODULES_STATE)),
        'cog_states': {},
        'module_configs': {},
        'audit_logs': []
    }

    changed = False
    for k, v in defaults.items():
        if k not in all_settings[gid]:
            all_settings[gid][k] = json.loads(json.dumps(v))
            changed = True

    # Ensure all 28 module keys exist inside 'modules' and 'cog_states'
    if not isinstance(all_settings[gid].get('modules'), dict):
        all_settings[gid]['modules'] = json.loads(json.dumps(DEFAULT_MODULES_STATE))
        changed = True
    else:
        for mod_key, mod_val in DEFAULT_MODULES_STATE.items():
            if mod_key not in all_settings[gid]['modules']:
                all_settings[gid]['modules'][mod_key] = mod_val
                changed = True

    if not isinstance(all_settings[gid].get('cog_states'), dict):
        all_settings[gid]['cog_states'] = {}
        changed = True

    for mod_key, cog_meta in MODULE_COG_MAP.items():
        cog_name = cog_meta["cog"]
        if cog_name not in all_settings[gid]['cog_states']:
            all_settings[gid]['cog_states'][cog_name] = bool(all_settings[gid]['modules'].get(mod_key, True))
            changed = True

    if guild_name and guild_name != "Discord Guild" and all_settings[gid].get('name') != guild_name:
        all_settings[gid]['name'] = guild_name
        changed = True

    if changed:
        save_settings(all_settings)

    return all_settings[gid]


def record_audit_log(all_settings: dict, guild_id: str, action_text: str):
    """Record dashboard configuration changes with user and timestamp (last 50 entries)."""
    gid = str(guild_id)
    settings = ensure_guild_settings(all_settings, gid)
    user_obj = session.get('user') or {}
    actor = user_obj.get('username', 'Admin')
    logs = settings.setdefault('audit_logs', [])
    logs.insert(0, {
        "user": actor,
        "action": action_text,
        "timestamp": int(time.time())
    })
    settings['audit_logs'] = logs[:50]


def load_levels_data():
    """Load leveling data from levels_v3.json storage."""
    os.makedirs(os.path.dirname(LEVELS_FILE), exist_ok=True)
    if not os.path.exists(LEVELS_FILE):
        return {"guilds": {}}
    try:
        with open(LEVELS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and "guilds" in data:
                return data
            return {"guilds": {}}
    except Exception:
        return {"guilds": {}}


def save_levels_data(data):
    """Save leveling data back to levels_v3.json storage."""
    os.makedirs(os.path.dirname(LEVELS_FILE), exist_ok=True)
    with open(LEVELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


def get_guild_level_config(levels_data: dict, guild_id: str, guild_name: str = "Discord Guild") -> dict:
    """Retrieve or initialize leveling configuration for a specific guild."""
    guilds = levels_data.setdefault("guilds", {})
    gid = str(guild_id)
    if gid not in guilds:
        guilds[gid] = json.loads(json.dumps(DEFAULT_LEVEL_CONFIG))
        guilds[gid]["name"] = guild_name
        save_levels_data(levels_data)
    else:
        for k, v in DEFAULT_LEVEL_CONFIG.items():
            if k not in guilds[gid]:
                guilds[gid][k] = json.loads(json.dumps(v))
        if guild_name and guild_name != "Discord Guild":
            guilds[gid]["name"] = guild_name
    return guilds[gid]


def parse_id_list(raw_str: str) -> list:
    """Parse comma-separated string of IDs into a unique integer list."""
    if not raw_str:
        return []
    ids = []
    for item in raw_str.replace(" ", "").split(","):
        if item.isdigit():
            ids.append(int(item))
    return list(dict.fromkeys(ids))


# =====================================================================
# DISCORD API REAL-TIME FETCHERS (BOT PRESENCE, GUILDS, DP/ICONS, CHANNELS, ROLES)
# =====================================================================

def get_bot_token() -> str:
    """Retrieve Discord Bot Token from environment variables."""
    return (
        os.getenv("DISCORD_TOKEN")
        or os.getenv("BOT_TOKEN")
        or os.getenv("TOKEN")
        or ""
    ).strip()


def fetch_bot_guild_ids(force_refresh: bool = False) -> set:
    """
    Fetch the exact set of Guild IDs where Sofiya Bot is currently installed.
    Uses Discord Bot Token (`/users/@me/guilds`) + local storage fallback.
    """
    now = time.time()
    bot_token = get_bot_token()

    if not force_refresh and _BOT_GUILDS_CACHE["timestamp"] > 0 and (now - _BOT_GUILDS_CACHE["timestamp"]) < 30:
        return set(_BOT_GUILDS_CACHE["guild_ids"])

    joined_ids = set()
    token_worked = False

    if bot_token:
        try:
            headers = {"Authorization": f"Bot {bot_token}"}
            resp = requests.get(f"{DISCORD_API_BASE}/users/@me/guilds", headers=headers, timeout=5)
            if resp.status_code == 200:
                token_worked = True
                for g in resp.json():
                    if g.get("id"):
                        joined_ids.add(str(g["id"]))
        except Exception as e:
            print(f"Error fetching bot guilds: {e}")

    # Also include any guilds already initialized in levels_v3.json or server_settings.json
    # when bot token is not yet active in local dev environment
    if not token_worked:
        all_settings = load_settings()
        levels_data = load_levels_data()
        for gid in all_settings.keys():
            joined_ids.add(str(gid))
        for gid in levels_data.get("guilds", {}).keys():
            joined_ids.add(str(gid))

    _BOT_GUILDS_CACHE["guild_ids"] = joined_ids
    _BOT_GUILDS_CACHE["timestamp"] = now
    _BOT_GUILDS_CACHE["token_valid"] = token_worked
    return set(joined_ids)


def get_display_bot_guild_count() -> str:
    """
    Returns the formatted live server count where the bot is joined,
    or uses your custom setting from `web/bot_status.json`.
    """
    status_cfg = load_bot_status_config()
    if status_cfg.get("custom_server_count_override"):
        return str(status_cfg["custom_server_count_override"])

    if status_cfg.get("use_live_bot_guild_count", True):
        bot_guild_ids = fetch_bot_guild_ids()
        if len(bot_guild_ids) > 0:
            return f"{len(bot_guild_ids):,}"

    return str(status_cfg.get("fallback_server_count_display", "1,600,000+"))


def is_bot_in_guild(guild_id: str, force_refresh: bool = False) -> bool:
    """Check if the bot is present in a specific Discord server."""
    gid = str(guild_id)
    bot_guild_ids = fetch_bot_guild_ids(force_refresh=force_refresh)
    if gid in bot_guild_ids:
        return True

    # Direct single-guild check fallback if Bot Token is configured
    bot_token = get_bot_token()
    if bot_token:
        try:
            headers = {"Authorization": f"Bot {bot_token}"}
            resp = requests.get(f"{DISCORD_API_BASE}/guilds/{gid}", headers=headers, timeout=4)
            if resp.status_code == 200:
                _BOT_GUILDS_CACHE["guild_ids"].add(gid)
                return True
        except Exception:
            pass
    return False


def build_bot_invite_url(guild_id: str = None) -> str:
    """Build official Discord OAuth2 Bot Invite URL pre-selecting the server."""
    base_url = (
        f"{DISCORD_API_BASE}/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&permissions=8"
        f"&scope=bot%20applications.commands"
    )
    if guild_id:
        base_url += f"&guild_id={guild_id}&disable_guild_select=true"
    return base_url


def fetch_user_admin_guilds(access_token: str, force_refresh: bool = False) -> list:
    """
    Fetch user's guilds from Discord OAuth2 with smart session caching,
    and enrich each guild with `bot_connected` and `invite_url`.
    """
    if not access_token:
        return []

    now = time.time()
    cached_guilds = session.get('cached_admin_guilds')
    cached_ts = session.get('cached_guilds_ts', 0)

    admin_guilds = None
    if not force_refresh and cached_guilds is not None and (now - cached_ts) < 45:
        admin_guilds = cached_guilds
    else:
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f'{DISCORD_API_BASE}/users/@me/guilds', headers=headers, timeout=5)
            if response.status_code == 200:
                guilds = response.json()
                admin_guilds = []
                for guild in guilds:
                    perms = int(guild.get('permissions', 0))
                    # Owner or Administrator (0x8) or Manage Guild (0x20)
                    if guild.get('owner') or (perms & 0x8) == 0x8 or (perms & 0x20) == 0x20:
                        admin_guilds.append(guild)
                session['cached_admin_guilds'] = admin_guilds
                session['cached_guilds_ts'] = now
        except Exception as e:
            print(f"Error fetching user guilds: {e}")

    if admin_guilds is None:
        admin_guilds = cached_guilds if cached_guilds is not None else []

    # Enrich every admin guild with real bot connection status & sort connected first
    bot_guild_ids = fetch_bot_guild_ids(force_refresh=force_refresh)
    for idx, g in enumerate(admin_guilds):
        gid = str(g.get('id', ''))
        if bot_guild_ids:
            is_conn = gid in bot_guild_ids
        else:
            # Fallback if no guilds registered yet: mark first server as connected for preview
            is_conn = (idx == 0)
        g['bot_connected'] = is_conn
        g['invite_url'] = build_bot_invite_url(gid)

    # Sort so connected servers appear first (matching dashboard.html loop.first expectation)
    admin_guilds.sort(key=lambda item: (0 if item.get('bot_connected') else 1, item.get('name', '').lower()))
    return admin_guilds


def get_guild_identity(guild_id: str, access_token: str) -> dict:
    """
    Resolve real server name, real server DP (guild_icon URL), and owner status
    from user's OAuth2 guilds or Bot Token fallback.
    """
    gid = str(guild_id)
    guild_name = "Discord Guild"
    guild_icon = None
    is_owner = False

    admin_guilds = fetch_user_admin_guilds(access_token)
    for g in admin_guilds:
        if str(g.get('id')) == gid:
            guild_name = g.get('name', 'Discord Guild')
            icon_hash = g.get('icon')
            if icon_hash:
                ext = "gif" if str(icon_hash).startswith("a_") else "png"
                guild_icon = f"https://cdn.discordapp.com/icons/{gid}/{icon_hash}.{ext}?size=128"
            is_owner = bool(g.get('owner'))
            break

    # Fallback: Check via Bot Token if icon/name wasn't in cached list
    bot_token = get_bot_token()
    if bot_token and (guild_name == "Discord Guild" or not guild_icon):
        try:
            headers = {"Authorization": f"Bot {bot_token}"}
            resp = requests.get(f"{DISCORD_API_BASE}/guilds/{gid}", headers=headers, timeout=4)
            if resp.status_code == 200:
                gdata = resp.json()
                guild_name = gdata.get("name", guild_name)
                icon_hash = gdata.get("icon")
                if icon_hash:
                    ext = "gif" if str(icon_hash).startswith("a_") else "png"
                    guild_icon = f"https://cdn.discordapp.com/icons/{gid}/{icon_hash}.{ext}?size=128"
        except Exception:
            pass

    return {
        "id": gid,
        "name": guild_name,
        "icon": guild_icon,
        "owner": is_owner,
        "bot_connected": is_bot_in_guild(gid)
    }


def fetch_guild_channels(guild_id: str) -> list:
    """Fetch text and announcement channels from Discord API using Bot Token."""
    channels = []
    bot_token = get_bot_token()
    if not bot_token:
        return channels
    try:
        headers = {"Authorization": f"Bot {bot_token}"}
        resp = requests.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/channels", headers=headers, timeout=4)
        if resp.status_code == 200:
            for ch in resp.json():
                # Type 0 = Text Channel, Type 5 = Announcement Channel
                if ch.get("type") in [0, 5]:
                    channels.append({"id": str(ch["id"]), "name": ch["name"]})
    except Exception as e:
        print(f"Error fetching channels: {e}")
    return channels


def fetch_guild_roles(guild_id: str) -> list:
    """Fetch server roles from Discord API using Bot Token."""
    roles = []
    bot_token = get_bot_token()
    if not bot_token:
        return roles
    try:
        headers = {"Authorization": f"Bot {bot_token}"}
        resp = requests.get(f"{DISCORD_API_BASE}/guilds/{guild_id}/roles", headers=headers, timeout=4)
        if resp.status_code == 200:
            for r in resp.json():
                if r.get("name") != "@everyone" and not r.get("managed", False):
                    roles.append({"id": str(r["id"]), "name": r["name"]})
    except Exception as e:
        print(f"Error fetching roles: {e}")
    return roles


def save_full_level_and_general_form(guild_id: str, guild_name: str, all_settings: dict, levels_data: dict, lconfig: dict) -> str:
    """
    Process and save all form fields submitted from manage_level.html (or legacy manage.html).
    Preserves 100% of your original POST saving logic and syncs module & cog states.
    """
    gid = str(guild_id)
    ensure_guild_settings(all_settings, gid, guild_name)

    all_settings[gid]['prefix'] = request.form.get('prefix', '!')
    all_settings[gid]['leveling_enabled'] = 'leveling_enabled' in request.form
    all_settings[gid]['theme'] = request.form.get('theme', 'crimson')
    all_settings[gid]['bg_url'] = request.form.get('bg_url', '').strip()

    try:
        mult_val = max(0.25, min(float(request.form.get('multiplier', 1.0)), 10.0))
    except ValueError:
        mult_val = 1.0
    all_settings[gid]['multiplier'] = mult_val

    all_settings[gid]['economy_enabled'] = 'economy_enabled' in request.form
    all_settings[gid]['currency_name'] = request.form.get('currency_name', 'Coins')

    try:
        all_settings[gid]['starting_balance'] = int(request.form.get('starting_balance', 1000))
    except ValueError:
        all_settings[gid]['starting_balance'] = 1000

    all_settings[gid]['automod_enabled'] = 'automod_enabled' in request.form
    all_settings[gid]['welcome_enabled'] = 'welcome_enabled' in request.form
    all_settings[gid]['welcome_msg'] = request.form.get('welcome_msg', '')

    # Sync with the 28-module state dictionary & Bot Cogs so manage.html switches stay in sync
    all_settings[gid]['modules']['level'] = all_settings[gid]['leveling_enabled']
    all_settings[gid]['modules']['economy'] = all_settings[gid]['economy_enabled']
    all_settings[gid]['modules']['moderation'] = all_settings[gid]['automod_enabled']
    all_settings[gid]['modules']['welcomer'] = all_settings[gid]['welcome_enabled']

    all_settings[gid]['cog_states']['LevelingCog'] = all_settings[gid]['leveling_enabled']
    all_settings[gid]['cog_states']['EconomyCog'] = all_settings[gid]['economy_enabled']
    all_settings[gid]['cog_states']['ModerationCog'] = all_settings[gid]['automod_enabled']
    all_settings[gid]['cog_states']['WelcomerCog'] = all_settings[gid]['welcome_enabled']

    record_audit_log(all_settings, gid, "Updated Leveling & Server configuration")
    save_settings(all_settings)

    lconfig["name"] = guild_name
    lconfig["enabled"] = all_settings[gid]['leveling_enabled']
    lconfig["theme"] = all_settings[gid]['theme']
    lconfig["default_card_style"] = request.form.get('default_card_style', 'bento')
    lconfig["default_avatar_shape"] = request.form.get('default_avatar_shape', 'auto')

    bg_clean = all_settings[gid]['bg_url']
    lconfig["bg_url"] = bg_clean if bg_clean else None
    lconfig["levelup_bg_url"] = request.form.get('levelup_bg_url', '').strip() or None
    lconfig["multiplier"] = mult_val

    lconfig["notify_mode"] = request.form.get('notify_mode', 'current')
    raw_lvl_ch = request.form.get('level_channel', '').strip()
    lconfig["level_channel"] = int(raw_lvl_ch) if raw_lvl_ch.isdigit() else None
    lconfig["levelup_message"] = request.form.get(
        'levelup_message',
        'GG {user.mention}, you just advanced to **Level {level}**!'
    ).strip()
    lconfig["send_text"] = 'send_text' in request.form
    lconfig["send_card"] = 'send_card' in request.form

    lconfig["xp_text"] = 'xp_text' in request.form
    lconfig["xp_voice"] = 'xp_voice' in request.form
    lconfig["xp_threads"] = 'xp_threads' in request.form

    try:
        lconfig["min_xp"] = max(1, min(int(request.form.get('min_xp', 15)), 500))
        lconfig["max_xp"] = max(lconfig["min_xp"], min(int(request.form.get('max_xp', 25)), 1000))
    except ValueError:
        lconfig["min_xp"], lconfig["max_xp"] = 15, 25

    try:
        lconfig["cooldown_seconds"] = max(0, min(int(request.form.get('cooldown_seconds', 5)), 300))
    except ValueError:
        lconfig["cooldown_seconds"] = 5

    try:
        lconfig["voice_xp_per_min"] = max(1, min(int(request.form.get('voice_xp_per_min', 10)), 500))
    except ValueError:
        lconfig["voice_xp_per_min"] = 10

    lconfig["ignored_channels"] = parse_id_list(request.form.get('ignored_channels', ''))
    lconfig["ignored_roles"] = parse_id_list(request.form.get('ignored_roles', ''))
    lconfig["boosted_channels"] = parse_id_list(request.form.get('boosted_channels', ''))
    lconfig["stack_roles"] = 'stack_roles' in request.form

    cmd_toggles = {}
    for cmd_name in ["rank", "leaderboard", "daily", "prestige", "mycard", "xpstats", "rewards"]:
        cmd_toggles[cmd_name] = f"cmd_{cmd_name}" in request.form
    lconfig["command_toggles"] = cmd_toggles

    save_levels_data(levels_data)
    return "All changes successfully saved and synchronized!"


def get_redirect_target_after_level_action(guild_id: str, msg: str):
    """Redirect back to manage_level_module if action came from /level, otherwise manage_server."""
    ref = request.referrer or ""
    if f"/manage/{guild_id}/level" in ref:
        return redirect(url_for('manage_level_module', guild_id=guild_id, success=msg))
    return redirect(url_for('manage_server', guild_id=guild_id, success=msg))


# =====================================================================
# AUTOMATIC FRONTEND <-> BACKEND LIVE BRIDGE (100% PRESERVED + 28 MODULES)
# =====================================================================

@app.after_request
def inject_live_bot_bridge(response):
    """
    Automatically injects a lightweight live-sync script into `/`, `/dashboard`, and `/manage/<guild_id>`
    so that:
      1. `index.html` automatically receives custom status bar settings from `web/bot_status.json`!
      2. `dashboard.html` automatically shows real 'Manage server' vs 'Add Sofiya' buttons
         and routes 'Add Sofiya' to `/invite/<guild_id>`!
      3. `manage.html` automatically saves every module switch toggle, Enable All, Pause All,
         and Quick-Tune setting directly to `server_settings.json` & `levels_v3.json`!
    """
    try:
        if response.status_code != 200 or not response.content_type.startswith('text/html'):
            return response
        if response.direct_passthrough:
            return response

        path = request.path or ""

        # 0. Auto-Bridge for / (Index Page Status Bar & Custom Promo Sync from web/bot_status.json)
        if path == '/':
            status_cfg = load_bot_status_config()
            display_count = get_display_bot_guild_count()
            index_bridge_js = f"""
<script>
(function() {{
    const STATUS_CFG = {json.dumps(status_cfg)};
    const DISPLAY_COUNT = {json.dumps(display_count)};
    try {{
        const promoEl = document.getElementById('heroPromoText');
        if (promoEl && STATUS_CFG.promo_text) promoEl.textContent = STATUS_CFG.promo_text;
        const countEl = document.getElementById('liveBotServerCount');
        if (countEl && DISPLAY_COUNT) countEl.textContent = DISPLAY_COUNT;
        const pingEl = document.getElementById('clusterPing');
        if (pingEl && STATUS_CFG.default_ping_ms) pingEl.textContent = STATUS_CFG.default_ping_ms + 'ms';
        const bridgeLbl = document.getElementById('liveBridgeServerLabel');
        if (bridgeLbl && !{json.dumps(bool(session.get('user')))} && STATUS_CFG.status_bar_text) {{
            bridgeLbl.textContent = STATUS_CFG.status_bar_text;
        }}
    }} catch (e) {{}}
}})();
</script>
"""
            html_text = response.get_data(as_text=True)
            if "</body>" in html_text:
                response.set_data(html_text.replace("</body>", index_bridge_js + "\n</body>", 1))

        # 1. Auto-Bridge for /dashboard (Manage server vs Add Sofiya)
        elif path == '/dashboard' and session.get('access_token'):
            admin_guilds = session.get('cached_admin_guilds') or []
            bot_guild_ids = fetch_bot_guild_ids()
            token_active = _BOT_GUILDS_CACHE.get("token_valid", False)

            conn_map = {}
            for idx, g in enumerate(admin_guilds):
                gid = str(g.get('id', ''))
                if token_active or bot_guild_ids:
                    conn_map[gid] = (gid in bot_guild_ids)
                else:
                    conn_map[gid] = (idx == 0)

            bridge_js = f"""
<script>
(function() {{
    const SERVER_CONN_MAP = {json.dumps(conn_map)};
    const TOKEN_ACTIVE = {json.dumps(token_active)};
    try {{
        let existing = JSON.parse(localStorage.getItem('sofiya_connected_servers_v2')) || {{}};
        let merged = TOKEN_ACTIVE ? SERVER_CONN_MAP : Object.assign({{}}, SERVER_CONN_MAP, existing);
        localStorage.setItem('sofiya_connected_servers_v2', JSON.stringify(merged));
    }} catch (e) {{}}

    function syncActionButtonsToInviteOrManage() {{
        document.querySelectorAll('.guild-card').forEach(card => {{
            const gid = card.getAttribute('data-guild-id');
            const isConn = card.getAttribute('data-connected') === 'true';
            const btn = card.querySelector('.action-btn');
            const label = card.querySelector('.action-btn-label');
            if (!btn || !gid) return;
            if (isConn) {{
                btn.setAttribute('href', '/manage/' + gid);
                if (label) label.textContent = 'Manage server';
            }} else {{
                btn.setAttribute('href', '/invite/' + gid);
                if (label) label.textContent = 'Add Sofiya';
            }}
        }});
    }}

    if (typeof initServerStates === 'function') {{
        initServerStates();
    }}
    syncActionButtonsToInviteOrManage();

    if (typeof window.applyCardConnectionUI === 'function') {{
        const origApply = window.applyCardConnectionUI;
        window.applyCardConnectionUI = function(card, isConn) {{
            origApply(card, isConn);
            syncActionButtonsToInviteOrManage();
        }};
        syncActionButtonsToInviteOrManage();
    }}
}})();
</script>
"""
            html_text = response.get_data(as_text=True)
            if "</body>" in html_text:
                response.set_data(html_text.replace("</body>", bridge_js + "\n</body>", 1))

        # 2. Auto-Bridge for /manage/<guild_id> (Live 28-Module Backend Sync)
        elif path.startswith('/manage/') and path.count('/') == 2 and session.get('access_token'):
            guild_id = path.split('/')[-1]
            all_settings = load_settings()
            settings = ensure_guild_settings(all_settings, guild_id)
            backend_modules = settings.get('modules', DEFAULT_MODULES_STATE)

            bridge_js = f"""
<script>
(function() {{
    const GID = {json.dumps(str(guild_id))};
    const S_KEY = 'sofiya_modules_state_' + GID;
    const BACKEND_MODS = {json.dumps(backend_modules)};

    try {{
        localStorage.setItem(S_KEY, JSON.stringify(BACKEND_MODS));
        if (typeof initModuleSwitches === 'function') {{
            initModuleSwitches();
        }}
    }} catch (e) {{}}
}})();
</script>
"""
            html_text = response.get_data(as_text=True)
            if "</body>" in html_text:
                response.set_data(html_text.replace("</body>", bridge_js + "\n</body>", 1))
    except Exception as e:
        print(f"Bridge injection warning: {e}")

    return response


# =====================================================================
# PUBLIC, BOT INVITE, DIRECT PREMIUM & DASHBOARD WEB ROUTES
# =====================================================================

@app.route('/')
def index():
    access_token = session.get('access_token')
    admin_guilds = fetch_user_admin_guilds(access_token) if access_token else []
    bot_status_cfg = load_bot_status_config()
    bot_guild_count = get_display_bot_guild_count()

    return render_template(
        'index.html',
        user=session.get('user'),
        guilds=admin_guilds,
        bot_guild_count=bot_guild_count,
        bot_status_config=bot_status_cfg
    )


@app.route('/features')
def features():
    try:
        return render_template('features.html', user=session.get('user'))
    except TemplateNotFound:
        return redirect(url_for('index') + '#bento-features')


@app.route('/commands')
def commands():
    try:
        return render_template('commands.html', user=session.get('user'))
    except TemplateNotFound:
        return redirect(url_for('index') + '#bento-features')


@app.route('/tutorials')
def tutorials():
    try:
        return render_template('tutorials.html', user=session.get('user'))
    except TemplateNotFound:
        return redirect(url_for('index') + '#modules-cloud')


@app.route('/invite')
@app.route('/invite/<guild_id>')
def invite_bot(guild_id=None):
    """
    Redirects user to Discord OAuth2 Bot Authorization page for the selected server.
    When user clicks 'Add Sofiya' on dashboard.html, this opens the exact server invite screen.
    """
    return redirect(build_bot_invite_url(guild_id))


@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))

    force_sync = request.args.get('refresh') == '1'
    admin_guilds = fetch_user_admin_guilds(access_token, force_refresh=force_sync)

    return render_template(
        'dashboard.html',
        guilds=admin_guilds,
        user=session.get('user'),
        bot_status_config=load_bot_status_config()
    )


# =====================================================================
# DEDICATED PREMIUM PANEL ROUTES (/premium AND /manage/<guild_id>/premium)
# Directly opens the separate Premium & Custom Branding panel (`manage_premium.html`)
# =====================================================================

@app.route('/premium')
def global_premium_redirect():
    """
    When a user clicks 'Premium' on index.html or navbar, this routes them directly
    to their active server's dedicated Premium panel (`/manage/<guild_id>/premium`)
    or renders `manage_premium.html` / `premium.html` directly!
    """
    access_token = session.get('access_token')
    if access_token:
        admin_guilds = fetch_user_admin_guilds(access_token)
        if admin_guilds:
            return redirect(url_for('manage_premium_panel', guild_id=admin_guilds[0]['id']))

    try:
        return render_template(
            'manage_premium.html',
            guild_name='Your Discord Server',
            guild_icon=None,
            guild_id='default_guild',
            settings={},
            guilds=[],
            user=session.get('user')
        )
    except TemplateNotFound:
        try:
            return render_template('premium.html', user=session.get('user'))
        except TemplateNotFound:
            if not access_token:
                return redirect(url_for('auth.login'))
            return redirect(url_for('dashboard'))


@app.route('/manage/<guild_id>/premium', methods=['GET', 'POST'])
@app.route('/manage/<guild_id>/customiser', methods=['GET', 'POST'])
def manage_premium_panel(guild_id):
    """
    Dedicated Server Premium & Custom Bot Branding ($3.50) Route.
    Renders `manage_premium.html` (or `manage_customiser.html`) when created,
    and saves all Premium & Custom Bot Branding settings to `server_settings.json`.
    """
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))

    admin_guilds = fetch_user_admin_guilds(access_token)
    guild_info = get_guild_identity(guild_id, access_token)
    guild_name = guild_info["name"]
    guild_icon = guild_info["icon"]

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id, guild_name)
    guild_channels = fetch_guild_channels(guild_id)
    guild_roles = fetch_guild_roles(guild_id)
    success_msg = request.args.get('success')

    if request.method == 'POST':
        if 'bot_nickname' in request.form:
            settings['bot_nickname'] = request.form.get('bot_nickname', 'Sofiya').strip()
        if 'bot_status' in request.form:
            settings['bot_status'] = request.form.get('bot_status', '').strip()
        if 'bot_avatar' in request.form:
            settings['bot_avatar'] = request.form.get('bot_avatar', '').strip()
        if 'bot_banner' in request.form:
            settings['bot_banner'] = request.form.get('bot_banner', '').strip()
        if 'bot_bio' in request.form:
            settings['bot_bio'] = request.form.get('bot_bio', '').strip()
        if 'is_premium' in request.form or 'activate_premium' in request.form:
            settings['is_premium'] = True
            settings['premium_plan'] = request.form.get('premium_plan', 'Premium Pro')

        record_audit_log(all_settings, guild_id, "Updated Server Premium & Custom Bot Branding")
        save_settings(all_settings)
        success_msg = "Premium Pro & Custom Bot Branding synchronized with Sofiya!"

    context = dict(
        guild_name=guild_name,
        guild_icon=guild_icon,
        guild_owner=guild_info["owner"],
        bot_connected=guild_info["bot_connected"],
        guilds=admin_guilds,
        settings=settings,
        modules_state=settings.get('modules', DEFAULT_MODULES_STATE),
        guild_channels=guild_channels,
        guild_roles=guild_roles,
        guild_id=guild_id,
        user=session.get('user'),
        success=success_msg
    )

    # Check if the user has created `manage_premium.html` or `manage_customiser.html`
    if request.path.endswith('/customiser'):
        for tpl in ['manage_customiser.html', 'manage_premium.html', 'manage.html']:
            try:
                return render_template(tpl, **context)
            except TemplateNotFound:
                continue
    else:
        for tpl in ['manage_premium.html', 'manage_customiser.html', 'manage.html']:
            try:
                return render_template(tpl, **context)
            except TemplateNotFound:
                continue

    return render_template('manage.html', **context)


# =====================================================================
# MAIN 28-MODULE HUB ROUTE (/manage/<guild_id>)
# =====================================================================

@app.route('/manage/<guild_id>', methods=['GET', 'POST'])
def manage_server(guild_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))

    admin_guilds = fetch_user_admin_guilds(access_token)
    guild_info = get_guild_identity(guild_id, access_token)
    guild_name = guild_info["name"]
    guild_icon = guild_info["icon"]

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id, guild_name)

    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id, guild_name)
    guild_channels = fetch_guild_channels(guild_id)
    guild_roles = fetch_guild_roles(guild_id)
    success_msg = request.args.get('success')

    # If a form is POSTed to url_for('manage_server', guild_id=guild_id) from manage_level.html
    if request.method == 'POST':
        success_msg = save_full_level_and_general_form(guild_id, guild_name, all_settings, levels_data, lconfig)
        settings = all_settings[str(guild_id)]
        # If the POST came from the dedicated /level page, keep the user on /level
        ref = request.referrer or ""
        if f"/manage/{guild_id}/level" in ref:
            return redirect(url_for('manage_level_module', guild_id=guild_id, success=success_msg))

    users_dict = lconfig.get("users", {})
    top_users = sorted(
        users_dict.items(),
        key=lambda x: (x[1].get("prestige", 0), x[1].get("level", 0), x[1].get("xp", 0)),
        reverse=True
    )[:10]

    return render_template(
        'manage.html',
        guild_name=guild_name,
        guild_icon=guild_icon,
        guild_owner=guild_info["owner"],
        bot_connected=guild_info["bot_connected"],
        guilds=admin_guilds,
        settings=settings,
        modules_state=settings.get('modules', DEFAULT_MODULES_STATE),
        level_config=lconfig,
        guild_channels=guild_channels,
        guild_roles=guild_roles,
        top_users=top_users,
        guild_id=guild_id,
        user=session.get('user'),
        success=success_msg
    )


# =====================================================================
# DEDICATED LEVELING MODULE ROUTE (/manage/<guild_id>/level)
# Renders `manage_level.html` (or falls back to `manage.html` if not renamed yet)
# =====================================================================

@app.route('/manage/<guild_id>/level', methods=['GET', 'POST'])
@app.route('/manage/<guild_id>/levels', methods=['GET', 'POST'])
def manage_level_module(guild_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))

    admin_guilds = fetch_user_admin_guilds(access_token)
    guild_info = get_guild_identity(guild_id, access_token)
    guild_name = guild_info["name"]
    guild_icon = guild_info["icon"]

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id, guild_name)

    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id, guild_name)
    guild_channels = fetch_guild_channels(guild_id)
    guild_roles = fetch_guild_roles(guild_id)
    success_msg = request.args.get('success')

    if request.method == 'POST':
        success_msg = save_full_level_and_general_form(guild_id, guild_name, all_settings, levels_data, lconfig)
        settings = all_settings[str(guild_id)]

    users_dict = lconfig.get("users", {})
    top_users = sorted(
        users_dict.items(),
        key=lambda x: (x[1].get("prestige", 0), x[1].get("level", 0), x[1].get("xp", 0)),
        reverse=True
    )[:10]

    context = dict(
        guild_name=guild_name,
        guild_icon=guild_icon,
        guild_owner=guild_info["owner"],
        bot_connected=guild_info["bot_connected"],
        guilds=admin_guilds,
        settings=settings,
        level_config=lconfig,
        guild_channels=guild_channels,
        guild_roles=guild_roles,
        top_users=top_users,
        guild_id=guild_id,
        user=session.get('user'),
        success=success_msg
    )

    try:
        return render_template('manage_level.html', **context)
    except TemplateNotFound:
        return render_template('manage.html', **context)


# =====================================================================
# DYNAMIC ROUTER FOR ALL OTHER 27 MODULE PAGES (/manage/<guild_id>/<module_key>)
# Automatically renders `manage_<module_key>.html` when created!
# =====================================================================

@app.route('/manage/<guild_id>/<module_key>', methods=['GET', 'POST'])
def manage_specific_module(guild_id, module_key):
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))

    mod_key = module_key.lower().strip()
    if mod_key in ['level', 'levels']:
        return redirect(url_for('manage_level_module', guild_id=guild_id))
    if mod_key in ['premium', 'customiser']:
        return redirect(url_for('manage_premium_panel', guild_id=guild_id))

    admin_guilds = fetch_user_admin_guilds(access_token)
    guild_info = get_guild_identity(guild_id, access_token)
    guild_name = guild_info["name"]
    guild_icon = guild_info["icon"]

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id, guild_name)
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id, guild_name)
    guild_channels = fetch_guild_channels(guild_id)
    guild_roles = fetch_guild_roles(guild_id)
    success_msg = request.args.get('success')

    cog_meta = MODULE_COG_MAP.get(mod_key, {"cog": "CoreCog", "db_namespace": mod_key})

    if request.method == 'POST':
        # Save custom module-specific form fields into settings['module_configs'][mod_key]
        mod_cfg = settings.setdefault('module_configs', {}).setdefault(mod_key, {})
        for form_k, form_v in request.form.items():
            mod_cfg[form_k] = form_v
        mod_cfg['cog_name'] = cog_meta["cog"]
        mod_cfg['db_namespace'] = cog_meta["db_namespace"]
        mod_cfg['updated_at'] = int(time.time())

        if 'module_enabled' in request.form:
            is_en = request.form.get('module_enabled') in ['true', 'on', '1', 'True']
            settings['modules'][mod_key] = is_en
            settings['cog_states'][cog_meta["cog"]] = is_en

        record_audit_log(all_settings, guild_id, f"Configured {mod_key.replace('_', ' ').title()} ({cog_meta['cog']})")
        save_settings(all_settings)
        success_msg = f"{mod_key.replace('_', ' ').title()} settings saved & synced with {cog_meta['cog']}!"

    context = dict(
        guild_name=guild_name,
        guild_icon=guild_icon,
        guild_owner=guild_info["owner"],
        bot_connected=guild_info["bot_connected"],
        guilds=admin_guilds,
        module_key=mod_key,
        cog_name=cog_meta["cog"],
        db_namespace=cog_meta["db_namespace"],
        settings=settings,
        module_config=settings.get('module_configs', {}).get(mod_key, {}),
        level_config=lconfig,
        guild_channels=guild_channels,
        guild_roles=guild_roles,
        guild_id=guild_id,
        user=session.get('user'),
        success=success_msg
    )

    try:
        return render_template(f'manage_{mod_key}.html', **context)
    except TemplateNotFound:
        # If the dedicated template file hasn't been created yet, redirect safely to the Hub
        return redirect(url_for('manage_server', guild_id=guild_id, success=f"Module '{mod_key}' ({cog_meta['cog']}) ready."))


# =====================================================================
# LEVELING SUB-ACTION ROUTES (100% PRESERVED FROM ORIGINAL app.py)
# =====================================================================

@app.route('/manage/<guild_id>/levels/add_reward', methods=['POST'])
def add_level_reward(guild_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    level_str = request.form.get('reward_level', '').strip()
    role_id_str = request.form.get('reward_role_id', '').strip()
    if level_str.isdigit() and role_id_str.isdigit():
        lvl = max(1, min(int(level_str), 500))
        lconfig["role_rewards"][str(lvl)] = int(role_id_str)
        save_levels_data(levels_data)
        msg = f"Role reward added for Level {lvl}!"
    else:
        msg = "Invalid Level or Role ID."
    return get_redirect_target_after_level_action(guild_id, msg)


@app.route('/manage/<guild_id>/levels/remove_reward/<level>', methods=['POST'])
def remove_level_reward(guild_id, level):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    lconfig.get("role_rewards", {}).pop(str(level), None)
    save_levels_data(levels_data)
    return get_redirect_target_after_level_action(guild_id, f"Removed Role Reward for Level {level}.")


@app.route('/manage/<guild_id>/levels/add_role_multiplier', methods=['POST'])
def add_role_multiplier(guild_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    role_id_str = request.form.get('mult_role_id', '').strip()
    rate_str = request.form.get('mult_rate', '1.5').strip()
    try:
        rate = max(0.5, min(float(rate_str), 10.0))
        if role_id_str.isdigit():
            lconfig.setdefault("role_multipliers", {})[role_id_str] = rate
            save_levels_data(levels_data)
            msg = f"Added {rate}x XP multiplier for Role ID {role_id_str}!"
        else:
            msg = "Invalid Role ID."
    except ValueError:
        msg = "Invalid multiplier rate."
    return get_redirect_target_after_level_action(guild_id, msg)


@app.route('/manage/<guild_id>/levels/remove_role_multiplier/<role_id>', methods=['POST'])
def remove_role_multiplier(guild_id, role_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    lconfig.get("role_multipliers", {}).pop(str(role_id), None)
    save_levels_data(levels_data)
    return get_redirect_target_after_level_action(guild_id, f"Removed multiplier for Role ID {role_id}.")


@app.route('/manage/<guild_id>/levels/user_action', methods=['POST'])
def manage_user_xp(guild_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    user_id = request.form.get('user_id', '').strip()
    action = request.form.get('action', '')
    amount_str = request.form.get('amount', '0').strip()

    if not user_id.isdigit():
        return get_redirect_target_after_level_action(guild_id, "Invalid User ID.")

    users = lconfig.setdefault("users", {})
    udata = users.setdefault(user_id, {
        "name": f"User {user_id[:6]}",
        "xp": 0,
        "level": 0,
        "total_xp": 0,
        "messages": 0,
        "voice_minutes": 0,
        "streak": 0,
        "prestige": 0
    })
    val = int(amount_str) if amount_str.isdigit() else 0

    if action == "give_xp":
        udata["xp"] = udata.get("xp", 0) + val
        udata["total_xp"] = udata.get("total_xp", 0) + val
        while udata["xp"] >= (100 + udata["level"] * 150):
            udata["xp"] -= (100 + udata["level"] * 150)
            udata["level"] += 1
        msg = f"Granted +{val} XP to User {user_id}!"
    elif action == "remove_xp":
        udata["xp"] = max(0, udata.get("xp", 0) - val)
        udata["total_xp"] = max(0, udata.get("total_xp", 0) - val)
        msg = f"Removed {val} XP from User {user_id}."
    elif action == "set_level":
        udata["level"] = max(0, val)
        udata["xp"] = 0
        msg = f"Set User {user_id} to Level {val}!"
    elif action == "reset_user":
        users.pop(user_id, None)
        msg = f"Reset XP data for User {user_id}."
    else:
        msg = "Unknown action."

    save_levels_data(levels_data)
    return get_redirect_target_after_level_action(guild_id, msg)


@app.route('/manage/<guild_id>/levels/reset_all', methods=['POST'])
def reset_all_server_xp(guild_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    lconfig["users"] = {}
    save_levels_data(levels_data)
    return get_redirect_target_after_level_action(guild_id, "All server members have been reset to Level 0 (0 XP)!")


# =====================================================================
# ULTRA NEXT-GEN LIVE REST API ENDPOINTS (REAL-TIME BOT <-> WEB SYNC)
# =====================================================================

@app.route('/api/bot/stats', methods=['GET', 'POST'])
def api_bot_stats():
    """
    GET: Returns live bot server count (`guild_count`) and customizable status bar config from `web/bot_status.json`.
    POST: Allows updating `web/bot_status.json` live if authenticated!
    """
    status_cfg = load_bot_status_config()

    if request.method == 'POST' and session.get('access_token'):
        payload = request.get_json(silent=True) or {}
        for k in DEFAULT_BOT_STATUS_CONFIG.keys():
            if k in payload:
                status_cfg[k] = payload[k]
        save_bot_status_config(status_cfg)

    bot_guild_ids = fetch_bot_guild_ids()
    live_count = len(bot_guild_ids)

    return jsonify({
        "ok": True,
        "guild_count": live_count if live_count > 0 else None,
        "display_server_count": get_display_bot_guild_count(),
        "total_modules": 28,
        "status_config": status_cfg
    })


@app.route('/api/guild/<guild_id>/modules', methods=['GET', 'POST'])
def api_guild_modules(guild_id):
    """
    GET: Returns the live state of all 28 modules & Bot Cogs for this guild.
    POST: Toggles a single module (and its mapped Bot Cog) or bulk-updates all 28 modules in server_settings.json & levels_v3.json.
    """
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id)

    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}

        # Bulk update (Enable All / Pause All)
        if 'bulk_state' in payload:
            b_state = bool(payload['bulk_state'])
            for k, cog_info in MODULE_COG_MAP.items():
                settings['modules'][k] = b_state
                settings['cog_states'][cog_info['cog']] = b_state
            settings['leveling_enabled'] = b_state
            settings['economy_enabled'] = b_state
            settings['automod_enabled'] = b_state
            settings['welcome_enabled'] = b_state
            record_audit_log(all_settings, guild_id, f"{'Enabled' if b_state else 'Paused'} all 28 modules & Bot Cogs")
        # Single module switch toggle
        elif 'module_key' in payload:
            m_key = str(payload['module_key']).strip()
            m_enabled = bool(payload.get('enabled', True))
            cog_info = MODULE_COG_MAP.get(m_key, {"cog": payload.get("cog_name", "CoreCog"), "db_namespace": m_key})
            target_cog = str(payload.get("cog_name") or cog_info["cog"])

            settings['modules'][m_key] = m_enabled
            settings.setdefault('cog_states', {})[target_cog] = m_enabled

            # Keep legacy flags and levels_v3.json in sync for the bot cogs
            if m_key == 'level':
                settings['leveling_enabled'] = m_enabled
                levels_data = load_levels_data()
                lconfig = get_guild_level_config(levels_data, guild_id)
                lconfig['enabled'] = m_enabled
                save_levels_data(levels_data)
            elif m_key == 'economy':
                settings['economy_enabled'] = m_enabled
            elif m_key == 'moderation':
                settings['automod_enabled'] = m_enabled
            elif m_key == 'welcomer':
                settings['welcome_enabled'] = m_enabled

            record_audit_log(all_settings, guild_id, f"{'Enabled' if m_enabled else 'Disabled'} module '{m_key}' ({target_cog})")

        save_settings(all_settings)

    active_count = sum(1 for v in settings['modules'].values() if v)
    return jsonify({
        "ok": True,
        "guild_id": str(guild_id),
        "modules": settings['modules'],
        "cog_states": settings.get('cog_states', {}),
        "active_count": active_count,
        "total_modules": len(DEFAULT_MODULES_STATE)
    })


@app.route('/api/guild/<guild_id>/quick_config', methods=['POST'])
def api_guild_quick_config(guild_id):
    """Save Quick-Tune slide-over drawer settings for any of the 28 modules & their Bot Cogs."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    mod_key = str(payload.get('module_key', 'general')).strip()
    cog_info = MODULE_COG_MAP.get(mod_key, {"cog": "CoreCog", "db_namespace": mod_key})
    target_cog = str(payload.get('cog_name') or cog_info['cog'])
    target_ns = str(payload.get('db_namespace') or cog_info['db_namespace'])

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id)

    if 'enabled' in payload:
        is_en = bool(payload['enabled'])
        settings['modules'][mod_key] = is_en
        settings.setdefault('cog_states', {})[target_cog] = is_en

    mod_configs = settings.setdefault('module_configs', {})
    mod_configs[mod_key] = {
        "cog_name": target_cog,
        "db_namespace": target_ns,
        "channel": payload.get("channel", "default"),
        "access_role": payload.get("access_role", "everyone"),
        "silent_ephemeral": bool(payload.get("silent_ephemeral", False)),
        "exempt_boosters": bool(payload.get("exempt_boosters", True)),
        "updated_at": int(time.time())
    }

    record_audit_log(all_settings, guild_id, f"Quick-tuned module '{mod_key}' ({target_cog})")
    save_settings(all_settings)
    return jsonify({
        "ok": True,
        "guild_id": str(guild_id),
        "module_key": mod_key,
        "cog_name": target_cog,
        "config": mod_configs[mod_key]
    })


@app.route('/api/guild/<guild_id>/branding', methods=['POST'])
def api_guild_branding(guild_id):
    """Save Custom Bot Branding nickname, avatar, banner, bio & status activity for the server."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id)

    settings['bot_nickname'] = str(payload.get('bot_nickname', settings.get('bot_nickname', 'Sofiya'))).strip()
    settings['bot_status'] = str(payload.get('bot_status', settings.get('bot_status', ''))).strip()
    if 'bot_avatar' in payload:
        settings['bot_avatar'] = str(payload.get('bot_avatar', '')).strip()
    if 'bot_banner' in payload:
        settings['bot_banner'] = str(payload.get('bot_banner', '')).strip()
    if 'bot_bio' in payload:
        settings['bot_bio'] = str(payload.get('bot_bio', '')).strip()

    record_audit_log(all_settings, guild_id, f"Updated custom bot branding ({settings['bot_nickname']})")
    save_settings(all_settings)

    return jsonify({
        "ok": True,
        "bot_nickname": settings['bot_nickname'],
        "bot_status": settings['bot_status'],
        "bot_avatar": settings.get('bot_avatar', ''),
        "bot_banner": settings.get('bot_banner', ''),
        "bot_bio": settings.get('bot_bio', '')
    })


@app.route('/api/guild/<guild_id>/diagnostics', methods=['GET'])
def api_guild_diagnostics(guild_id):
    """Live diagnostics check for Initial Setup accordion on manage.html & dashboard.html."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id)
    channels = fetch_guild_channels(guild_id)
    roles = fetch_guild_roles(guild_id)
    active_count = sum(1 for v in settings['modules'].values() if v)

    return jsonify({
        "ok": True,
        "guild_id": str(guild_id),
        "bot_connected": is_bot_in_guild(guild_id),
        "bot_token_configured": bool(get_bot_token()),
        "channels_detected": len(channels),
        "roles_detected": len(roles),
        "active_modules": active_count,
        "total_modules": len(DEFAULT_MODULES_STATE)
    })


@app.route('/api/guild/<guild_id>/audit_logs', methods=['GET'])
def api_guild_audit_logs(guild_id):
    """Return recent dashboard configuration audit logs for this server."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id)
    return jsonify({
        "ok": True,
        "guild_id": str(guild_id),
        "audit_logs": settings.get("audit_logs", [])
    })


@app.route('/api/guild/<guild_id>/backup', methods=['GET'])
def api_guild_backup(guild_id):
    """Export complete 28-module & leveling configuration snapshot for 1-click backup."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    all_settings = load_settings()
    settings = ensure_guild_settings(all_settings, guild_id)
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)

    return jsonify({
        "ok": True,
        "guild_id": str(guild_id),
        "exported_at": int(time.time()),
        "server_settings": settings,
        "level_config": lconfig
    })


@app.route('/api/guild/<guild_id>/restore', methods=['POST'])
def api_guild_restore(guild_id):
    """Restore server settings and leveling config from a JSON backup snapshot."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    all_settings = load_settings()
    levels_data = load_levels_data()

    if isinstance(payload.get("server_settings"), dict):
        all_settings[str(guild_id)] = payload["server_settings"]
        ensure_guild_settings(all_settings, guild_id)
        record_audit_log(all_settings, guild_id, "Restored server configuration from backup")
        save_settings(all_settings)

    if isinstance(payload.get("level_config"), dict):
        levels_data.setdefault("guilds", {})[str(guild_id)] = payload["level_config"]
        save_levels_data(levels_data)

    return jsonify({"ok": True, "guild_id": str(guild_id), "message": "Configuration restored successfully!"})


@app.route('/api/guild/<guild_id>/test_message', methods=['POST'])
def api_guild_test_message(guild_id):
    """Send a live test message to a Discord channel using the Bot Token."""
    if not session.get('access_token'):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    bot_token = get_bot_token()
    if not bot_token:
        return jsonify({"ok": False, "error": "DISCORD_TOKEN not set in .env"}), 400

    payload = request.get_json(silent=True) or {}
    channel_id = str(payload.get("channel_id", "")).strip()
    content = str(payload.get("content", "✅ **Sofiya Dashboard Sync Test:** Your web dashboard is connected to this channel!")).strip()

    if not channel_id.isdigit():
        channels = fetch_guild_channels(guild_id)
        if channels:
            channel_id = channels[0]["id"]
        else:
            return jsonify({"ok": False, "error": "No valid channel ID found."}), 400

    try:
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }
        resp = requests.post(
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            headers=headers,
            json={"content": content},
            timeout=5
        )
        if resp.status_code in [200, 201]:
            return jsonify({"ok": True, "channel_id": channel_id, "message": "Test message sent to Discord!"})
        return jsonify({"ok": False, "error": f"Discord API returned {resp.status_code}"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == '__main__':
    # Ensure customizable status file (`web/bot_status.json`) is created on startup
    load_bot_status_config()
    app.run(debug=True, port=5000)