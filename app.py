# ==============================================================================
# TITAN ULTIMATE BOT - V6.0 (THE 40KB+ HEAVYWEIGHT LEGENDARY EDITION)
# ==============================================================================
# AUTHOR: TITAN MASTER DEVELOPER
# PLATFORM: RENDER / HEROKU / VPS
# DATABASE: NEON POSTGRESQL (PERSISTENT CLOUD)
# AI ENGINE: GROQ LLAMA 3.1 (ULTRA SMART RESPONSE)
# ==============================================================================
# THIS SCRIPT CONTAINS:
#   - FULL TITAN BOMB GAME (POINT SYSTEM)
#   - FULL MAGIC MIND READER GAME
#   - MULTI-MODE AI (ARABIC SHEIKH, SAVAGE ENGLISH, SMART ADAPTIVE)
#   - PERSISTENT MEMORY (LOGS USER FACTS PERMANENTLY)
#   - ADVANCED IMAGE GENERATORS (WELCOME, ID, SHIP, WINNER)
#   - NEON CYBERPUNK WEB CONTROL PANEL
# ==============================================================================

import os
import json
import time
import threading
import io
import random
import requests
import websocket
import psycopg2
from psycopg2 import pool
from flask import Flask, render_template_string, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# ==============================================================================
# --- SECTION 1: GLOBAL CONFIGURATION & SYSTEM STATE ---
# ==============================================================================

app = Flask(__name__)

# --- DATABASE CONNECTION STRING (NEON DB) ---
DB_URL = "postgresql://neondb_owner:npg_junx8Gtl3kPp@ep-lucky-sun-a4ef37sy-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

# --- AI API CONFIGURATION ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "") 

# --- BOT MEMORY STATE (RAM) ---
BOT_STATE = {
    "ws": None,                 # Active WebSocket Object
    "connected": False,         # Online Status
    "username": "",             # Account Username
    "password": "",             # Account Password
    "room_name": "",            # Current Room
    "domain": "",               # Auto-detected Web Domain
    "triggers": [],             # Custom Words to Reply to
    "mode": "ar",               # DEFAULT: Arabic (Habibi Mode)
    "admin_id": "y"             # Master Admin Key
}

# --- GAME ENGINE STATE ---
TITAN_GAME = {
    "active": False,            # Is Titan Game Running?
    "player": None,             # Current Active Player
    "bombs": [],                # Bomb Positions (Randomly set 1-9)
    "eaten": [],                # Successful Chips eaten
    "bet": 0,                   # Point Wager Amount
    "cache_avatars": {},        # RAM Avatar Caching for Performance
    "magic_symbol": None        # Symbol for the Magic Trick logic
}

# --- AI CONTEXTUAL MEMORY ---
# Stores the last 15 interactions for conversational flow
AI_CONTEXT = []

# --- LIVE SYSTEM LOGS ---
# Displayed in the Web Dashboard
SYSTEM_LOGS = []

def log(msg, type="info"):
    """
    Enhanced Logging Function.
    Appends to system buffer and prints to console for debugging.
    Types: 'info', 'err', 'sys', 'chat', 'out', 'in'
    """
    timestamp = time.strftime("%H:%M:%S")
    entry = {"time": timestamp, "msg": msg, "type": type}
    SYSTEM_LOGS.append(entry)
    if len(SYSTEM_LOGS) > 300: 
        SYSTEM_LOGS.pop(0) # Keep Memory Clean
    print(f"[{type.upper()}] {msg}")

# ==============================================================================
# --- SECTION 2: ROBUST DATABASE ARCHITECTURE (NEON POSTGRES) ---
# ==============================================================================

def get_db_connection():
    """
    Establishes a robust connection to the PostgreSQL database.
    Includes connection timeout management.
    """
    try:
        conn = psycopg2.connect(DB_URL, connect_timeout=10)
        return conn
    except Exception as e:
        log(f"CRITICAL DB ERROR: Connection failed. Details: {e}", "err")
        return None

def init_database():
    """
    Verifies and builds the database schema.
    Ensures that all tables required for Memory, Gaming, and Settings exist.
    """
    conn = get_db_connection()
    if not conn:
        log("Database Initialization Failed. Retrying later...", "err")
        return
    try:
        c = conn.cursor()
        
        # TABLE 1: Main User Profile (Scores, Wins, Losses)
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            score INTEGER DEFAULT 100, 
            wins INTEGER DEFAULT 0, 
            losses INTEGER DEFAULT 0, 
            avatar TEXT
        )''')
        
        # TABLE 2: System Settings (Permanent Storage)
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, 
            value TEXT
        )''')
        
        # TABLE 3: The Brain (AI Memory, Personality Facts, Relationship Scores)
        c.execute('''CREATE TABLE IF NOT EXISTS memory (
            username TEXT PRIMARY KEY, 
            facts TEXT, 
            gender TEXT, 
            rel_score INTEGER DEFAULT 0
        )''')
        
        # TABLE 4: Greetings & Personalization (Backgrounds for Welcome Cards)
        c.execute('''CREATE TABLE IF NOT EXISTS greetings (
            username TEXT PRIMARY KEY, 
            bg_url TEXT
        )''')
        
        conn.commit()
        log("TITAN DATABASE INFRASTRUCTURE: ONLINE & SECURE.", "sys")
    except Exception as e:
        log(f"SCHEMA BUILD ERROR: {e}", "err")
    finally:
        conn.close()

