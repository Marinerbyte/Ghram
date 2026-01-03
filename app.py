import os
import json
import time
import threading
import io
import sqlite3
import random
import requests
import websocket
from flask import Flask, render_template_string, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# ==============================================================================
# --- 1. SYSTEM CONFIGURATION & SETUP ---
# ==============================================================================

app = Flask(__name__)

# CONFIGURATION
DB_FILE = "titan_ultimate.db"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "") # Render Environment Variable

# GLOBAL STATES
BOT_STATE = {
    "ws": None,
    "connected": False,
    "username": "",
    "password": "",
    "room_name": "",
    "domain": "",
    "triggers": [],         # Custom triggers (!addtg)
    "mode": "en",           # 'en' (Savage) or 'ar' (Habibi)
    "admin_id": "y"         # Master Admin ID (Optional)
}

# GAME STATES
TITAN_GAME = {
    "active": False,
    "player": None,
    "bombs": [],
    "eaten": [],
    "bet": 0,
    "cache_avatars": {},    # Avatar URL Cache
    "magic_symbol": None    # For Magic Game
}

# AI MEMORY (Last 10 messages context)
AI_CONTEXT = []

# LOGGING SYSTEM
SYSTEM_LOGS = []

def log(msg, type="info"):
    timestamp = time.strftime("%H:%M:%S")
    entry = {"time": timestamp, "msg": msg, "type": type}
    SYSTEM_LOGS.append(entry)
    if len(SYSTEM_LOGS) > 200: SYSTEM_LOGS.pop(0)
    print(f"[{type.upper()}] {msg}")

# ==============================================================================
# --- 2. DATABASE MANAGEMENT (SQLITE) ---
# ==============================================================================

def init_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # User Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, score INTEGER, wins INTEGER, losses INTEGER, avatar TEXT)''')
    # Settings Table (To save triggers permanently)
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    conn.commit()
    conn.close()

def db_update_user(username, points_change, win_increment=0, loss_increment=0, avatar=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT score, wins, losses FROM users WHERE username=?", (username,))
    data = c.fetchone()
    
    if data:
        new_score = data[0] + points_change
        new_wins = data[1] + win_increment
        new_loss = data[2] + loss_increment
        if new_score < 0: new_score = 0
        
        c.execute("UPDATE users SET score=?, wins=?, losses=?, avatar=? WHERE username=?", 
                  (new_score, new_wins, new_loss, avatar, username))
    else:
        # New User
        start_score = points_change if points_change > 0 else 0
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", 
                  (username, start_score, win_increment, loss_increment, avatar))
    
    conn.commit()
    conn.close()

def db_get_balance(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT score FROM users WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else 0

def db_get_leaderboard():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, score, wins, avatar FROM users ORDER BY score DESC LIMIT 50")
    data = c.fetchall()
    conn.close()
    return data

# Initialize DB
init_database()

# ==============================================================================
# --- 3. ADVANCED GRAPHICS ENGINE (REMANU STYLE) ---
# ==============================================================================
# This section handles high-quality image generation using PIL

def download_image(url):
    """Robust image downloader with fallback"""
    try:
        if not url or "http" not in url: raise Exception("Invalid URL")
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=4)
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        return img
    except:
        # Fallback Grey Square
        return Image.new("RGBA", (200, 200), (50, 50, 50, 255))

