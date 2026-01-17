from flask import Flask, request, jsonify
import json
import hashlib
import secrets
from datetime import datetime
import os

app = Flask(__name__)

# ========== SIMPLE IN-MEMORY DATABASE ==========
users_db = []          # Store user accounts
sessions_db = []       # Store login sessions
players_db = []        # Store player game data

# ========== HELPER FUNCTIONS ==========
def find_user_by_email(email):
    for user in users_db:
        if user['email'] == email:
            return user
    return None

def find_user_by_username(username):
    for user in users_db:
        if user['username'] == username:
            return user
    return None

def find_user_by_id(user_id):
    for user in users_db:
        if user['user_id'] == user_id:
            return user
    return None

def find_session_by_token(token):
    for session in sessions_db:
        if session['auth_token'] == token:
            return session
    return None

def find_player_data(user_id):
    for player in players_db:
        if player['user_id'] == user_id:
            return player
    return None

# ========== API ENDPOINTS ==========
@app.route('/')
def home():
    return "🎮 NextLifeRP API - ONLINE | Use /register, /login, /validate"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "online",
        "service": "nextliferp",
        "users_count": len(users_db),
        "timestamp": datetime.now().isoformat()
    })

# ---------- REGISTER ----------
@app.route('/register', methods=['POST'])
def register():
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"})
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        print(f"📝 Registration attempt: {username} | {email}")
        
        # Validation
        if len(username) < 3:
            return jsonify({"success": False, "error": "Username must be at least 3 characters"})
        
        if len(password) < 4:
            return jsonify({"success": False, "error": "Password must be at least 4 characters"})
        
        if '@' not in email:
            return jsonify({"success": False, "error": "Invalid email format"})
        
        # Check if exists
        if find_user_by_username(username):
            return jsonify({"success": False, "error": "Username already taken"})
        
        if find_user_by_email(email):
            return jsonify({"success": False, "error": "Email already registered"})
        
        # Create user
        user_id = secrets.token_hex(8)
        salt = secrets.token_hex(4)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        
        new_user = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "salt": salt,
            "created_at": datetime.now().isoformat()
        }
        users_db.append(new_user)
        
        # Create auth token
        auth_token = secrets.token_hex(32)
        new_session = {
            "auth_token": auth_token,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        sessions_db.append(new_session)
        
        # Create player data
        new_player = {
            "user_id": user_id,
            "username": username,
            "level": 1,
            "money": 1000,
            "city": "Los Santos",
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat()
        }
        players_db.append(new_player)
        
        print(f"✅ User registered: {username} (ID: {user_id})")
        
        return jsonify({
            "success": True,
            "message": "Account created successfully!",
            "auth_token": auth_token,
            "user_id": user_id,
            "username": username,
            "player_data": new_player
        })
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({"success": False, "error": "Server error"})

# ---------- LOGIN ----------
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"})
        
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        print(f"🔑 Login attempt: {email}")
        
        # Find user
        user = find_user_by_email(email)
        if not user:
            return jsonify({"success": False, "error": "Invalid email or password"})
        
        # Verify password
        test_hash = hashlib.sha256((password + user['salt']).encode()).hexdigest()
        if test_hash != user['password_hash']:
            return jsonify({"success": False, "error": "Invalid email or password"})
        
        # Create new token
        auth_token = secrets.token_hex(32)
        new_session = {
            "auth_token": auth_token,
            "user_id": user['user_id'],
            "created_at": datetime.now().isoformat()
        }
        sessions_db.append(new_session)
        
        # Update player last login
        player = find_player_data(user['user_id'])
        if player:
            player['last_login'] = datetime.now().isoformat()
        
        print(f"✅ User logged in: {user['username']}")
        
        return jsonify({
            "success": True,
            "message": "Login successful!",
            "auth_token": auth_token,
            "user_id": user['user_id'],
            "username": user['username'],
            "player_data": player if player else {
                "user_id": user['user_id'],
                "username": user['username'],
                "level": 1,
                "money": 1000,
                "city": "Los Santos"
            }
        })
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({"success": False, "error": "Server error"})

# ---------- VALIDATE TOKEN ----------
@app.route('/validate', methods=['POST'])
def validate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"})
        
        auth_token = data.get('auth_token', '').strip()
        
        # Find session
        session = find_session_by_token(auth_token)
        if not session:
            return jsonify({"success": True, "valid": False, "message": "Invalid token"})
        
        # Find user
        user = find_user_by_id(session['user_id'])
        if not user:
            return jsonify({"success": True, "valid": False, "message": "User not found"})
        
        # Get player data
        player = find_player_data(user['user_id'])
        
        return jsonify({
            "success": True,
            "valid": True,
            "message": "Token is valid",
            "user_id": user['user_id'],
            "username": user['username'],
            "player_data": player if player else {}
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": "Server error"})

# ---------- GET PLAYER DATA ----------
@app.route('/player_data', methods=['POST'])
def get_player_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"})
        
        user_id = data.get('user_id', '').strip()
        auth_token = data.get('auth_token', '').strip()
        
        # Validate token if provided
        if auth_token:
            session = find_session_by_token(auth_token)
            if not session or session['user_id'] != user_id:
                return jsonify({"success": False, "error": "Unauthorized"})
        
        # Find player data
        player = find_player_data(user_id)
        if not player:
            return jsonify({"success": False, "error": "Player data not found"})
        
        return jsonify({
            "success": True,
            "player_data": player
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": "Server error"})

# ---------- UPDATE PLAYER DATA ----------
@app.route('/update_player', methods=['POST'])
def update_player():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data received"})
        
        user_id = data.get('user_id', '').strip()
        auth_token = data.get('auth_token', '').strip()
        updates = data.get('updates', {})
        
        # Validate token
        session = find_session_by_token(auth_token)
        if not session or session['user_id'] != user_id:
            return jsonify({"success": False, "error": "Unauthorized"})
        
        # Find player
        player = find_player_data(user_id)
        if not player:
            return jsonify({"success": False, "error": "Player not found"})
        
        # Update fields
        for key, value in updates.items():
            if key in ['level', 'money', 'city', 'last_login']:
                player[key] = value
        
        return jsonify({
            "success": True,
            "message": "Player data updated",
            "player_data": player
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": "Server error"})

# ---------- GET ALL DATA (DEBUG) ----------
@app.route('/debug', methods=['GET'])
def debug():
    return jsonify({
        "users": users_db,
        "sessions": sessions_db,
        "players": players_db,
        "counts": {
            "users": len(users_db),
            "sessions": len(sessions_db),
            "players": len(players_db)
        }
    })

# ========== RUN SERVER ==========
if __name__ == '__main__':
    print("🚀 Starting NextLifeRP API Server...")
    print("📡 Endpoints:")
    print("  POST /register  - Create account")
    print("  POST /login     - Login user")
    print("  POST /validate  - Validate token")
    print("  POST /player_data - Get player data")
    print("  GET  /health    - Check server health")
    print("  GET  /debug     - View all data (debug)")
    print("=" * 50)
    
    # Run server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