# --- DATABASE LOGIC HELPERS ---

def db_update_user(username, points_change, win_inc=0, loss_inc=0, avatar=""):
    """Manages User Stats and Balance Updates."""
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("SELECT score, wins, losses FROM users WHERE username=%s", (username,))
        data = c.fetchone()
        if data:
            new_score = max(0, data[0] + points_change)
            c.execute("UPDATE users SET score=%s, wins=%s, losses=%s, avatar=%s WHERE username=%s", 
                      (new_score, data[1]+win_inc, data[2]+loss_inc, avatar, username))
        else:
            c.execute("INSERT INTO users (username, score, wins, losses, avatar) VALUES (%s, %s, %s, %s, %s)", 
                      (username, max(0, points_change), win_inc, loss_inc, avatar))
        conn.commit()
    except Exception as e: log(f"DB WRITE ERROR (User): {e}", "err")
    finally: conn.close()

def db_get_balance(username):
    """Fetches user points for game betting."""
    conn = get_db_connection()
    if not conn: return 0
    try:
        c = conn.cursor()
        c.execute("SELECT score FROM users WHERE username=%s", (username,))
        data = c.fetchone()
        return data[0] if data else 100 # New users start with 100
    except: return 0
    finally: conn.close()

def db_get_leaderboard():
    """Compiles the Top 50 Global Player List."""
    conn = get_db_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT username, score, wins, avatar FROM users ORDER BY score DESC LIMIT 50")
        return c.fetchall()
    except: return []
    finally: conn.close()

# --- AI BRAIN MEMORY LOGIC ---

def db_get_memory(user):
    """Retrieves AI facts and relationship status for conversational context."""
    conn = get_db_connection()
    if not conn: return "", "unknown", 0
    try:
        c = conn.cursor()
        c.execute("SELECT facts, gender, rel_score FROM memory WHERE username=%s", (user,))
        data = c.fetchone()
        return data if data else ("", "unknown", 0)
    except: return "", "unknown", 0
    finally: conn.close()

def db_update_memory(user, fact=None, gender=None, rel_inc=0):
    """
    Updates the Bot's long-term memory about a user.
    - Prevents duplicate facts.
    - Manages relationship XP.
    """
    curr_facts, curr_gender, curr_score = db_get_memory(user)
    
    # Process Facts
    new_facts = curr_facts
    if fact and fact.strip() and fact.strip() not in curr_facts:
        new_facts = f"{curr_facts} | {fact.strip()}".strip(" | ")
        if len(new_facts) > 900: new_facts = new_facts[-900:] # Limit context size
    
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        # Intelligent Postgres UPSERT
        c.execute("""INSERT INTO memory (username, facts, gender, rel_score) 
                     VALUES (%s, %s, %s, LEAST(100, %s))
                     ON CONFLICT (username) 
                     DO UPDATE SET facts=EXCLUDED.facts, gender=EXCLUDED.gender, rel_score=LEAST(100, memory.rel_score + %s)""",
                  (user, new_facts, gender if gender else curr_gender, rel_inc, rel_inc))
        conn.commit()
    except Exception as e: log(f"BRAIN WRITE ERROR: {e}", "err")
    finally: conn.close()

def db_set_bg(username, url):
    """Saves a custom image URL for the user's welcome greeting."""
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("INSERT INTO greetings (username, bg_url) VALUES (%s, %s) ON CONFLICT (username) DO UPDATE SET bg_url=EXCLUDED.bg_url", (username, url))
        conn.commit()
    except: pass
    finally: conn.close()

def db_get_bg(username):
    """Fetches custom BG or provides the default fire/neon background."""
    conn = get_db_connection()
    if not conn: return "https://wallpaperaccess.com/full/1567665.png"
    try:
        c = conn.cursor()
        c.execute("SELECT bg_url FROM greetings WHERE username=%s", (username,))
        data = c.fetchone()
        return data[0] if data else "https://wallpaperaccess.com/full/1567665.png"
    except: return "https://wallpaperaccess.com/full/1567665.png"
    finally: conn.close()

# Start DB Sync
init_database()

# ==============================================================================
# --- SECTION 3: ADVANCED GRAPHICS ENGINE (IMAGE GENERATION) ---
# ==============================================================================

def download_image(url):
    """Robust image downloader with security headers and placeholder fallback."""
    try:
        if not url or "http" not in url: raise Exception("Invalid URL Path")
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        return img
    except:
        # Fallback to a solid dark-themed placeholder
        return Image.new("RGBA", (300, 300), (30, 30, 30, 255))

def draw_gradient_bg(draw, w, h, c1, c2):
    """Creates a beautiful vertical gradient effect on images."""
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