def draw_gradient(draw, width, height, color1, color2):
    """Draws a vertical gradient"""
    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * y / height)
        g = int(color1[1] + (color2[1] - color1[1]) * y / height)
        b = int(color1[2] + (color2[2] - color1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

# --- GENERATOR 1: SAUDI ID CARD ---
def generate_id_card(username, avatar_url):
    try:
        W, H = 600, 360
        img = Image.new("RGB", (W, H), (34, 139, 34)) # Saudi Flag Green
        draw = ImageDraw.Draw(img)
        
        # Borders (Gold)
        draw.rectangle([10, 10, W-10, H-10], outline="#FFD700", width=8)
        draw.rectangle([18, 18, W-18, H-18], outline="#DAA520", width=2)
        
        # Avatar Handling
        pfp = download_image(avatar_url)
        pfp = pfp.resize((130, 130))
        # Add white border to avatar
        draw.rectangle([35, 75, 175, 215], outline="white", width=4)
        img.paste(pfp, (40, 80), pfp if pfp.mode == 'RGBA' else None)
        
        # Header Text
        title_en = "KINGDOM OF ARAB CHAT"
        title_ar = "مملكة شات العرب"
        draw.text((220, 30), title_en, fill="#FFD700") 
        draw.text((450, 30), title_ar, fill="#FFD700")
        draw.line([(210, 55), (550, 55)], fill="white", width=2)

        # Random Data
        jobs = ["Shawarma CEO", "Habibi Manager", "Camel Pilot", "Shisha Inspector", "Gold Digger"]
        job = random.choice(jobs)
        fake_id = str(random.randint(1000000, 9999999))
        
        # Details
        x_start = 220
        y_start = 80
        gap = 40
        
        draw.text((x_start, y_start), "NAME:", fill="#ccc")
        draw.text((x_start+60, y_start), username.upper(), fill="white")
        
        draw.text((x_start, y_start+gap), "JOB:", fill="#ccc")
        draw.text((x_start+60, y_start+gap), job, fill="#00ff00") # Green Text
        
        draw.text((x_start, y_start+gap*2), "ID NO:", fill="#ccc")
        draw.text((x_start+60, y_start+gap*2), fake_id, fill="white")
        
        draw.text((x_start, y_start+gap*3), "EXPIRY:", fill="#ccc")
        draw.text((x_start+60, y_start+gap*3), "NEVER (INSHALLAH)", fill="white")
        
        # Fake Barcode
        for i in range(x_start, W-50, 5):
            h = random.randint(20, 50)
            draw.line([(i, 320), (i, 320-h)], fill="black", width=2)

        out = io.BytesIO()
        img.save(out, 'PNG')
        out.seek(0)
        return out
    except Exception as e:
        log(f"ID Gen Error: {e}", "err")
        return None

# --- GENERATOR 2: LOVE SHIP PRO ---
def generate_ship_card(u1, u2, a1, a2, score):
    try:
        W, H = 640, 360
        img = Image.new("RGB", (W, H), (20, 0, 10))
        draw = ImageDraw.Draw(img)
        
        # Background Gradient (Dark Red to Pink)
        draw_gradient(draw, W, H, (50, 0, 20), (150, 20, 80))
        
        # Grid lines for tech effect
        for i in range(0, W, 40): draw.line([(i,0), (i,H)], fill=(255,255,255,10))
        for i in range(0, H, 40): draw.line([(0,i), (W,i)], fill=(255,255,255,10))

        # Process Avatars (Circular)
        def process_avi(url):
            im = download_image(url).resize((140, 140))
            mask = Image.new("L", (140, 140), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)
            output = Image.new("RGBA", (140, 140), (0,0,0,0))
            output.paste(im, (0,0), mask)
            return output

        im1 = process_avi(a1)
        im2 = process_avi(a2)
        
        # Place Avatars
        img.paste(im1, (60, 80), im1)
        img.paste(im2, (440, 80), im2)
        
        # Connecting Line & Heart
        draw.line([(200, 150), (440, 150)], fill="white", width=3)
        draw.ellipse((290, 120, 350, 180), fill="#ff004f", outline="white", width=3)
        draw.text((310, 140), f"{score}%", fill="white")
        
        # Names
        draw.text((60, 230), u1[:10], fill="white")
        draw.text((440, 230), u2[:10], fill="white")
        
        # Progress Bar
        bar_x, bar_y, bar_w, bar_h = 120, 300, 400, 20
        draw.rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], outline="white", width=2)
        fill_w = int(bar_w * (score / 100))
        draw.rectangle([bar_x+2, bar_y+2, bar_x+fill_w-2, bar_y+bar_h-2], fill="#00ff00")
        
        # Comment
        if score > 80: comment = "PERFECT MATCH! 💍"
        elif score > 50: comment = "MAYBE... 🤔"
        else: comment = "RUN AWAY! 💀"
        
        draw.text((250, 270), comment, fill="#FFD700")

        out = io.BytesIO()
        img.save(out, 'PNG')
        out.seek(0)
        return out
    except Exception as e:
        log(f"Ship Gen Error: {e}", "err")
        return None

