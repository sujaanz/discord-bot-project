import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, session, request
from dotenv import load_dotenv
from web.auth import auth_bp

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = "sofiya_maki_exact_master_key_2026"

app.register_blueprint(auth_bp, url_prefix='/auth')

SETTINGS_FILE = 'web/server_settings.json'
LEVELS_FILE = 'bot/data/levels_v3.json'

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


def load_settings():
    """Load general server settings from JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_settings(data):
    """Save general server settings to JSON file."""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)


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
    except:
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


def fetch_guild_channels(guild_id: str) -> list:
    """Fetch text and announcement channels from Discord API using Bot Token."""
    channels = []
    bot_token = os.getenv("DISCORD_TOKEN", "")
    if not bot_token:
        return channels
    try:
        headers = {"Authorization": f"Bot {bot_token}"}
        resp = requests.get(f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers, timeout=4)
        if resp.status_code == 200:
            for ch in resp.json():
                # Type 0 = Text Channel, Type 5 = Announcement Channel
                if ch.get("type") in [0, 5]:
                    channels.append({"id": str(ch["id"]), "name": ch["name"]})
    except Exception as e:
        print(f"Error fetching channels: {e}")
    return channels


@app.route('/')
def index():
    return render_template('index.html', user=session.get('user'))


@app.route('/features')
def features():
    return render_template('features.html', user=session.get('user'))


@app.route('/commands')
def commands():
    return render_template('commands.html', user=session.get('user'))


@app.route('/tutorials')
def tutorials():
    return render_template('tutorials.html', user=session.get('user'))


@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))
    
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers)
    
    if response.status_code != 200:
        return "Failed to fetch guilds from Discord."
        
    guilds = response.json()
    admin_guilds = []
    for guild in guilds:
        perms = int(guild.get('permissions', 0))
        if guild.get('owner') or (perms & 0x8) == 0x8:
            admin_guilds.append(guild)
            
    return render_template('dashboard.html', guilds=admin_guilds, user=session.get('user'))


@app.route('/manage/<guild_id>', methods=['GET', 'POST'])
def manage_server(guild_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('auth.login'))
        
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers)
    guild_name = "Discord Guild"
    
    if response.status_code == 200:
        for g in response.json():
            if g['id'] == guild_id:
                guild_name = g['name']
                break

    all_settings = load_settings()
    if guild_id not in all_settings:
        all_settings[guild_id] = {
            'prefix': '!',
            'leveling_enabled': True,
            'theme': 'crimson',
            'bg_url': '',
            'multiplier': 1.0,
            'economy_enabled': True,
            'currency_name': 'Coins',
            'starting_balance': 1000,
            'automod_enabled': True,
            'welcome_enabled': True,
            'welcome_msg': 'Welcome to the server!'
        }

    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id, guild_name)
    guild_channels = fetch_guild_channels(guild_id)
    success_msg = request.args.get('success')

    if request.method == 'POST':
        all_settings[guild_id]['prefix'] = request.form.get('prefix', '!')
        all_settings[guild_id]['leveling_enabled'] = 'leveling_enabled' in request.form
        all_settings[guild_id]['theme'] = request.form.get('theme', 'crimson')
        all_settings[guild_id]['bg_url'] = request.form.get('bg_url', '').strip()
        
        try:
            mult_val = max(0.25, min(float(request.form.get('multiplier', 1.0)), 10.0))
        except ValueError:
            mult_val = 1.0
        all_settings[guild_id]['multiplier'] = mult_val

        all_settings[guild_id]['economy_enabled'] = 'economy_enabled' in request.form
        all_settings[guild_id]['currency_name'] = request.form.get('currency_name', 'Coins')
        
        try:
            all_settings[guild_id]['starting_balance'] = int(request.form.get('starting_balance', 1000))
        except ValueError:
            all_settings[guild_id]['starting_balance'] = 1000

        all_settings[guild_id]['automod_enabled'] = 'automod_enabled' in request.form
        all_settings[guild_id]['welcome_enabled'] = 'welcome_enabled' in request.form
        all_settings[guild_id]['welcome_msg'] = request.form.get('welcome_msg', '')

        save_settings(all_settings)

        lconfig["name"] = guild_name
        lconfig["enabled"] = all_settings[guild_id]['leveling_enabled']
        lconfig["theme"] = all_settings[guild_id]['theme']
        lconfig["default_card_style"] = request.form.get('default_card_style', 'bento')
        lconfig["default_avatar_shape"] = request.form.get('default_avatar_shape', 'auto')

        bg_clean = all_settings[guild_id]['bg_url']
        lconfig["bg_url"] = bg_clean if bg_clean else None
        lconfig["levelup_bg_url"] = request.form.get('levelup_bg_url', '').strip() or None
        lconfig["multiplier"] = mult_val

        lconfig["notify_mode"] = request.form.get('notify_mode', 'current')
        raw_lvl_ch = request.form.get('level_channel', '').strip()
        lconfig["level_channel"] = int(raw_lvl_ch) if raw_lvl_ch.isdigit() else None
        lconfig["levelup_message"] = request.form.get('levelup_message', 'GG {user.mention}, you just advanced to **Level {level}**!').strip()
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
        success_msg = "All changes successfully saved and synchronized!"

    settings = all_settings[guild_id]
    users_dict = lconfig.get("users", {})
    top_users = sorted(users_dict.items(), key=lambda x: (x[1].get("prestige", 0), x[1].get("level", 0), x[1].get("xp", 0)), reverse=True)[:10]

    return render_template(
        'manage.html', 
        guild_name=guild_name, 
        settings=settings, 
        level_config=lconfig,
        guild_channels=guild_channels,
        top_users=top_users,
        guild_id=guild_id, 
        user=session.get('user'), 
        success=success_msg
    )


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
    return redirect(url_for('manage_server', guild_id=guild_id, success=msg))


@app.route('/manage/<guild_id>/levels/remove_reward/<level>', methods=['POST'])
def remove_level_reward(guild_id, level):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    lconfig.get("role_rewards", {}).pop(str(level), None)
    save_levels_data(levels_data)
    return redirect(url_for('manage_server', guild_id=guild_id, success=f"Removed Role Reward for Level {level}."))


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
    return redirect(url_for('manage_server', guild_id=guild_id, success=msg))


@app.route('/manage/<guild_id>/levels/remove_role_multiplier/<role_id>', methods=['POST'])
def remove_role_multiplier(guild_id, role_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    lconfig.get("role_multipliers", {}).pop(str(role_id), None)
    save_levels_data(levels_data)
    return redirect(url_for('manage_server', guild_id=guild_id, success=f"Removed multiplier for Role ID {role_id}."))


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
        return redirect(url_for('manage_server', guild_id=guild_id, success="Invalid User ID."))

    users = lconfig.setdefault("users", {})
    udata = users.setdefault(user_id, {"name": f"User {user_id[:6]}", "xp": 0, "level": 0, "total_xp": 0, "messages": 0, "voice_minutes": 0, "streak": 0, "prestige": 0})
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
    return redirect(url_for('manage_server', guild_id=guild_id, success=msg))


@app.route('/manage/<guild_id>/levels/reset_all', methods=['POST'])
def reset_all_server_xp(guild_id):
    if not session.get('access_token'):
        return redirect(url_for('auth.login'))
    levels_data = load_levels_data()
    lconfig = get_guild_level_config(levels_data, guild_id)
    lconfig["users"] = {}
    save_levels_data(levels_data)
    return redirect(url_for('manage_server', guild_id=guild_id, success="All server members have been reset to Level 0 (0 XP)!"))


if __name__ == '__main__':
    app.run(debug=True, port=5000)