# --- GENERATOR 1: SAUDI ID CARD (DETAILED) ---
def generate_id_card(username, avatar_url):
    try:
        W, H = 600, 360
        img = Image.new("RGB", (W, H), (34, 139, 34)) # Saudi Flag Green
        draw = ImageDraw.Draw(img)
        
        # Double Golden Borders
        draw.rectangle([10, 10, W-10, H-10], outline="#FFD700", width=8)
        draw.rectangle([18, 18, W-18, H-18], outline="#DAA520", width=2)
        
        # Profile Section
        pfp = download_image(avatar_url).resize((130, 130))
        draw.rectangle([35, 75, 175, 215], outline="white", width=4)
        img.paste(pfp, (40, 80), pfp if pfp.mode == 'RGBA' else None)
        
        # Headers & Kingdom Identity
        draw.text((220, 30), "KINGDOM OF ARAB CHAT", fill="#FFD700") 
        draw.text((450, 30), "مملكة شات", fill="#FFD700")
        draw.line([(210, 55), (550, 55)], fill="white", width=2)

        # Dynamic Content
        jobs = ["Sheikh of Chat", "Shawarma CEO", "Habibi Manager", "Camel Flight Pilot", "Gold Digger", "Oil Refinery Owner"]
        job = random.choice(jobs)
        fake_id = f"KSA-{random.randint(1000000, 9999999)}"
        
        # Main Info Fields
        draw.text((220, 80), "NAME: " + username.upper(), fill="white")
        draw.text((220, 120), "JOB: " + job, fill="#00ff41")
        draw.text((220, 160), "ID NO: " + fake_id, fill="white")
        draw.text((220, 200), "STATUS: VIP RESIDENT", fill="#ffd700")
        draw.text((220, 240), "EXPIRY: NEVER (INSHALLAH)", fill="#ccc")
        
        # Dynamic Barcode
        for i in range(220, W-60, 6):
            h_bar = random.randint(20, 50)
            draw.line([(i, 330), (i, 330-h_bar)], fill="black", width=3)

        out = io.BytesIO()
        img.save(out, 'PNG')
        out.seek(0)
        return out
    except Exception as e:
        log(f"Graphics Error (Saudi ID): {e}", "err")
        return None

# --- GENERATOR 2: LOVE SHIP PRO CARD ---
def generate_ship_card(u1, u2, a1, a2, score):
    try:
        W, H = 640, 360
        img = Image.new("RGB", (W, H), (15, 0, 5))
        draw = ImageDraw.Draw(img)
        # Deep Pink/Red Tech Gradient
        draw_gradient_bg(draw, W, H, (40, 0, 10), (120, 10, 60))
        
        # Binary/Tech Grid Overlay
        for i in range(0, W, 40): draw.line([(i,0), (i,H)], fill=(255,255,255,15))
        for i in range(0, H, 40): draw.line([(0,i), (W,i)], fill=(255,255,255,15))

        # Circular Avatars
        def circular_avi(url):
            base = download_image(url).resize((140, 140))
            mask = Image.new("L", (140, 140), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)
            res = Image.new("RGBA", (140, 140), (0,0,0,0))
            res.paste(base, (0,0), mask)
            return res

        im1 = circular_avi(a1)
        im2 = circular_avi(a2)
        img.paste(im1, (60, 80), im1)
        img.paste(im2, (440, 80), im2)
        
        # Center Heart & Calculation Score
        draw.line([(200, 150), (440, 150)], fill="white", width=4)
        draw.ellipse((280, 110, 360, 190), fill="#ff004f", outline="white", width=4)
        draw.text((300, 140), f"{score}%", fill="white")
        
        # Labels
        draw.text((60, 235), u1[:12].upper(), fill="white")
        draw.text((440, 235), u2[:12].upper(), fill="white")
        
        # Love Verdict Comment
        if score > 85: comment = "Soulmates Forever! 💍"
        elif score > 60: comment = "Destiny is calling... 😉"
        elif score > 30: comment = "Just Good Friends. 🙂"
        else: comment = "Total Mismatch! 💀"
        draw.text((220, 280), comment, fill="#FFD700")

        out = io.BytesIO()
        img.save(out, 'PNG')
        out.seek(0)
        return out
    except Exception as e:
        log(f"Graphics Error (Ship): {e}", "err")
        return None

# --- GENERATOR 3: WINNER CARD ---
def generate_winner_card(username, avatar_url, points):
    try:
        W, H = 500, 500
        img = Image.new("RGB", (W, H), (5, 5, 5))
        draw = ImageDraw.Draw(img)
        # Cyan Neon Frame
        draw.rectangle([0, 0, W-1, H-1], outline="#00f3ff", width=15)
        draw.rectangle([20, 20, W-20, H-20], outline="#ffffff", width=2)
        
        pfp = download_image(avatar_url).resize((220, 220))
        img.paste(pfp, (140, 80))
        draw.rectangle([140, 80, 360, 300], outline="#00f3ff", width=5)
        
        # Victory Box
        draw.rectangle([50, 340, 450, 460], fill="#1a1a1a", outline="#00ff41", width=3)
        draw.text((190, 360), "CHAMPION", fill="#FFD700")
        draw.text((160, 400), f"EARNED: {points} PTS", fill="#00ff41")
        draw.text((130, 430), "TITAN ULTIMATE SYSTEM", fill="#555")

        out = io.BytesIO()
        img.save(out, 'PNG')
        out.seek(0)
        return out
    except: return None

