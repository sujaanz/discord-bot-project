import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, session, request
from web.auth import auth_bp

app = Flask(__name__)
app.secret_key = "sofiya_maki_exact_master_key_2026"

app.register_blueprint(auth_bp, url_prefix='/auth')

SETTINGS_FILE = 'web/server_settings.json'

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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

    success_msg = None
    if request.method == 'POST':
        all_settings[guild_id]['prefix'] = request.form.get('prefix', '!')
        all_settings[guild_id]['leveling_enabled'] = True if request.form.get('leveling_enabled') else False
        all_settings[guild_id]['theme'] = request.form.get('theme', 'crimson')
        all_settings[guild_id]['bg_url'] = request.form.get('bg_url', '').strip()
        all_settings[guild_id]['multiplier'] = float(request.form.get('multiplier', 1.0))
        all_settings[guild_id]['economy_enabled'] = True if request.form.get('economy_enabled') else False
        all_settings[guild_id]['currency_name'] = request.form.get('currency_name', 'Coins')
        all_settings[guild_id]['starting_balance'] = int(request.form.get('starting_balance', 1000))
        all_settings[guild_id]['automod_enabled'] = True if request.form.get('automod_enabled') else False
        all_settings[guild_id]['welcome_enabled'] = True if request.form.get('welcome_enabled') else False
        all_settings[guild_id]['welcome_msg'] = request.form.get('welcome_msg', '')

        save_settings(all_settings)
        success_msg = "All changes successfully saved and synchronized!"
        
    settings = all_settings[guild_id]
    
    return render_template('manage.html', guild_name=guild_name, settings=settings, guild_id=guild_id, user=session.get('user'), success=success_msg)

if __name__ == '__main__':
    app.run(debug=True, port=5000)