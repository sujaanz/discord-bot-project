import os
from flask import Blueprint, redirect, request, session, url_for
import requests

auth_bp = Blueprint('auth', __name__)

CLIENT_ID = '1267928727833149592'
CLIENT_SECRET = 'rm0z4EnaoFoiRKE-anIq7elKfXcXZM3Z'
REDIRECT_URI = 'http://localhost:5000/auth/callback'
API_ENDPOINT = 'https://discord.com/api/v10'

@auth_bp.route('/login')
def login():
    discord_login_url = (
        f"{API_ENDPOINT}/oauth2/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    )
    return redirect(discord_login_url)

@auth_bp.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "No code provided!", 400
        
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(f"{API_ENDPOINT}/oauth2/token", data=data, headers=headers)
    token_json = response.json()
    
    if 'access_token' in token_json:
        session['access_token'] = token_json['access_token']
        user_headers = {'Authorization': f"Bearer {session['access_token']}"}
        user_resp = requests.get(f"{API_ENDPOINT}/users/@me", headers=user_headers)
        if user_resp.status_code == 200:
            session['user'] = user_resp.json()
            
        return redirect(url_for('dashboard'))
    
    return f"Failed to authenticate with Discord. Details: {token_json}", 400

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))