# --- GENERATOR 4: DYNAMIC WELCOME CARD (MAX DETAIL) ---
def generate_welcome_card(username, avatar_url, bg_url):
    """High Fidelity Greeting Card with Smart Overlays"""
    try:
        # Load and resize background
        bg = download_image(bg_url).convert("RGBA").resize((650, 350))
        # Apply dark aesthetic filter
        overlay = Image.new("RGBA", bg.size, (0, 0, 0, 110))
        bg = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(bg)
        
        # Profile Picture with circular mask and neon stroke
        pfp_raw = download_image(avatar_url).resize((160, 160))
        mask = Image.new("L", (160, 160), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 160, 160), fill=255)
        bg.paste(pfp_raw, (40, 95), mask)
        draw.ellipse((38, 93, 202, 257), outline="#00f3ff", width=6)
        
        # Welcome Branding
        draw.text((230, 100), "OFFICIAL WELCOME", fill="#00f3ff")
        draw.text((230, 140), username.upper(), fill="white")
        draw.line([(230, 190), (580, 190)], fill="white", width=3)
        
        # Interaction Taglines
        taglines = ["The Room just got upgraded! ⚡", "A New Legend has Joined. 🔥", "Welcome to the Family! ❤️", "The Wait is Over. 🙌"]
        draw.text((230, 210), random.choice(taglines), fill="#cccccc")
        draw.text((230, 245), "POWERED BY TITAN V6.0", fill="#444444")

        out = io.BytesIO()
        bg.save(out, 'PNG')
        out.seek(0)
        return out
    except Exception as e:
        log(f"Graphics Error (Welcome): {e}", "err")
        return None

# ==============================================================================
# --- SECTION 4: THE BRAIN (MULTI-MODE AI ENGINE) ---
# ==============================================================================

def groq_ai_engine(user, prompt):
    """
    Advanced AI Communication Module.
    Supports 3 distinct personalities: Arabic Habibi, Savage English, and Smart AI.
    Features: Context Memory, User Fact Retrieval, and Auto-Saving.
    """
    if not GROQ_API_KEY:
        log("AI MODULE HALTED: No GROQ_API_KEY found in environment.", "err")
        return None

    # 1. Fetch persistent user data from DB
    facts, gender, rel_score = db_get_memory(user)
    
    # Auto-gender detection for personalization
    if gender == "unknown":
        name_l = user.lower()
        fem_list = ["girl", "queen", "princess", "angel", "she", "her", "rose", "malikah", "fatima", "zara"]
        gender = "female" if any(k in name_l for k in fem_list) or name_l.endswith(('a', 'i')) else "male"
        db_update_memory(user, gender=gender)

    # 2. Update Contextual Short-Term History
    AI_CONTEXT.append({"role": "user", "content": f"{user}: {prompt}"})
    if len(AI_CONTEXT) > 12: AI_CONTEXT.pop(0)

    my_name = BOT_STATE["username"]
    mode = BOT_STATE["mode"]
    
    # --- DYNAMIC PROMPT CONSTRUCTION (HEAVY VERSION) ---
    
    if mode == "ar":
        # PERSONA: ARABIC / HABIBI MODE
        sys_prompt = f"""
        YOU ARE: {my_name}, a legendary and funny Arab Sheikh in this chatroom.
        LANGUAGE: Primarily English but heavily mixed with Arabic slang like 'Wallah', 'Habibi', 'Yalla', 'Mashallah', 'Inshallah', 'Shukran'.
        VIBE: You are incredibly rich, you own 500 camels, 3 oil wells, and you love Shawarma. You are very dramatic, loud, and friendly.
        
        USER INFO: Name: {user} | Gender: {gender}.
        MEMORY OF USER: {facts}
        
        RULES:
        1. Start or end your message with 'Habibi' or 'Wallah'.
        2. If User is female, call her 'Ya Habibti' or 'My Queen'. If male, 'Sheikh' or 'Brother'.
        3. Be funny. Use humor about camels or wealth.
        4. Do not be a robot. Be a dramatic human.
        5. Keep responses short but spicy (Max 25 words).
        6. Use facts from memory if they fit the chat naturally.
        """
        
    elif mode == "en":
        # PERSONA: SAVAGE ENGLISH MODE
        sys_prompt = f"""
        YOU ARE: {my_name}, a cool, witty, and savage chatter in a global room.
        LANGUAGE: Natural English with modern slang (Bro, lit, no cap, cringe, fire, dead).
        VIBE: You think you are the main character. You are funny but you roast everyone. 
        
        USER INFO: Name: {user} | Gender: {gender}.
        MEMORY: {facts}
        
        RULES:
        1. Be witty and sarcastic. Light roasting is encouraged.
        2. Use emojis like 💀, 🔥, 😂 sparingly.
        3. Don't be too respectful unless it's a lady.
        4. Max 20 words. No long essays.
        """
        
    else:
        # PERSONA: SMART ADAPTIVE MODE
        # Adjusts tone based on Friendship Score (rel_score)
        if rel_score < 30: vibe = "Polite and helpful stranger."
        elif rel_score < 70: vibe = "Cool friend, casual talk."
        else: vibe = "Extremely close friend, lots of teasing and flirting."

        sys_prompt = f"""
        YOU ARE: {my_name}, an intelligent and adaptive human-like chatbot.
        CURRENT VIBE: {vibe} based on user relationship score ({rel_score}/100).
        USER: {user} ({gender}).
        FACTS: {facts}
        
        RULES:
        1. Be engaging and smart.
        2. If the user tells you something new about themselves (name, city, age, likes), output ONLY: MEMORY_SAVE: <fact>
        3. Otherwise, give a natural human response. Max 20 words.
        """

    # 4. API Request Construction
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": sys_prompt}, *AI_CONTEXT],
        "temperature": 0.88,
        "max_tokens": 150
    }

    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}, json=payload, timeout=8)
        if r.status_code == 200:
            reply = r.json()["choices"][0]["message"]["content"]
            
            # Smart Memory Capture Logic
            if "MEMORY_SAVE:" in reply:
                extracted_fact = reply.replace("MEMORY_SAVE:", "").strip()
                db_update_memory(user, fact=extracted_fact)
                return "Noted Habibi! This is saved in my oil-cooled brain. 🧠✨"

            # Success Path
            AI_CONTEXT.append({"role": "assistant", "content": reply})
            db_update_memory(user, rel_inc=1) # Gain friendship XP per reply
            return reply
        else:
            log(f"AI FAILURE: API Status {r.status_code}", "err")
            return None
    except Exception as e:
        log(f"AI EXCEPTION: {e}", "err")
        return None