# --- GENERATOR 3: WINNER CARD ---
def generate_winner_card(username, avatar_url, points):
    try:
        W, H = 500, 500
        img = Image.new("RGB", (W, H), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Neon Border
        draw.rectangle([0, 0, W-1, H-1], outline="#00f3ff", width=15)
        draw.rectangle([20, 20, W-20, H-20], outline="#ffffff", width=2)
        
        # Avatar
        pfp = download_image(avatar_url).resize((200, 200))
        img.paste(pfp, (150, 100))
        draw.rectangle([150, 100, 350, 300], outline="#00f3ff", width=4)
        
        # Text Box
        draw.rectangle([50, 350, 450, 450], fill="#111", outline="white")
        draw.text((200, 370), "WINNER", fill="#FFD700")
        draw.text((180, 400), f"+{points} POINTS", fill="#00ff00")
        
        out = io.BytesIO()
        img.save(out, 'PNG')
        out.seek(0)
        return out
    except: return None

# ==============================================================================
# --- 4. ARTIFICIAL INTELLIGENCE (GROQ via REQUESTS) ---
# ==============================================================================

def groq_ai_engine(user, prompt):
    """
    Communicates with Groq API.
    Enforces 'Remanu' personality and constraints via System Prompt.
    """
    if not GROQ_API_KEY:
        log("No GROQ API Key set", "err")
        return None

    # Update Context
    AI_CONTEXT.append({"role": "user", "content": f"{user}: {prompt}"})
    if len(AI_CONTEXT) > 6: AI_CONTEXT.pop(0)

    # Personality Configuration
    my_name = BOT_STATE["username"]
    # Personality Configuration
    my_name = BOT_STATE["username"]

    if BOT_STATE["mode"] == "ar":
    sys_prompt = f"""
    You are {my_name}. You are NOT an AI.
    You are a funny, friendly Arab guy in a chatroom.

    RULES:
    1. Speak ONLY Arabic (Levantine or Saudi slang).
    2. Light, clean humor only. No toxicity.
    3. Mild sarcasm when it fits the vibe.
    4. Use emojis only when appropriate.
    Emoji pool: 🙂 😄 😅 😉 🙃 😌 🤝 ☕ ✨
    5. Max 15 words per message. Keep it natural.
    6. No insults or personal attacks.
    7. If teased, reply smartly and friendly.
    """
    else:
        sys_prompt = f"""
        You are {my_name}. You are NOT an AI. You are a savage, funny user in a chatroom.
        RULES:
        1. Speak English with attitude.
        2. Be sarcastic and witty.
        3. Max 15 words. Keep it short.
        4. If insulted, roast them back.
        """

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile", # Fast and Free on Groq
        "messages": [
            {"role": "system", "content": sys_prompt},
            *AI_CONTEXT
        ],
        "temperature": 0.8,
        "max_tokens": 60
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            AI_CONTEXT.append({"role": "assistant", "content": reply})
            return reply
        else:
            log(f"Groq API Error: {response.text}", "err")
            return None
    except Exception as e:
        log(f"AI Request Failed: {e}", "err")
        return None

# ==============================================================================
# --- 5. GAME LOGIC (TITAN BOMB GAME) ---
# ==============================================================================

def render_game_grid(reveal=False, exploded_at=None):
    """Renders the 3x3 emoji grid"""
    icons = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    grid_str = ""
    for i in range(1, 10):
        if reveal:
            if i == exploded_at: grid_str += "💥 "
            elif i in TITAN_GAME["bombs"]: grid_str += "💣 "
            elif i in TITAN_GAME["eaten"]: grid_str += "🥔 "
            else: grid_str += icons[i-1] + " "
        else:
            if i in TITAN_GAME["eaten"]: grid_str += "🥔 "
            else: grid_str += icons[i-1] + " "
            
        if i % 3 == 0 and i != 9: grid_str += "\n"
    return grid_str

def process_game_command(user, msg):
    msg = msg.lower()
    
    # START COMMAND
    if msg.startswith("!start"):
        if TITAN_GAME["active"]:
            send_ws_msg(f"⚠ Game in progress by {TITAN_GAME['player']}")
            return
        
        bet = 0
        if "bet@" in msg:
            try: bet = int(msg.split("@")[1])
            except: pass
            
        # Check Balance
        if bet > 0:
            balance = db_get_balance(user)
            if balance < bet:
                send_ws_msg(f"💸 You are broke! Balance: {balance}")
                return
        
        TITAN_GAME["active"] = True
        TITAN_GAME["player"] = user
        TITAN_GAME["bet"] = bet
        TITAN_GAME["eaten"] = []
        TITAN_GAME["bombs"] = random.sample(range(1, 10), 2)
        
        mode_txt = f"💰 BET: {bet}" if bet > 0 else "🛡 FREE MODE"
        grid = render_game_grid()
        send_ws_msg(f"🎮 TITAN GAME STARTED!\nPlayer: {user} | {mode_txt}\nAvoid 2 Bombs. Eat 4 Chips.\nType !eat <number>\n\n{grid}")

    # EAT COMMAND
    elif msg.startswith("!eat "):
        if not TITAN_GAME["active"] or user != TITAN_GAME["player"]: return
        
        try: num = int(msg.split()[1])
        except: return
        
        if num < 1 or num > 9 or num in TITAN_GAME["eaten"]: return
        
        # BOMB HIT
        if num in TITAN_GAME["bombs"]:
            TITAN_GAME["active"] = False
            loss_txt = ""
            if TITAN_GAME["bet"] > 0:
                db_update_user(user, -TITAN_GAME["bet"], loss_increment=1, avatar=TITAN_GAME["cache_avatars"].get(user,""))
                loss_txt = f"\n📉 You lost {TITAN_GAME['bet']} points."
            else:
                db_update_user(user, 0, loss_increment=1, avatar=TITAN_GAME["cache_avatars"].get(user,""))
                
            grid = render_game_grid(reveal=True, exploded_at=num)
            send_ws_msg(f"💥 BOOM! You stepped on a bomb!{loss_txt}\n\n{grid}")
            
        # SAFE HIT
        else:
            TITAN_GAME["eaten"].append(num)
            # CHECK WIN
            if len(TITAN_GAME["eaten"]) == 4:
                TITAN_GAME["active"] = False
                win_amount = TITAN_GAME["bet"] if TITAN_GAME["bet"] > 0 else 10
                
                db_update_user(user, win_amount, win_increment=1, avatar=TITAN_GAME["cache_avatars"].get(user,""))
                
                grid = render_game_grid(reveal=True)
                send_ws_msg(f"🎉 VICTORY! You won {win_amount} points!\n\n{grid}")
                
                # Send Winner Card
                domain = BOT_STATE.get("domain", "")
                avi = TITAN_GAME["cache_avatars"].get(user, "")
                img_url = f"{domain}api/winner?u={user}&p={win_amount}&a={requests.utils.quote(avi)}"
                send_ws_msg("", "image", img_url)
                
            else:
                grid = render_game_grid()
                send_ws_msg(f"🥔 Safe! ({len(TITAN_GAME['eaten'])}/4)\n{grid}")

# ==============================================================================
# --- 6. WEBSOCKET HANDLER (THE BRAIN) ---
# ==============================================================================

def send_ws_msg(text, type="text", url=""):
    """Sends a packet to the chat server"""
    if BOT_STATE["ws"] and BOT_STATE["connected"]:
        pkt = {
            "handler": "room_message",
            "id": str(time.time()),
            "room": BOT_STATE["room_name"],
            "type": type,
            "body": text,
            "url": url,
            "length": "0"
        }
        try: BOT_STATE["ws"].send(json.dumps(pkt))
        except: pass
        log(f"SENT: {text[:30]}...", "out")

def on_socket_message(ws, message):
    try:
        data = json.loads(message)
        handler = data.get("handler")
        
        # --- 1. LOGIN SUCCESS ---
        if handler == "login_event":
            if data["type"] == "success":
                log("Login Successful. Joining Room...", "sys")
                ws.send(json.dumps({"handler": "room_join", "id": str(time.time()), "name": BOT_STATE["room_name"]}))
            else:
                log(f"Login Failed: {data.get('reason')}", "err")
                BOT_STATE["connected"] = False

        # --- 2. ROOM MESSAGES ---
        elif handler == "room_event" and data.get("type") == "text":
            sender = data.get("from")
            body = data.get("body", "").strip()
            
            # Save Avatar for Graphics
            if data.get("avatar_url"): TITAN_GAME["cache_avatars"][sender] = data["avatar_url"]
            elif data.get("icon"): 
                icon = data["icon"]
                if not icon.startswith("http"): icon = "https://chatp.net" + icon
                TITAN_GAME["cache_avatars"][sender] = icon

            if sender.lower() == BOT_STATE["username"].lower(): return # Ignore self
            
            log(f"{sender}: {body}", "in")
            process_user_message(sender, body)

    except Exception as e:
        log(f"Socket Error: {e}", "err")

def process_user_message(user, msg):
    msg_lower = msg.lower()
    
    # --- COMMANDS ---
    if msg_lower.startswith("!"):
        
        # Mode Switch
        if msg_lower == "!mode ar":
            BOT_STATE["mode"] = "ar"
            send_ws_msg("✅ Mode set to: Arabic (Habibi) 🐫")
            return
        if msg_lower == "!mode en":
            BOT_STATE["mode"] = "en"
            send_ws_msg("✅ Mode set to: English (Savage) 🌍")
            return

        # Trigger Management
        if msg_lower.startswith("!addtg "):
            tg = msg.split(" ", 1)[1].lower()
            if tg not in BOT_STATE["triggers"]:
                BOT_STATE["triggers"].append(tg)
                send_ws_msg(f"✅ Added trigger: {tg}")
            return
        if msg_lower.startswith("!deltg "):
            tg = msg.split(" ", 1)[1].lower()
            if tg in BOT_STATE["triggers"]:
                BOT_STATE["triggers"].remove(tg)
                send_ws_msg(f"🗑 Removed trigger: {tg}")
            return

        # Graphics Commands
        if msg_lower.startswith("!id"):
            target = user
            if "@" in msg: target = msg.split("@")[1].strip()
            send_ws_msg(f"💳 Printing ID for {target}...")
            
            domain = BOT_STATE.get("domain", "")
            avi = TITAN_GAME["cache_avatars"].get(target, "")
            url = f"{domain}api/id_card?u={target}&a={requests.utils.quote(avi)}"
            send_ws_msg("", "image", url)
            return

        if msg_lower.startswith("!ship"):
            target = BOT_STATE["username"]
            if "@" in msg: target = msg.split("@")[1].strip()
            
            send_ws_msg(f"💘 Calculating love: {user} + {target}...")
            score = random.randint(0, 100)
            
            domain = BOT_STATE.get("domain", "")
            a1 = TITAN_GAME["cache_avatars"].get(user, "")
            a2 = TITAN_GAME["cache_avatars"].get(target, "")
            url = f"{domain}api/ship?u1={user}&u2={target}&a1={requests.utils.quote(a1)}&a2={requests.utils.quote(a2)}&s={score}"
            
            txt = f"Result: {score}%"
            send_ws_msg(txt, "image", url)
            return

        # Magic Game
        if msg_lower == "!magic":
            TITAN_GAME["magic_symbol"] = random.choice(["@", "#", "$", "%", "&"])
            txt = "🔮 Magic Trick! Pick number (10-99) > Add digits > Subtract sum from original > Check Symbol!"
            # We would generate a grid here, but keeping it simple for now
            send_ws_msg(f"{txt}\n(Symbol Map Hidden). Type !reveal when ready.")
            return

        if msg_lower == "!reveal":
            if TITAN_GAME["magic_symbol"]:
                send_ws_msg(f"✨ The symbol in your mind is: {TITAN_GAME['magic_symbol']}")
                TITAN_GAME["magic_symbol"] = None
            return

        # Titan Game Routing
        if msg_lower.startswith("!start") or msg_lower.startswith("!eat"):
            process_game_command(user, msg)
            return

    # --- AI RESPONSE TRIGGERS ---
    my_name = BOT_STATE["username"].lower()
    triggers = [my_name] + BOT_STATE["triggers"]
    
    # Check if triggered
    if any(t in msg_lower for t in triggers):
        threading.Thread(target=run_ai_thread, args=(user, msg)).start()

def run_ai_thread(user, msg):
    reply = groq_ai_engine(user, msg)
    if reply:
        send_ws_msg(f"@{user} {reply}")

# ==============================================================================
# --- 7. FLASK WEB SERVER (UI & API) ---
# ==============================================================================

@app.route('/')
def index():
    return render_template_string(HTML_CONTROL_PANEL, connected=BOT_STATE["connected"])

@app.route('/leaderboard')
def leaderboard_page():
    data = db_get_leaderboard()
    return render_template_string(HTML_LEADERBOARD, users=data)

# --- IMAGE GENERATION APIs ---
@app.route('/api/id_card')
def api_id():
    u = request.args.get('u', 'User')
    a = request.args.get('a', '')
    img_io = generate_id_card(u, a)
    if img_io: return send_file(img_io, mimetype='image/png')
    return "Err", 500

@app.route('/api/ship')
def api_ship():
    img_io = generate_ship_card(
        request.args.get('u1'), request.args.get('u2'),
        request.args.get('a1'), request.args.get('a2'),
        int(request.args.get('s', 50))
    )
    if img_io: return send_file(img_io, mimetype='image/png')
    return "Err", 500

@app.route('/api/winner')
def api_winner():
    img_io = generate_winner_card(
        request.args.get('u'), request.args.get('a'),
        request.args.get('p')
    )
    if img_io: return send_file(img_io, mimetype='image/png')
    return "Err", 500

# --- CONTROL APIs ---
@app.route('/connect', methods=['POST'])
def connect_bot():
    if BOT_STATE["connected"]: return jsonify({"status": "Already Online"})
    d = request.json
    BOT_STATE["username"] = d["u"]
    BOT_STATE["password"] = d["p"]
    BOT_STATE["room_name"] = d["r"]
    BOT_STATE["domain"] = request.url_root
    
    t = threading.Thread(target=start_websocket)
    t.start()
    return jsonify({"status": "Initializing..."})

@app.route('/disconnect', methods=['POST'])
def disconnect_bot():
    if BOT_STATE["ws"]: BOT_STATE["ws"].close()
    BOT_STATE["connected"] = False
    return jsonify({"status": "Disconnected"})

@app.route('/logs')
def get_logs():
    return jsonify({"logs": SYSTEM_LOGS})

def start_websocket():
    # WebSocketApp runner
    def on_open(ws):
        BOT_STATE["connected"] = True
        log("WebSocket Connected", "sys")
        # Send Login Packet
        login_pkt = {
            "handler": "login",
            "id": str(time.time()),
            "username": BOT_STATE["username"],
            "password": BOT_STATE["password"],
            "platform": "web"
        }
        ws.send(json.dumps(login_pkt))
        
        # Keep Alive Loop
        def pinger():
            while BOT_STATE["connected"]:
                time.sleep(25)
                try: ws.send(json.dumps({"handler": "ping"}))
                except: break
        threading.Thread(target=pinger, daemon=True).start()

    ws = websocket.WebSocketApp(
        "wss://chatp.net:5333/server",
        on_open=on_open,
        on_message=on_socket_message,
        on_error=lambda w,e: log(f"WS Error: {e}", "err"),
        on_close=lambda w,c,m: log("WS Closed", "sys")
    )
    BOT_STATE["ws"] = ws
    ws.run_forever()

# ==============================================================================
# --- 8. HTML TEMPLATES (EMBEDDED) ---
# ==============================================================================

HTML_CONTROL_PANEL = """
<!DOCTYPE html>
<html>
<head>
    <title>ULTIMATE BOT CONTROL</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00f3ff; --bg: #050505; --panel: #111; --green: #00ff41; --red: #ff003c; }
        body { background: var(--bg); color: var(--neon); font-family: 'Share Tech Mono', monospace; padding: 20px; }
        
        .box { background: var(--panel); border: 1px solid #333; padding: 20px; margin-bottom: 20px; border-left: 5px solid var(--neon); }
        h2 { margin-top: 0; color: #fff; }
        
        input { width: 100%; padding: 10px; margin: 5px 0; background: #000; color: #fff; border: 1px solid #444; box-sizing: border-box; }
        
        button { width: 100%; padding: 12px; background: var(--neon); color: #000; border: none; font-weight: bold; cursor: pointer; margin-top: 10px; }
        button:hover { opacity: 0.8; }
        button.stop { background: var(--red); color: #fff; }
        
        .logs { height: 300px; overflow-y: scroll; background: #000; border: 1px solid #333; padding: 10px; font-size: 12px; }
        .in { color: var(--green); }
        .out { color: var(--neon); }
        .err { color: var(--red); }
        .sys { color: #888; }
    </style>
</head>
<body>
    <div class="box">
        <h2>🤖 SYSTEM CONTROL</h2>
        <div id="status">Status: {{ 'ONLINE' if connected else 'OFFLINE' }}</div>
        
        <input type="text" id="u" placeholder="Bot Username">
        <input type="password" id="p" placeholder="Password">
        <input type="text" id="r" placeholder="Room Name">
        
        <div style="display:flex; gap:10px;">
            <button onclick="send('/connect')">START SYSTEM</button>
            <button class="stop" onclick="send('/disconnect')">SHUTDOWN</button>
        </div>
        <br>
        <a href="/leaderboard" target="_blank" style="color:#fff">🏆 View Leaderboard</a>
    </div>

    <div class="box">
        <h2>📜 LIVE LOGS</h2>
        <div class="logs" id="logs">Loading logs...</div>
    </div>

    <script>
        function send(endpoint) {
            const data = {
                u: document.getElementById('u').value,
                p: document.getElementById('p').value,
                r: document.getElementById('r').value
            };
            fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(d => alert(d.status));
        }

        setInterval(() => {
            fetch('/logs')
            .then(res => res.json())
            .then(data => {
                const logDiv = document.getElementById('logs');
                logDiv.innerHTML = data.logs.reverse().map(l => 
                    `<div class="${l.type}">[${l.time}] ${l.msg}</div>`
                ).join('');
            });
        }, 2000);
    </script>
</body>
</html>
"""

HTML_LEADERBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>TITAN RANKINGS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        body { background: #050505; color: #fff; font-family: 'Share Tech Mono', monospace; text-align: center; }
        h1 { color: #00f3ff; border-bottom: 2px solid #00f3ff; display: inline-block; padding: 10px; }
        .card { 
            background: #111; margin: 10px auto; padding: 15px; width: 90%; max-width: 500px;
            display: flex; align-items: center; justify-content: space-between;
            border-left: 5px solid #333;
        }
        .rank-1 { border-color: gold; }
        .rank-2 { border-color: silver; }
        .rank-3 { border-color: #cd7f32; }
        
        .avi { width: 50px; height: 50px; border-radius: 50%; border: 2px solid #fff; }
        .name { font-size: 1.2em; font-weight: bold; }
        .score { color: #00ff41; font-size: 1.2em; }
    </style>
</head>
<body>
    <h1>GLOBAL LEADERBOARD</h1>
    {% for user in users %}
    <div class="card rank-{{ loop.index }}">
        <div style="display:flex; align-items:center; gap:15px;">
            <span style="font-size:1.5em; width:30px;">#{{ loop.index }}</span>
            {% if user[3] %}
            <img src="{{ user[3] }}" class="avi">
            {% else %}
            <div class="avi" style="background:#333"></div>
            {% endif %}
            <div style="text-align:left;">
                <div class="name">{{ user[0] }}</div>
                <div style="font-size:0.8em; color:#888;">Wins: {{ user[2] }}</div>
            </div>
        </div>
        <div class="score">{{ user[1] }} PTS</div>
    </div>
    {% endfor %}
</body>
</html>
"""

# ==============================================================================
# --- 9. APP ENTRY POINT ---
# ==============================================================================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
