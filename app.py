import discord
import json
import hashlib
import secrets
import os
from discord.ext import commands
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Thread

# ========== DISCORD BOT ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Your Discord bot token
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')

# Channel storage
players_channel = None
sessions_channel = None
data_channel = None

@bot.event
async def on_ready():
    print(f'✅ Discord Bot {bot.user} is online!')
    
    # Find our server and channels
    for guild in bot.guilds:
        print(f"Found server: {guild.name}")
        
        for channel in guild.channels:
            if hasattr(channel, 'name'):
                if channel.name == 'players-db':
                    global players_channel
                    players_channel = channel
                    print(f"✅ Found players-db channel")
                
                elif channel.name == 'sessions-db':
                    global sessions_channel
                    sessions_channel = channel
                    print(f"✅ Found sessions-db channel")
                
                elif channel.name == 'player-data':
                    global data_channel
                    data_channel = channel
                    print(f"✅ Found player-data channel")
    
    if not players_channel:
        print("❌ ERROR: Could not find players-db channel!")
    if not sessions_channel:
        print("❌ ERROR: Could not find sessions-db channel!")
    if not data_channel:
        print("❌ ERROR: Could not find player-data channel!")
    
    print("🚀 Discord Bot ready for database operations!")

# ========== FLASK API ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 NextLifeRP API with Discord Database - ONLINE"

@app.route('/health', methods=['GET'])
def health():
    bot_status = "online" if bot.is_ready() else "offline"
    return jsonify({
        "status": "online",
        "discord_bot": bot_status,
        "service": "nextliferp-discord-db"
    })

# Helper function to check if channels are ready
def check_channels():
    if not players_channel or not sessions_channel or not data_channel:
        return False, "Discord channels not ready yet"
    return True, "OK"

# ---------- REGISTER ----------
@app.route('/register', methods=['POST'])
def register():
    try:
        # Check channels
        ready, msg = check_channels()
        if not ready:
            return jsonify({"success": False, "error": f"Discord not ready: {msg}"})
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"})
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        print(f"📝 Registration: {username} | {email}")
        
        # Validation
        if len(username) < 3:
            return jsonify({"success": False, "error": "Username too short"})
        if len(password) < 4:
            return jsonify({"success": False, "error": "Password too short"})
        if '@' not in email:
            return jsonify({"success": False, "error": "Invalid email"})
        
        # Import async function
        import asyncio
        result = asyncio.run(register_user(username, email, password))
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Register error: {e}")
        return jsonify({"success": False, "error": str(e)})

async def register_user(username, email, password):
    # Check if user exists in Discord
    async for msg in players_channel.history(limit=200):
        if msg.content:
            try:
                user = json.loads(msg.content)
                if user.get('username') == username:
                    return {"success": False, "error": "Username taken"}
                if user.get('email') == email:
                    return {"success": False, "error": "Email exists"}
            except:
                continue
    
    # Create user
    user_id = secrets.token_hex(8)
    salt = secrets.token_hex(4)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    
    user_data = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "salt": salt,
        "created_at": datetime.now().isoformat()
    }
    
    # Save to Discord players-db channel
    await players_channel.send(json.dumps(user_data))
    print(f"✅ User saved to Discord: {username}")
    
    # Create auth token
    auth_token = secrets.token_hex(32)
    session_data = {
        "auth_token": auth_token,
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }
    await sessions_channel.send(json.dumps(session_data))
    
    # Create player game data
    game_data = {
        "user_id": user_id,
        "username": username,
        "level": 1,
        "money": 1000,
        "city": "Los Santos",
        "created_at": datetime.now().isoformat()
    }
    await data_channel.send(json.dumps(game_data))
    
    return {
        "success": True,
        "message": "Account created!",
        "auth_token": auth_token,
        "user_id": user_id,
        "username": username,
        "player_data": game_data
    }

# ---------- LOGIN ----------
@app.route('/login', methods=['POST'])
def login():
    try:
        ready, msg = check_channels()
        if not ready:
            return jsonify({"success": False, "error": f"Discord not ready: {msg}"})
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data"})
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        import asyncio
        result = asyncio.run(login_user(email, password))
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

async def login_user(email, password):
    # Find user in Discord
    async for msg in players_channel.history(limit=200):
        if msg.content:
            try:
                user = json.loads(msg.content)
                if user.get('email') == email:
                    # Check password
                    test_hash = hashlib.sha256((password + user['salt']).encode()).hexdigest()
                    if test_hash == user['password_hash']:
                        # Create new token
                        auth_token = secrets.token_hex(32)
                        session_data = {
                            "auth_token": auth_token,
                            "user_id": user['user_id'],
                            "created_at": datetime.now().isoformat()
                        }
                        await sessions_channel.send(json.dumps(session_data))
                        
                        # Get player data
                        player_data = await get_player_data_from_discord(user['user_id'])
                        
                        return {
                            "success": True,
                            "auth_token": auth_token,
                            "user_id": user['user_id'],
                            "username": user['username'],
                            "player_data": player_data
                        }
            except:
                continue
    
    return {"success": False, "error": "Invalid email or password"}

async def get_player_data_from_discord(user_id):
    # Find player data in Discord
    async for msg in data_channel.history(limit=200):
        if msg.content:
            try:
                data = json.loads(msg.content)
                if data.get('user_id') == user_id:
                    return data
            except:
                continue
    
    # Return default if not found
    return {
        "user_id": user_id,
        "level": 1,
        "money": 1000,
        "city": "Los Santos"
    }

# ---------- VALIDATE TOKEN ----------
@app.route('/validate', methods=['POST'])
def validate():
    try:
        ready, msg = check_channels()
        if not ready:
            return jsonify({"success": False, "error": f"Discord not ready: {msg}"})
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data"})
        
        token = data.get('auth_token', '')
        
        import asyncio
        result = asyncio.run(validate_token_async(token))
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

async def validate_token_async(token):
    # Check sessions in Discord
    async for msg in sessions_channel.history(limit=200):
        if msg.content:
            try:
                session = json.loads(msg.content)
                if session.get('auth_token') == token:
                    # Get user
                    async for user_msg in players_channel.history(limit=200):
                        if user_msg.content:
                            user = json.loads(user_msg.content)
                            if user.get('user_id') == session.get('user_id'):
                                return {
                                    "success": True,
                                    "valid": True,
                                    "username": user['username'],
                                    "user_id": user['user_id']
                                }
            except:
                continue
    
    return {"success": True, "valid": False}

# ---------- GET PLAYER DATA ----------
@app.route('/player_data', methods=['POST'])
def player_data():
    try:
        ready, msg = check_channels()
        if not ready:
            return jsonify({"success": False, "error": f"Discord not ready: {msg}"})
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data"})
        
        user_id = data.get('user_id', '')
        
        import asyncio
        result = asyncio.run(get_player_data_from_discord(user_id))
        return jsonify({"success": True, "player_data": result})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ========== START BOTH SERVICES ==========
def run_flask():
    print("🚀 Starting Flask API on port 10000...")
    app.run(host='0.0.0.0', port=10000, debug=False, threaded=True)

# Start Flask in thread
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Start Discord bot
print("🤖 Starting Discord Bot...")
print(f"Using token: {DISCORD_TOKEN[:10]}...")
bot.run(DISCORD_TOKEN)