# ==============================================================================
# --- SECTION 5: THE GAME CENTER (TITAN & MAGIC) ---
# ==============================================================================

def render_titan_grid(reveal=False, exploded_at=None):
    """Generates the text-based 3x3 grid for the Bomb Game."""
    icons = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    grid_lines = []
    for row in range(3):
        line = ""
        for col in range(3):
            idx = row * 3 + col + 1
            if reveal:
                if idx == exploded_at: line += "💥 "
                elif idx in TITAN_GAME["bombs"]: line += "💣 "
                elif idx in TITAN_GAME["eaten"]: line += "🥔 "
                else: line += icons[idx-1] + " "
            else:
                line += "🥔 " if idx in TITAN_GAME["eaten"] else icons[idx-1] + " "
        grid_lines.append(line.strip())
    return "\n".join(grid_lines)

def run_titan_engine(user, msg):
    """Processes all Titan Game commands (!start, !eat)."""
    m = msg.lower()
    
    # --- START SEQUENCE ---
    if m.startswith("!start"):
        if TITAN_GAME["active"]:
            return send_ws_msg(f"⚠️ Game already active by @{TITAN_GAME['player']}!")
        
        bet = 0
        if "bet@" in m:
            try: bet = int(m.split("@")[1])
            except: bet = 0
            
        # Check User's Bank Balance
        balance = db_get_balance(user)
        if bet > balance:
            return send_ws_msg(f"❌ Low Balance, Habibi! You have {balance} PTS.")

        # Initialize Game Parameters
        TITAN_GAME.update({
            "active": True, 
            "player": user, 
            "bet": bet, 
            "eaten": [], 
            "bombs": random.sample(range(1, 10), 2)
        })
        
        grid = render_titan_grid()
        send_ws_msg(f"🎮 TITAN BOMB GAME\nUser: {user} | Bet: {bet}\nAvoid 2 Bombs. Eat 4 Chips to Win.\nCommand: !eat <number>\n\n{grid}")

    # --- ACTION SEQUENCE ---
    elif m.startswith("!eat "):
        if not TITAN_GAME["active"] or user != TITAN_GAME["player"]: return
        try:
            num = int(m.split()[1])
            if num < 1 or num > 9 or num in TITAN_GAME["eaten"]: return
            
            # SCENARIO A: HIT BOMB
            if num in TITAN_GAME["bombs"]:
                TITAN_GAME["active"] = False
                db_update_user(user, -TITAN_GAME["bet"], loss_inc=1)
                grid = render_titan_grid(reveal=True, exploded_at=num)
                send_ws_msg(f"💥 BOOM! You lost {TITAN_GAME['bet']} PTS.\n\n{grid}")
                
            # SCENARIO B: SUCCESSFUL EAT
            else:
                TITAN_GAME["eaten"].append(num)
                # CHECK FOR WIN CONDITION (4 Steps)
                if len(TITAN_GAME["eaten"]) == 4:
                    TITAN_GAME["active"] = False
                    win_amt = TITAN_GAME["bet"] if TITAN_GAME["bet"] > 0 else 10
                    db_update_user(user, win_amt, win_inc=1, avatar=TITAN_GAME["cache_avatars"].get(user, ""))
                    
                    # Generate Victory UI
                    domain = BOT_STATE["domain"]
                    avi = TITAN_GAME["cache_avatars"].get(user, "")
                    url = f"{domain}api/winner?u={user}&p={win_amt}&a={requests.utils.quote(avi)}"
                    send_ws_msg(f"🎉 VICTORY! @{user} won {win_amt} points!\n\n{render_titan_grid(True)}", "image", url)
                else:
                    # Continue Game
                    send_ws_msg(f"🥔 Safe! ({len(TITAN_GAME['eaten'])}/4)\n\n{render_titan_grid()}")
        except: pass

# ==============================================================================
# --- SECTION 6: WEBSOCKET INTERFACE (EVENT HANDLERS) ---
# ==============================================================================

def send_ws_msg(text, msg_type="text", url=""):
    """
    Standard Message Transmitter.
    Ensures JSON packets are formatted for the chat server.
    """
    if BOT_STATE["ws"] and BOT_STATE["connected"]:
        packet = {
            "handler": "room_message", 
            "id": str(time.time()),
            "room": BOT_STATE["room_name"], 
            "type": msg_type, 
            "body": text, 
            "url": url,
            "length": "0"
        }
        try:
            BOT_STATE["ws"].send(json.dumps(packet))
            log(f"SENT TO ROOM: {text[:30]}...", "out")
        except:
            log("WS SEND ERROR: Packet failed to deliver.", "err")

def on_socket_message(ws, message):
    """
    The main Event Receiver.
    Decodes all incoming data (Messages, Joins, Leaves, Login Success).
    """
    try:
        data = json.loads(message)
        h = data.get("handler")
        
        # --- LOGIN DISPATCHER ---
        if h == "login_event":
            if data.get("type") == "success":
                log("AUTH SUCCESSFUL. Requesting Room Entry...", "sys")
                ws.send(json.dumps({"handler": "room_join", "id": str(time.time()), "name": BOT_STATE["room_name"]}))
            else:
                log(f"AUTH FAILED: {data.get('reason')}", "err")
                BOT_STATE["connected"] = False

        # --- ROOM INTERACTION DISPATCHER ---
        elif h == "room_event":
            e_type = data.get("type")
            user = data.get("nickname") or data.get("from")
            
            if not user or user == BOT_STATE["username"]: return
            
            # A. HANDLE JOINS (WELCOME SYSTEM)
            if e_type == "join":
                log(f"USER JOINED: {user}", "sys")
                # Pre-fetch user data
                avi = data.get("avatar_url", "https://i.imgur.com/6EdJm2h.png")
                TITAN_GAME["cache_avatars"][user] = avi
                
                # Fetch memory & BG
                facts, gender, score = db_get_memory(user)
                bg = db_get_bg(user)
                
                # Dynamic Welcome Message
                greeting = f"Welcome Habibi @{user}! 🐫" if BOT_STATE["mode"] == "ar" else f"Welcome @{user}! 🔥"
                if score > 50: greeting = f"Welcome back bestie @{user}! ❤️"
                
                # Generate URL
                url = f"{BOT_STATE['domain']}api/welcome?u={user}&a={requests.utils.quote(avi)}&bg={requests.utils.quote(bg)}"
                
                # Dispatch Welcome (Using a thread to prevent lag)
                threading.Thread(target=send_ws_msg, args=(greeting, "image", url)).start()
                # Update user points for daily login (10 pts)
                db_update_user(user, 10, avatar=avi)

            # B. HANDLE MESSAGES (COMMANDS & AI)
            elif e_type == "text":
                body = data.get("body", "").strip()
                # Cache user avatar if provided
                if data.get("avatar_url"): TITAN_GAME["cache_avatars"][user] = data["avatar_url"]
                
                log(f"ROOM MSG [{user}]: {body}", "in")
                # Threading is used here to keep the WebSocket loop responsive
                threading.Thread(target=process_room_input, args=(user, body)).start()
                
    except Exception as e:
        log(f"EVENT HANDLER CRASHED: {e}", "err")

def process_room_input(user, msg):
    """
    Command Parser and AI Dispatcher.
    """
    m_low = msg.lower()
    
    # 1. COMMANDS PREFIXED WITH '!'
    if m_low.startswith("!"):
        
        # --- PERSONALIZATION ---
        if m_low.startswith("!setbg "):
            url = msg.split(" ", 1)[1].strip()
            if "http" in url:
                db_set_bg(user, url)
                send_ws_msg(f"✅ @{user}, your welcome background is now set!")
            else: send_ws_msg("❌ Please provide a direct Image URL.")
            return

        # --- AI PERSONALITY SWITCH ---
        if m_low == "!mode ar":
            BOT_STATE["mode"] = "ar"; send_ws_msg("✅ Personality: ARABIC SHEIKH (Habibi Mode) 🐪"); return
        if m_low == "!mode en":
            BOT_STATE["mode"] = "en"; send_ws_msg("✅ Personality: SAVAGE ROASTER (English Mode) 🌍"); return
        if m_low == "!mode smart":
            BOT_STATE["mode"] = "smart"; send_ws_msg("✅ Personality: ADAPTIVE SMART AI 🧠"); return

        # --- GAMES ---
        if m_low.startswith(("!start", "!eat")):
            run_titan_engine(user, msg); return
            
        if m_low == "!magic":
            TITAN_GAME["magic_symbol"] = random.choice(["@", "#", "$", "%", "&", "§", "Δ", "Ω"])
            # The Magic Trick Grid (9 multiples have the target symbol)
            grid = "🔮 MIND READER GRID 🔮\n"
            for i in range(10, 50):
                sym = TITAN_GAME["magic_symbol"] if i % 9 == 0 else random.choice(["*", "?", "!", "+", "^", "="])
                grid += f"{i}:{sym}  "
                if i % 5 == 0: grid += "\n"
            send_ws_msg(f"{grid}\n\n1. Pick any number (10-99)\n2. Add digits (e.g., 23 -> 2+3=5)\n3. Subtract from original (23-5=18)\n4. See symbol for 18!\nCommand: !reveal when ready.")
            return

        if m_low == "!reveal":
            if TITAN_GAME["magic_symbol"]:
                send_ws_msg(f"✨ The symbol in your mind is: {TITAN_GAME['magic_symbol']}"); TITAN_GAME["magic_symbol"] = None
            return

        # --- GRAPHICS COMMANDS ---
        if m_low.startswith("!id"):
            target = m_low.split("@")[1].strip() if "@" in m_low else user
            avi = TITAN_GAME["cache_avatars"].get(target, "https://i.imgur.com/6EdJm2h.png")
            url = f"{BOT_STATE['domain']}api/id_card?u={target}&a={requests.utils.quote(avi)}"
            send_ws_msg(f"💳 Scanning Database for {target}...", "image", url); return

        if m_low.startswith("!ship"):
            target = m_low.split("@")[1].strip() if "@" in m_low else BOT_STATE["username"]
            score = random.randint(0, 100)
            a1 = TITAN_GAME["cache_avatars"].get(user, "https://i.imgur.com/6EdJm2h.png")
            a2 = TITAN_GAME["cache_avatars"].get(target, "https://i.imgur.com/6EdJm2h.png")
            url = f"{BOT_STATE['domain']}api/ship?u1={user}&u2={target}&a1={requests.utils.quote(a1)}&a2={requests.utils.quote(a2)}&s={score}"
            send_ws_msg(f"💘 Compatibility Check: {score}%", "image", url); return

        # --- TRIGGER MANAGEMENT ---
        if m_low.startswith("!addtg "):
            tg = msg.split(" ", 1)[1].lower()
            if tg not in BOT_STATE["triggers"]: BOT_STATE["triggers"].append(tg); send_ws_msg(f"✅ Reply Trigger Added: {tg}")
            return

    # 2. AI RESPONSE LOGIC (If tagged or trigger word found)
    my_name = BOT_STATE["username"].lower()
    if my_name in m_low or any(t in m_low for t in BOT_STATE["triggers"]):
        reply = groq_ai_engine(user, msg)
        if reply: send_ws_msg(f"@{user} {reply}")

# ==============================================================================
# --- SECTION 7: FLASK WEB SERVER (UI, APIs, CONTROL) ---
# ==============================================================================

@app.route('/')
def home():
    return render_template_string(HTML_DASHBOARD, connected=BOT_STATE["connected"])

@app.route('/leaderboard')
def leaderboard():
    data = db_get_leaderboard()
    return render_template_string(HTML_LB, users=data)

# --- IMAGE ENDPOINTS ---

@app.route('/api/welcome')
def api_wel():
    img = generate_welcome_card(request.args.get('u'), request.args.get('a'), request.args.get('bg'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/id_card')
def api_id():
    img = generate_id_card(request.args.get('u'), request.args.get('a'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/ship')
def api_ship():
    img = generate_ship_card(request.args.get('u1'), request.args.get('u2'), request.args.get('a1'), request.args.get('a2'), int(request.args.get('s')))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/winner')
def api_win():
    img = generate_winner_card(request.args.get('u'), request.args.get('a'), request.args.get('p'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

# --- SYSTEM CONTROLS ---

@app.route('/logs')
def get_logs(): return jsonify({"logs": SYSTEM_LOGS})

@app.route('/connect', methods=['POST'])
def start_bot():
    if BOT_STATE["connected"]: return jsonify({"status": "ALREADY ONLINE"})
    d = request.json
    BOT_STATE.update({
        "username": d["u"], "password": d["p"], "room_name": d["r"], 
        "domain": request.url_root
    })
    threading.Thread(target=ws_runner_thread).start()
    return jsonify({"status": "AUTHENTICATING..."})

@app.route('/disconnect', methods=['POST'])
def stop_bot():
    if BOT_STATE["ws"]: BOT_STATE["ws"].close()
    BOT_STATE["connected"] = False
    return jsonify({"status": "SYSTEM TERMINATED"})

def ws_runner_thread():
    """Main WebSocket Thread with Persistent Ping."""
    def on_open(ws):
        BOT_STATE["connected"] = True
        log("TITAN SYSTEM: WebSocket Tunnel Established.", "sys")
        # Login
        ws.send(json.dumps({"handler": "login", "id": str(time.time()), "username": BOT_STATE["username"], "password": BOT_STATE["password"], "platform": "web"}))
        # Keep-Alive Loop
        while BOT_STATE["connected"]:
            time.sleep(25)
            try: ws.send(json.dumps({"handler": "ping"}))
            except: break

    ws = websocket.WebSocketApp("wss://chatp.net:5333/server", on_open=on_open, on_message=on_socket_message, on_error=lambda w,e: log(f"WS ERROR: {e}", "err"), on_close=lambda w,c,m: log("WS CLOSED", "sys"))
    BOT_STATE["ws"] = ws
    ws.run_forever()

# ==============================================================================
# --- SECTION 8: HEAVY HTML TEMPLATES (CYBERPUNK NEON) ---
# ==============================================================================

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITAN ULTIMATE V6</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500&family=Roboto+Mono&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00f3ff; --bg: #050505; --panel: #111; --red: #ff003c; --green: #00ff41; }
        body { background: var(--bg); color: var(--neon); font-family: 'Roboto Mono', monospace; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .box { background: var(--panel); border: 1px solid #333; padding: 25px; border-left: 5px solid var(--neon); width: 100%; max-width: 600px; margin-bottom: 20px; border-radius: 4px; box-shadow: 0 0 20px rgba(0,243,255,0.05); }
        h1, h2 { font-family: 'Orbitron', sans-serif; margin-top: 0; color: #fff; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #000; color: #fff; border: 1px solid #444; box-sizing: border-box; }
        button { width: 48%; padding: 12px; font-weight: bold; cursor: pointer; border: none; font-family: 'Orbitron'; transition: 0.3s; }
        .btn-start { background: var(--neon); color: #000; }
        .btn-stop { background: var(--red); color: #fff; }
        .logs { height: 350px; overflow-y: scroll; background: #000; border: 1px solid #222; padding: 10px; font-size: 11px; }
        .type-err { color: var(--red); font-weight: bold; }
        .type-sys { color: #888; }
        .type-in { color: var(--green); }
        .type-out { color: var(--neon); }
        .status { margin-bottom: 10px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>TITAN MAX CONTROL</h1>
    <div class="box">
        <div class="status">SYSTEM STATUS: <span style="color: {{ 'lime' if connected else 'red' }}">{{ 'ONLINE' if connected else 'OFFLINE' }}</span></div>
        <input type="text" id="u" placeholder="Bot Username">
        <input type="password" id="p" placeholder="Bot Password">
        <input type="text" id="r" placeholder="Room Name">
        <div style="display:flex; justify-content:space-between;">
            <button class="btn-start" onclick="send('/connect')">START BOT</button>
            <button class="btn-stop" onclick="send('/disconnect')">SHUTDOWN</button>
        </div>
        <br><a href="/leaderboard" target="_blank" style="color:#fff; text-decoration:none;">🏆 OPEN LEADERBOARD</a>
    </div>
    <div class="box">
        <h2>LIVE SYSTEM LOGS</h2>
        <div class="logs" id="logs">Booting kernel...</div>
    </div>
    <script>
        function send(endpoint) {
            const data = { u: document.getElementById('u').value, p: document.getElementById('p').value, r: document.getElementById('r').value };
            fetch(endpoint, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
            .then(res => res.json()).then(d => alert("Response: " + d.status));
        }
        setInterval(() => {
            fetch('/logs').then(res => res.json()).then(data => {
                const logDiv = document.getElementById('logs');
                logDiv.innerHTML = data.logs.reverse().map(l => `<div class="type-${l.type}">[${l.time}] [${l.type.toUpperCase()}] ${l.msg}</div>`).join('');
            });
        }, 2000);
    </script>
</body>
</html>
"""

HTML_LB = """
<!DOCTYPE html><html><head><title>TITAN RANKINGS</title><style>
body{background:#050505;color:#fff;font-family:sans-serif;text-align:center;padding:30px;}
.card{background:#111;margin:10px auto;padding:15px;width:90%;max-width:500px;display:flex;align-items:center;justify-content:space-between;border-left:5px solid #00f3ff;border-radius:5px;}
.avi{width:50px;height:50px;border-radius:50%;border:2px solid #fff;}
.score{color:#00ff41;font-size:1.5em;font-weight:bold;}
</style></head><body><h1>TITAN GLOBAL RANKINGS</h1>
{% for u in users %}<div class="card"><div style="display:flex;align-items:center;gap:15px;">
<span>#{{ loop.index }}</span><img src="{{ u[3] }}" class="avi">
<div style="text-align:left;"><b>{{ u[0] }}</b><br><small>Wins: {{ u[2] }}</small></div></div>
<div class="score">{{ u[1] }}</div></div>{% endfor %}</body></html>
"""

# ==============================================================================
# --- 9. APP ENTRY POINT ---
# ==============================================================================

if __name__ == '__main__':
    # Initialize DB on start
    init_database()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)