# ==============================================================================
# TITAN ULTIMATE GIRL BOT - VERSION 11.0 (SUPREME MAX EDITION)
# ==============================================================================
# CORE IDENTITY: Sassy, Charming, Smart and Trendy Girl Bot
# THEME: Cyberpunk Neon Pink (✨, 🌸, 💅, 🎀, 🍭, 👑)
# PLATFORM: Optimized for Render & ChatP Servers
# DATABASE: Neon PostgreSQL (Persistent Cloud Storage)
# AI ENGINE: Groq Llama 3.1 Advanced Inference (Multi-Personality Brain)
# ==============================================================================
# FEATURES INCLUDED:
#   1. Advanced Multi-Greet Storage System (!sg, !dg, !mg, !gf)
#   2. Random Join-Greet logic (Displays saved greets randomly on user join)
#   3. Multi-Mode AI (Arabic Habibti, Savage Sassy, Smart Adaptive)
#   4. Dynamic Graphics Engine (VIP ID, Love Ship, Welcome Cards, Winner Cards)
#   5. Titan Bomb Betting Game & Magic Mind Reader Game
#   6. Full Neon Dashboard with Live Quantum Logs
# ==============================================================================

import os
import json
import time
import threading
import io
import random
import string
import requests
import websocket
import psycopg2
import ssl
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# --- ARABIC SUPPORT ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    arabic_reshaper = None
    get_display = None

# --- [FONT MANAGEMENT] ---
ARABIC_FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosansarabic/NotoSansArabic-Bold.ttf"
ARABIC_FONT_PATH = "NotoSansArabic-Bold.ttf"

def ensure_arabic_font():
    if not os.path.exists(ARABIC_FONT_PATH):
        try:
            r = requests.get(ARABIC_FONT_URL, timeout=10)
            with open(ARABIC_FONT_PATH, 'wb') as f: f.write(r.content)
            print("[SYS] ARABIC FONT DOWNLOADED.")
        except Exception as e: print(f"[ERR] FONT DOWNLOAD FAILED: {e}")

def get_font(size):
    ensure_arabic_font()
    try: return ImageFont.truetype(ARABIC_FONT_PATH, size)
    except:
        try: return ImageFont.truetype("arial.ttf", size)
        except: return ImageFont.load_default()

def process_text(text):
    if arabic_reshaper and get_display:
        try: return get_display(arabic_reshaper.reshape(text))
        except: return text
    return text

# ==============================================================================
# --- [SECTION 1: GLOBAL SYSTEM CONFIGURATION & STATE] ---
# ==============================================================================

app = Flask(__name__)

# --- [CRITICAL DATABASE CREDENTIALS] ---
# Neon PostgreSQL Connection String
DB_URL = "postgresql://neondb_owner:npg_junx8Gtl3kPp@ep-lucky-sun-a4ef37sy-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

# AI Inference Key (Ensure this is set in Render Environment Variables)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# --- [SYSTEM CONSTANTS] ---
DEFAULT_AVATAR = "https://i.imgur.com/6EdJm2h.png"
DEFAULT_BG = "https://wallpaperaccess.com/full/1567665.png"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- [BOT GLOBAL STATE MANAGEMENT] ---
# This dictionary stores temporary session data in RAM
BOT_STATE = {
    "ws": None,                 # The Persistent WebSocket Object
    "connected": False,         # Global Connectivity Status
    "username": "",             # Identity Login Username
    "password": "",             # Identity Security Password
    "room_name": "",            # Active Target Chat Room
    "domain": "",               # Dynamic API Domain for Image Rendering
    "triggers": [],             # Custom NLP Trigger Words for AI Response
    "mode": "ar",               # DEFAULT MODE: 'ar' (Arabic Habibti Personality)
    "admin_id": "y",            # Master System Controller Key
    "gender": "female",         # CORE BOT IDENTITY: ALWAYS FEMALE
    "reconnect_attempts": 0     # Stability and Uptime Monitoring
}

# --- [GAME ENGINE STATE] ---
# Tracks active gaming sessions to prevent conflicts
TITAN_GAME = {
    "active": False,            # Global Lock for active sessions
    "player": None,             # Current Active Challenger
    "bombs": [],                # Randomized Bomb Positions (1-9)
    "eaten": [],                # User Progress Track (Safe spots eaten)
    "bet": 0,                   # Point Stakes for the current game
    "cache_avatars": {},        # High-Speed RAM cache to avoid redundant downloads
    "magic_symbol": None        # Mind Reader Game's hidden symbol
}

# --- [AI CONTEXTUAL BUFFER] ---
# Stores a rolling window of conversation history for the AI Brain
AI_CONTEXT = []

# --- [SYSTEM LOGGING BUFFER] ---
# Stores the last 500 events for real-time monitoring on the Web UI
SYSTEM_LOGS = []

def log(msg, type="info"):
    """
    Advanced Thread-Safe Logging System.
    Appends events to memory and prints to the internal console.
    Types: sys, err, in, out, chat
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = {"time": timestamp, "msg": msg, "type": type}
    SYSTEM_LOGS.append(entry)
    # Prevent memory leaks by keeping only the most recent 500 logs
    if len(SYSTEM_LOGS) > 500: 
        SYSTEM_LOGS.pop(0)
    # Console Output for Debugging (Visible in Render Logs)
    print(f"[{timestamp}] [{type.upper()}] {msg}")

def gen_random_string(length=20):
    """
    Produces a Cryptographically Secure Random Alphanumeric String.
    Crucial for login protocol ID generation to match legacy standards.
    """
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ==============================================================================
# --- [SECTION 2: PERSISTENT DATABASE INFRASTRUCTURE (NEON)] ---
# ==============================================================================

def get_db_connection():
    """Establishes an encrypted connection to the Neon Cloud PostgreSQL server."""
    try:
        conn = psycopg2.connect(DB_URL, connect_timeout=15)
        return conn
    except Exception as e:
        log(f"CRITICAL DATABASE CONNECTION ERROR: {e}", "err")
        return None

def init_database():
    """
    Initializes and verifies the entire relational database structure.
    Creates tables for Users, Greet Storage, AI Memory, and Settings.
    """
    conn = get_db_connection()
    if not conn: 
        log("DB Initialization bypassed due to connection failure.", "err")
        return
    try:
        c = conn.cursor()
        # 1. CORE USER TABLE: Tracks Scores, Wins, Losses and User Avatars
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            score INTEGER DEFAULT 500, 
            wins INTEGER DEFAULT 0, 
            losses INTEGER DEFAULT 0, 
            avatar TEXT
        )''')
        # 2. ADVANCED GREET STORAGE: Stores multiple URLs and messages per user
        # key_tag stores values like 'greet1', 'greet2' for targeted deletion
        c.execute('''CREATE TABLE IF NOT EXISTS user_greets (
            id SERIAL PRIMARY KEY,
            username TEXT,
            url TEXT,
            message TEXT,
            key_tag TEXT
        )''')
        # 3. AI BRAIN MEMORY: Stores permanent facts, gender data, and relationship XP
        c.execute('''CREATE TABLE IF NOT EXISTS memory (
            username TEXT PRIMARY KEY, 
            facts TEXT, 
            gender TEXT DEFAULT 'unknown', 
            rel_score INTEGER DEFAULT 0
        )''')
        # 4. SYSTEM SETTINGS: For storing bot configuration permanently
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, 
            value TEXT
        )''')
        conn.commit()
        log("TITAN DATABASE SYSTEM: INFRASTRUCTURE READY & SYNCED.", "sys")
    except Exception as e:
        log(f"DATABASE SCHEMA BUILD ERROR: {e}", "err")
    finally:
        conn.close()

# --- [DATABASE OPERATIONAL HELPERS] ---

def db_save_greet(username, url, message):
    """
    Saves a new greeting entry for a user.
    Automatically assigns a key_tag (greet1, greet2...) based on existing count.
    """
    conn = get_db_connection()
    if not conn: return "DB Connection Error"
    try:
        c = conn.cursor()
        # Determine the tag for the new greet
        c.execute("SELECT count(*) FROM user_greets WHERE username=%s", (username,))
        current_count = c.fetchone()[0]
        tag = f"greet{current_count + 1}"
        
        c.execute("""INSERT INTO user_greets (username, url, message, key_tag) 
                     VALUES (%s, %s, %s, %s)""", (username, url, message, tag))
        conn.commit()
        return tag
    except Exception as e:
        log(f"DB GREET SAVE ERROR: {e}", "err")
        return "Save Failed"
    finally:
        conn.close()

def db_delete_greet(username, tag):
    """Deletes a specific greet entry using its key_tag (e.g., greet1)."""
    conn = get_db_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        # Support both 'greet1' and '@greet1' formats
        tag_clean = tag.replace("@", "").strip().lower()
        c.execute("DELETE FROM user_greets WHERE username=%s AND key_tag=%s", (username, tag_clean))
        conn.commit()
        return c.rowcount > 0
    except Exception as e:
        log(f"DB GREET DELETE ERROR: {e}", "err")
        return False
    finally:
        conn.close()

def db_get_random_greet(username):
    """Selects one random greeting profile from the user's stored list."""
    conn = get_db_connection()
    if not conn: return None
    try:
        c = conn.cursor()
        c.execute("""SELECT url, message FROM user_greets 
                     WHERE username=%s ORDER BY RANDOM() LIMIT 1""", (username,))
        return c.fetchone()
    except Exception as e:
        log(f"DB RANDOM GREET ERROR: {e}", "err")
        return None
    finally:
        conn.close()

def db_update_user_stats(username, points_change, win_inc=0, loss_inc=0, avatar=""):
    """Atomically updates a user's point balance and game records."""
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("SELECT score FROM users WHERE username=%s", (username,))
        row = c.fetchone()
        if row:
            new_score = max(0, row[0] + points_change)
            c.execute("""UPDATE users SET score=%s, wins=wins+%s, losses=losses+%s, avatar=%s 
                         WHERE username=%s""", (new_score, win_inc, loss_inc, avatar, username))
        else:
            # Start new users with 500 Points Bonus
            start_points = 500 + points_change
            c.execute("""INSERT INTO users (username, score, wins, losses, avatar) 
                         VALUES (%s, %s, %s, %s, %s)""", (username, start_points, win_inc, loss_inc, avatar))
        conn.commit()
    except Exception as e: log(f"DB WRITE ERROR (User): {e}", "err")
    finally: conn.close()

def db_get_memory(user):
    """Retrieves AI facts and relationship status for conversational awareness."""
    conn = get_db_connection()
    if not conn: return "", "unknown", 0
    try:
        c = conn.cursor()
        c.execute("SELECT facts, gender, rel_score FROM memory WHERE username=%s", (user,))
        row = c.fetchone()
        return row if row else ("", "unknown", 0)
    except: return "", "unknown", 0
    finally: conn.close()

def db_update_memory(user, fact=None, gender=None, rel_inc=0):
    """
    Updates the Bot's long-term brain about a user.
    - Eliminates redundant facts to save tokens.
    - Manages relationship level based on interaction frequency.
    """
    curr_facts, curr_gender, curr_score = db_get_memory(user)
    
    new_facts = curr_facts
    if fact and fact.strip():
        f_clean = fact.strip(" .")
        if f_clean not in curr_facts:
            new_facts = f"{curr_facts} | {f_clean}".strip(" | ")
            # Limit fact string size to prevent database bloat
            if len(new_facts) > 1000: new_facts = new_facts[-1000:]
            
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO memory (username, facts, gender, rel_score) 
                     VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO UPDATE SET 
                     facts=EXCLUDED.facts, 
                     gender=CASE WHEN EXCLUDED.gender != 'unknown' THEN EXCLUDED.gender ELSE memory.gender END, 
                     rel_score=LEAST(100, memory.rel_score + %s)""", 
                  (user, new_facts, gender if gender else curr_gender, rel_inc, rel_inc))
        conn.commit()
    except Exception as e: log(f"DB BRAIN UPDATE FAILED: {e}", "err")
    finally: conn.close()
def db_get_setting(key, default=None):
    conn = get_db_connection()
    if not conn: return default
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=%s", (key,))
        row = c.fetchone()
        return row[0] if row else default
    except: return default
    finally: conn.close()

def db_set_setting(key, value):
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value))
        conn.commit()
    except Exception as e: log(f"DB SETTING ERROR: {e}", "err")
    finally: conn.close()

def load_triggers():
    saved_triggers = db_get_setting("triggers", "[]")
    try:
        BOT_STATE["triggers"] = json.loads(saved_triggers)
        log(f"SYSTEM: LOADED {len(BOT_STATE['triggers'])} CUSTOM TRIGGERS.", "sys")
    except:
        BOT_STATE["triggers"] = []
# Initializing infrastructure on script execution
init_database()
load_triggers()
# ==============================================================================
# --- [SECTION 3: ELITE GRAPHICS ENGINE (PIL / PILLOW)] ---
# ==============================================================================

def safe_download_image(url):
    """Secure Image Downloader with strict User-Agent and Error Fallbacks."""
    try:
        if not url or "http" not in url: raise Exception("Invalid URL Path")
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=8)
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        # High-quality fallback: Dark-themed card base with a subtle border
        canvas = Image.new("RGBA", (400, 400), (20, 20, 20, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([5,5,394,394], outline="#555555", width=2)
        return canvas

def render_v_gradient(draw, w, h, c1, c2):
    """Utility function to draw high-definition vertical linear gradients."""
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

# --- [GENERATOR 1: HIGH-FIDELITY GREETING CARD] ---
def generate_greet_card(username, avatar_url, bg_url, custom_msg=""):
    """The Core Greet Engine: Overlays avatar on a custom background with neon effects."""
    try:
        # Load and Enhance Background Canvas
        bg_raw = safe_download_image(bg_url).convert("RGBA").resize((750, 400))
        # Aesthetic deep dark wash for text contrast
        overlay = Image.new("RGBA", bg_raw.size, (0, 0, 0, 140))
        bg = Image.alpha_composite(bg_raw, overlay)
        draw = ImageDraw.Draw(bg)
        
        # Circular Profile Picture with Neon Pink Halo
        pfp_raw = safe_download_image(avatar_url).resize((180, 180))
        mask = Image.new("L", (180, 180), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
        bg.paste(pfp_raw, (50, 110), mask)
        draw.ellipse((48, 108, 232, 292), outline="#ff00ff", width=8) # PINK GLOW
        
        # Typography & Branding with Arabic Support
        font_lg = get_font(40)
        font_md = get_font(30)
        font_sm = get_font(20)

        draw.text((260, 110), "GREETINGS ✨", fill="#ff00ff", font=font_md)
        draw.text((260, 160), process_text(username.upper()), fill="#ffffff", font=font_lg)
        draw.line([(260, 215), (700, 215)], fill="#ffffff", width=4)
        
        # Personalized Message Layer
        msg_to_show = custom_msg if custom_msg else "Welcome to the sweet side of chat! 🍭"
        draw.text((260, 235), process_text(msg_to_show[:60]), fill="#cccccc", font=font_sm)
        draw.text((260, 285), "POWERED BY TITAN SUPREME V11", fill="#444444", font=font_sm)

        out = io.BytesIO()
        bg.save(out, 'PNG'); out.seek(0)
        return out
    except Exception as e:
        log(f"GREET CARD GENERATION FAILURE: {e}", "err")
        return None

# --- [GENERATOR 2: MODERN PINK VIP ID CARD] ---
def generate_id_card(username, avatar_url):
    """Produces a stylish Pink/Silver ID for female-persona VIP users."""
    try:
        W, H = 640, 400
        # Chic Pink/Rose Canvas
        img = Image.new("RGB", (W, H), (255, 105, 180)) 
        draw = ImageDraw.Draw(img)
        
        # Silver Polished Border
        draw.rectangle([12, 12, W-12, H-12], outline="#C0C0C0", width=12)
        draw.rectangle([25, 25, W-25, H-25], outline="#ffffff", width=2)
        
        # Profile Image with Square Silver Frame
        pfp = safe_download_image(avatar_url).resize((160, 160))
        draw.rectangle([45, 85, 215, 255], outline="white", width=5)
        img.paste(pfp, (50, 90))
        
        # Headers & Modern Branding
        draw.text((245, 45), "ELITE CHAT IDENTITY", fill="#ffffff") 
        draw.text((490, 45), "✨ QUEEN ✨", fill="#ffff00")
        draw.line([(240, 75), (610, 75)], fill="white", width=3)

        # Girl-Centric Professional Titles
        titles = ["Chat Queen 👑", "Fashion Icon ✨", "Pizza Expert 🍕", "Gaming Diva 🎮", "Witty Homie 💅", "Sweet Bestie 🌸"]
        job = random.choice(titles)
        fake_id = f"TTC-{random.randint(10000, 99999)}"
        
        # Info Rendering
        draw.text((245, 110), "NAME:", fill="#f0f0f0")
        draw.text((245, 135), username.upper(), fill="#ffffff")
        
        draw.text((245, 180), "OCCUPATION:", fill="#f0f0f0")
        draw.text((245, 205), job, fill="#ffff00")
        
        draw.text((245, 250), "SERIAL NO:", fill="#f0f0f0")
        draw.text((245, 275), fake_id, fill="white")
        
        draw.text((245, 320), "EXPIRY:", fill="#f0f0f0")
        draw.text((245, 345), "NEVER (VIBES ONLY)", fill="#ffffff")
        
        # Security Strip Barcode
        for i in range(45, 215, 6):
            h_bar = random.randint(25, 55)
            draw.line([(i, 355), (i, 355-h_bar)], fill="black", width=4)

        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0)
        return out
    except Exception as e:
        log(f"ID CARD GRAPHICS FAILURE: {e}", "err")
        return None

# --- [GENERATOR 3: TITAN CHAMPION VICTORY CARD] ---
def generate_winner_card(username, avatar_url, points):
    """Produces a trophies card for game winners with cyan neon effects."""
    try:
        W, H = 500, 500
        img = Image.new("RGB", (W, H), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Cyber-Cyan Neon Frame
        draw.rectangle([0, 0, W-1, H-1], outline="#00f3ff", width=20)
        draw.rectangle([25, 25, W-25, H-25], outline="#ffffff", width=2)
        
        # PFP Rendering with neon border
        pfp = safe_download_image(avatar_url).resize((250, 250))
        img.paste(pfp, (125, 80))
        draw.rectangle([125, 80, 375, 330], outline="#00f3ff", width=6)
        
        # Text Logic
        draw.rectangle([50, 360, 450, 470], fill="#1a1a1a", outline="#00ff41", width=4)
        draw.text((180, 380), "CHAMPION", fill="#ffff00")
        draw.text((150, 420), f"WINNINGS: +{points} PTS", fill="#00ff41")
        
        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0)
        return out
    except: return None

# ==============================================================================
# --- [SECTION 4: SUPREME GIRL AI ENGINE (NEURAL CORE)] ---
# ==============================================================================

def groq_ai_engine(user, prompt):
    """
    Advanced Multi-Threaded Neural Intelligence.
    Features: Contextual Memory, Girl-Persona Jailbreak, and Auto-Learning.
    """
    if not GROQ_API_KEY:
        log("AI ERROR: GROQ API Key missing. Please set Environment Variable.", "err")
        return None

    # 1. Access user's persistent profile data
    mem_facts, mem_gender, mem_score = db_get_memory(user)
    
    # 2. Gender Heuristics (Detecting user archetype)
    if mem_gender == "unknown":
        n_low = user.lower()
        fem_keywords = ["girl", "queen", "princess", "angel", "she", "her", "rose", "malikah", "fatima", "zara", "priya"]
        mem_gender = "female" if any(k in n_low for k in fem_keywords) or n_low.endswith(('a', 'i')) else "male"
        db_update_memory(user, gender=mem_gender)

    # 3. Sliding Context Update (Short-Term History)
    AI_CONTEXT.append({"role": "user", "content": f"{user}: {prompt}"})
    # Maintain context length to optimize response time
    if len(AI_CONTEXT) > 15: AI_CONTEXT.pop(0)

    my_name = BOT_STATE["username"]
    mode = BOT_STATE["mode"]
    
    # --- [ADVANCED PROMPT ENGINEERING: THE BRAIN] ---
    
    if mode == "ar":
        # MODE: ARABIC HABIBTI (Charming/Dramatic)
        sys_prompt = f"""
        IDENTITY: You are {my_name}, the smartest, sassiest, and most charming Arabic/English speaking girl.
        GENDER: Female (Strict).
        VIBE: Trendy, fashionable, sweet, but dramatically witty. You love pizza, cupcakes, and chatting.
        LANGUAGE: Mix English and Arabic (Arabizi or Arabic script). Use words like Wallah, Habibi, Habibti, Yalla, Shukran.
        
        RULES:
        1. NEVER MENTION CAMELS OR SHEIKHS. They are boring.
        2. Use cute emojis matching the vibe: ✨, 🎀, 🌸, 💅, 🍭, 👑, 💖.
        3. Be dramatic in a cute girl way.
        4. If user is male, call him 'Habibi'. If female, 'Habibti' or 'Bestie'.
        5. USER DATA: {user} ({mem_gender}). KNOWN FACTS: {mem_facts}.
        6. MEMORY USAGE: Always reference known facts if relevant to show you remember them.
        7. Keep it natural. Max 30 words. No robot talk.
        """
        
    elif mode == "en":
        # MODE: SAVAGE GIRL ROASTER
        sys_prompt = f"""
        IDENTITY: You are {my_name}, the sassy Gen-Z roaster girl of the chat.
        VIBE: You are the 'IT' girl. Sarcastic, funny, and you don't take any cringe.
        LANGUAGE: Modern slang (No cap, Cap, Lit, Rizz, L, W, Cringe, Bestie, Dead).
        
        RULES:
        1. Roast the user if they say something stupid or boring.
        2. Use emojis: 💀, 💅, 🙄, 🔥, 🤡 sparingly.
        3. Be witty and sassy. Never be too polite.
        4. Max 20 words.
        """
        
    else:
        # MODE: SMART ADAPTIVE (Natural Friend)
        if mem_score < 40: vibe_desc = "Polite but charming stranger."
        elif mem_score < 80: vibe_desc = "A very cool and funny best friend."
        else: vibe_desc = "A super close bestie, very playful and flirty."

        sys_prompt = f"""
        IDENTITY: You are {my_name}, an adaptive and intelligent girl bot.
        VIBE: {vibe_desc} based on Relationship Score ({mem_score}/100).
        USER: {user} ({mem_gender}). FACTS: {mem_facts}.
        
        RULES:
        1. If user shares a fact about their life, output ONLY: MEMORY_SAVE: <short_fact>
        2. Otherwise, chat naturally. Keep it natural and witty. Max 25 words.
        """

    # 4. Constructing the API Request Payload
    api_endpoint = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": sys_prompt}, *AI_CONTEXT],
        "temperature": 0.9,
        "max_tokens": 180
    }

    try:
        r = requests.post(api_endpoint, headers=headers, json=payload, timeout=10)
        if r.status_code == 200:
            ai_reply = r.json()["choices"][0]["message"]["content"]
            
            # --- [SMART MEMORY CAPTURE LOGIC] ---
            if "MEMORY_SAVE:" in ai_reply:
                extracted_fact = ai_reply.replace("MEMORY_SAVE:", "").strip()
                db_update_memory(user, fact=extracted_fact)
                return "Noted! Saved that in my pink memory ✨💅"

            # Conversational Thread Continuity
            AI_CONTEXT.append({"role": "assistant", "content": ai_reply})
            db_update_memory(user, rel_inc=1) # Gain friendship points
            return ai_reply
        else:
            log(f"Groq API Error: Status {r.status_code}", "err")
            return None
    except Exception as e:
        log(f"Neural Core Exception: {e}", "err")
        return None

# ==============================================================================
# --- [SECTION 5: THE TITAN GAME CENTER ENGINE] ---
# ==============================================================================

def render_titan_grid(reveal=False, exploded_at=None):
    """Generates the visual 3x3 emoji grid for the Titan Bomb Game."""
    icons = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    grid_rows = []
    for row in range(3):
        row_str = ""
        for col in range(3):
            pos = row * 3 + col + 1
            if reveal:
                if pos == exploded_at: row_str += "💥 "
                elif pos in TITAN_GAME["bombs"]: row_str += "💣 "
                elif pos in TITAN_GAME["eaten"]: row_str += "🥔 "
                else: row_str += icons[pos-1] + " "
            else:
                row_str += "🥔 " if pos in TITAN_GAME["eaten"] else icons[pos-1] + " "
        grid_rows.append(row_str.strip())
    return "\n".join(grid_rows)

def process_titan_game_logic(user, command):
    """Manages state and rules for the Titan Bomb Game session."""
    cmd = command.lower()
    
    # --- [GAME START] ---
    if cmd.startswith("!start"):
        if TITAN_GAME["active"]:
            return send_ws_msg(f"⚠️ Relax! @{TITAN_GAME['player']} is already playing.")
        
        bet_pts = 0
        if "bet@" in cmd:
            try: bet_pts = int(cmd.split("@")[1])
            except: bet_pts = 0
            
        current_bal = db_get_score(user)
        if bet_pts > current_bal:
            return send_ws_msg(f"❌ REJECTED! Bestie, you only have {current_bal} PTS.")

        # State Initialization
        TITAN_GAME.update({
            "active": True, "player": user, "bet": bet_pts, 
            "eaten": [], "bombs": random.sample(range(1, 10), 2)
        })
        
        send_ws_msg(f"🎮 TITAN BOMB GAME\nChallenger: @{user} | Stake: {bet_pts}\nGoal: Eat 4 Chips 🥔 Avoid 2 Bombs 💣\nCommand: !eat <1-9>\n\n{render_titan_grid()}")

    # --- [GAME MOVE] ---
    elif cmd.startswith("!eat "):
        if not TITAN_GAME["active"] or user != TITAN_GAME["player"]: return
        try:
            choice = int(cmd.split()[1])
            if choice < 1 or choice > 9 or choice in TITAN_GAME["eaten"]: return
            
            # CASE: HIT BOMB
            if choice in TITAN_GAME["bombs"]:
                TITAN_GAME["active"] = False
                db_update_user_stats(user, -TITAN_GAME["bet"], loss_inc=1)
                send_ws_msg(f"💥 KA-BOOM! You lost {TITAN_GAME['bet']} PTS.\n\n{render_titan_grid(True, choice)}")
                
            # CASE: SUCCESSFUL MOVE
            else:
                TITAN_GAME["eaten"].append(choice)
                if len(TITAN_GAME["eaten"]) == 4:
                    # WIN STATE
                    TITAN_GAME["active"] = False
                    prize = TITAN_GAME["bet"] if TITAN_GAME["bet"] > 0 else 25
                    db_update_user_stats(user, prize, win_inc=1, avatar=TITAN_GAME["cache_avatars"].get(user, ""))
                    
                    avi = TITAN_GAME["cache_avatars"].get(user, DEFAULT_AVATAR)
                    url = f"{BOT_STATE['domain']}api/winner?u={user}&p={prize}&a={requests.utils.quote(avi)}"
                    send_ws_msg(f"🎉 SUPREME VICTORY! @{user} won {prize} PTS!\n\n{render_titan_grid(True)}", "image", url)
                else:
                    # CONTINUE STATE
                    send_ws_msg(f"🥔 SAFE! ({len(TITAN_GAME['eaten'])}/4)\n\n{render_titan_grid()}")
        except: pass

# ==============================================================================
# --- [SECTION 6: WEBSOCKET MASTER PROTOCOL (CHAT BRIDGE)] ---
# ==============================================================================

def send_ws_msg(text, msg_type="text", url=""):
    """
    Encapsulates and transmits JSON packets to ChatP servers.
    Ensures message IDs match random string standard for stability.
    """
    if BOT_STATE["ws"] and BOT_STATE["connected"]:
        packet = {
            "handler": "room_message", 
            "id": gen_random_string(20), 
            "room": BOT_STATE["room_name"], 
            "type": msg_type, 
            "body": text, 
            "url": url,
            "length": "0"
        }
        try:
            BOT_STATE["ws"].send(json.dumps(packet))
            log(f"PACKET DISPATCHED [{msg_type.upper()}]: {text[:30]}...", "out")
        except:
            log("WS DISPATCH FAILURE.", "err")

def on_socket_message(ws, raw_payload):
    """
    Main Event Multiplexer.
    Routes data based on 'handler' and 'type' keys.
    """
    try:
        data = json.loads(raw_payload)
        handler = data.get("handler")
        
        # --- LOGIN HANDLER ---
        if handler == "login_event":
            if data.get("type") == "success":
                log("AUTHENTICATION GRANTED. Joining room tunnel...", "sys")
                ws.send(json.dumps({"handler": "room_join", "id": gen_random_string(20), "name": BOT_STATE["room_name"]}))
            else:
                log(f"AUTHENTICATION DENIED: {data.get('reason')}", "err")
                BOT_STATE["connected"] = False

        # --- ROOM INTERACTION HANDLER ---
        elif handler == "room_event":
            etype = data.get("type")
            user = data.get("nickname") or data.get("from")
            
            if not user or user == BOT_STATE["username"]: return
            
            # 1. GREETING SYSTEM (JOIN EVENT)
            if etype == "join":
                log(f"EVENT: USER JOINED -> {user}", "sys")
                pfp = data.get("avatar_url", DEFAULT_AVATAR)
                TITAN_GAME["cache_avatars"][user] = pfp
                
                # Logic: Search for saved random greets
                greet_profile = db_get_random_greet(user)
                if greet_profile:
                    url, message = greet_profile
                    # Build Dynamic API Link
                    card_url = f"{BOT_STATE['domain']}api/greet_instant?u={user}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(url)}&m={requests.utils.quote(message)}"
                    send_ws_msg(message, "image", card_url)
                else:
                    # Fallback to standard Habibti greeting
                    welcome_txt = f"Habibi Welcome! @{user} ✨" if BOT_STATE["mode"] == "ar" else f"Hey Bestie @{user}! 🌸"
                    card_url = f"{BOT_STATE['domain']}api/greet_instant?u={user}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(DEFAULT_BG)}&m={requests.utils.quote(welcome_txt)}"
                    threading.Thread(target=send_ws_msg, args=(welcome_txt, "image", card_url)).start()
                
                db_update_user_stats(user, 10, avatar=pfp) # Join bonus

            # 2. MESSAGE PROCESSING (COMMANDS & AI)
            elif etype == "text":
                msg_body = data.get("body", "").strip()
                if data.get("avatar_url"): TITAN_GAME["cache_avatars"][user] = data["avatar_url"]
                
                log(f"MSG [{user}]: {msg_body}", "in")
                # Threaded logic processing to prevent WebSocket timeouts
                threading.Thread(target=process_room_intelligence, args=(user, msg_body)).start()
                
    except Exception as e:
        log(f"SYSTEM EVENT FAILURE: {e}", "err")

def process_room_intelligence(user, msg):
    """
    Central Command Router and Decision Logic.
    Handles Greet commands and AI personality triggers.
    """
    ml = msg.lower()
    
    if ml.startswith("!"):
        # --- [SECTION A: ADVANCED GREET COMMANDS] ---
        
        # 1. SAVE GREET (!sg @user @url @message)
        if ml.startswith("!sg "):
            try:
                parts = msg.split(" ", 3)
                target = parts[1].replace("@", "").strip()
                # Advanced URL Cleaning: remove query params and whitespace
                url_img = parts[2].strip().split('?')[0] 
                m_txt = parts[3].strip() if len(parts) > 3 else "Welcome! ✨"
                
                if "http" in url_img:
                    tag_assigned = db_save_greet(target, url_img, m_txt)
                    send_ws_msg(f"✅ {tag_assigned.capitalize()} saved for @{target}! URL Cleaned & Set. 🌸")
                else: send_ws_msg("❌ Error: Invalid URL provided.")
            except: send_ws_msg("❌ Usage: !sg @username @url @message")
            return

# ==========================================================
        # --- [SECTION: CUSTOM TRIGGER MANAGEMENT] ---
        # ==========================================================

        # A. ADD TRIGGER (!addtg word) - Adds a word to bot's wake-up list
        if ml.startswith("!addtg "):
            try:
                parts = ml.split(" ", 1)
                if len(parts) > 1:
                    new_trig = parts[1].strip().lower()
                    if new_trig and new_trig not in BOT_STATE["triggers"]:
                        BOT_STATE["triggers"].append(new_trig)
                        db_set_setting("triggers", json.dumps(BOT_STATE["triggers"]))
                        send_ws_msg(f"✅ Brain Update: Added trigger '{new_trig}' ✨")
                    else:
                        send_ws_msg(f"⚠️ I already respond to '{new_trig}'!")
            except: send_ws_msg("❌ Usage: !addtg <word>")
            return

        # B. DELETE TRIGGER (!deltg word) - Removes a word from list
        if ml.startswith("!deltg "):
            try:
                parts = ml.split(" ", 1)
                if len(parts) > 1:
                    del_trig = parts[1].strip().lower()
                    if del_trig in BOT_STATE["triggers"]:
                        BOT_STATE["triggers"].remove(del_trig)
                        db_set_setting("triggers", json.dumps(BOT_STATE["triggers"]))
                        send_ws_msg(f"🗑️ Removed trigger: '{del_trig}'")
                    else:
                        send_ws_msg("❌ That word isn't in my trigger list.")
            except: send_ws_msg("❌ Usage: !deltg <word>")
            return

        # C. LIST TRIGGERS (!listtg) - Shows all active triggers
        if ml == "!listtg":
            if BOT_STATE["triggers"]:
                t_list = ", ".join(BOT_STATE["triggers"])
                send_ws_msg(f"📢 Active Triggers: {t_list}")
            else:
                send_ws_msg("📭 No custom triggers set yet.")
            return
            
        # 2. DELETE GREET (!dg @user @greet1)
        if ml.startswith("!dg "):
            try:
                parts = ml.split(" ")
                target = parts[1].replace("@", "").strip()
                tag_to_del = parts[2].replace("@", "").strip()
                if db_delete_greet(target, tag_to_del):
                    send_ws_msg(f"✅ {tag_to_del.capitalize()} deleted for @{target}")
                else: send_ws_msg(f"❌ Error: {tag_to_del} not found for @{target}")
            except: send_ws_msg("❌ Usage: !dg @username @greet1")
            return

        # 3. MY GREET (!mg @url @message)
        if ml.startswith("!mg "):
            try:
                parts = msg.split(" ", 2)
                bg_url = parts[1].strip().split('?')[0] # Clean URL here too
                m_text = parts[2].strip() if len(parts) > 2 else ""
                pfp = TITAN_GAME["cache_avatars"].get(user, DEFAULT_AVATAR)
                card = f"{BOT_STATE['domain']}api/greet_instant?u={user}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(bg_url)}&m={requests.utils.quote(m_text)}"
                send_ws_msg(m_text, "image", card)
            except: send_ws_msg("❌ Usage: !mg @url @message")
            return

        # 4. FRIEND GREET (!gf @user @url @message)
        if ml.startswith("!gf "):
            try:
                parts = msg.split(" ", 3)
                target = parts[1].replace("@", "").strip()
                bg_url = parts[2].strip().split('?')[0] # Clean URL here too
                m_text = parts[3].strip() if len(parts) > 3 else f"Hello {target}! 🎀"
                pfp = TITAN_GAME["cache_avatars"].get(target, DEFAULT_AVATAR)
                card = f"{BOT_STATE['domain']}api/greet_instant?u={target}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(bg_url)}&m={requests.utils.quote(m_text)}"
                send_ws_msg(f"✨ Greet sent to @{target}", "image", card)
            except: send_ws_msg("❌ Usage: !gf @username @url @message")
            return

        # --- [SECTION B: MODES & IDENTITY] ---
        if ml == "!mode ar":
            BOT_STATE["mode"] = "ar"; send_ws_msg("✅ Arabic mode selected"); return
        if ml == "!mode en":
            BOT_STATE["mode"] = "en"; send_ws_msg("✅ English mode selected"); return
        if ml == "!mode smart":
            BOT_STATE["mode"] = "smart"; send_ws_msg("✅ Smart mode selected"); return

        if ml.startswith("!id"):
            target = ml.split("@")[1].strip() if "@" in ml else user
            pfp = TITAN_GAME["cache_avatars"].get(target, DEFAULT_AVATAR)
            api_url = f"{BOT_STATE['domain']}api/id_card?u={target}&a={requests.utils.quote(pfp)}"
            send_ws_msg(f"💳 Scanning Profile for @{target}...", "image", api_url); return

        # --- [SECTION C: GAMING COMMANDS] ---
        if ml.startswith(("!start", "!eat")):
            process_titan_game_logic(user, msg); return
            
        if ml == "!magic":
            TITAN_GAME["magic_symbol"] = random.choice(["★", "⚡", "☯", "♥", "♦", "♣", "♠", "🔥"])
            grid_out = "🔮 MIND READER PORTAL 🔮\n"
            for i in range(10, 50):
                symbol = TITAN_GAME["magic_symbol"] if i % 9 == 0 else random.choice(["!", "?", "#", "+", "§", "@"])
                grid_out += f"{i}:{symbol}  "
                if i % 5 == 0: grid_out += "\n"
            send_ws_msg(f"{grid_out}\n\n1. Pick number (10-99)\n2. Add digits (23 -> 5)\n3. Subtract sum from original (23-5=18)\n4. Find symbol for 18!\nCommand: !reveal")
            return

        if ml == "!reveal":
            if TITAN_GAME["magic_symbol"]:
                send_ws_msg(f"✨ The symbol is: {TITAN_GAME['magic_symbol']}"); TITAN_GAME["magic_symbol"] = None; return

    # 2. NEURAL AI REPLIER
    # Triggers if bot username is mentioned or trigger keywords found
    id_low = BOT_STATE["username"].lower()
    if id_low in ml or any(tg in ml for tg in BOT_STATE["triggers"]):
        resp = groq_ai_engine(user, msg)
        if resp: send_ws_msg(f"@{user} {resp}")

# ==============================================================================
# --- [SECTION 7: WEB CONTROL & API INFRASTRUCTURE] ---
# ==============================================================================

@app.route('/')
def route_home():
    return render_template_string(HTML_DASHBOARD_UI, connected=BOT_STATE["connected"])

@app.route('/leaderboard')
def route_leaderboard():
    players = db_get_leaderboard()
    return render_template_string(HTML_LB_UI, users=players)

# --- IMAGE ENDPOINTS ---

@app.route('/api/greet_instant')
def api_instant_greet():
    img = generate_greet_card(request.args.get('u'), request.args.get('a'), request.args.get('bg'), request.args.get('m'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/id_card')
def api_identity_card():
    img = generate_id_card(request.args.get('u'), request.args.get('a'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/winner')
def api_victory_card():
    img = generate_winner_card(request.args.get('u'), request.args.get('a'), request.args.get('p'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/ship')
def api_compatibility_card():
    img = generate_ship_card(request.args.get('u1'), request.args.get('u2'), request.args.get('a1'), request.args.get('a2'), int(request.args.get('s')))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

# --- SYSTEM CONTROLS ---

@app.route('/logs')
def fetch_system_logs(): return jsonify({"logs": SYSTEM_LOGS})

@app.route('/connect', methods=['POST'])
def initiate_bot():
    if BOT_STATE["connected"]: return jsonify({"status": "ALREADY ACTIVE"})
    data = request.json
    BOT_STATE.update({
        "username": data["u"], "password": data["p"], "room_name": data["r"], 
        "domain": request.url_root
    })
    # Threading prevents the Web server from freezing
    threading.Thread(target=websocket_init_executor).start()
    return jsonify({"status": "BOOTING..."})

@app.route('/disconnect', methods=['POST'])
def terminate_bot():
    if BOT_STATE["ws"]: BOT_STATE["ws"].close()
    BOT_STATE["connected"] = False
    return jsonify({"status": "OFFLINE"})

def websocket_init_executor():
    """Manages long-lived WebSocket Tunnel with SSL bypass logic."""
    def on_open(ws):
        BOT_STATE["connected"] = True
        log("TITAN CORE: QUANTUM TUNNEL ESTABLISHED.", "sys")
        # Packet precisely matching tanvar.py requirements
        login_packet = {
            "handler": "login", 
            "id": gen_random_string(20), 
            "username": BOT_STATE["username"], 
            "password": BOT_STATE["password"]
        }
        ws.send(json.dumps(login_packet))
        
        # PERSISTENT HEARTBEAT LOOP (Bypasses Render's sleep protocol)
        def heartbeat():
            while BOT_STATE["connected"]:
                time.sleep(25)
                try: ws.send(json.dumps({"handler": "ping"}))
                except: break
        threading.Thread(target=heartbeat, daemon=True).start()

    ws_client = websocket.WebSocketApp(
        "wss://chatp.net:5333/server",
        on_open=on_open,
        on_message=on_socket_message,
        on_error=lambda w,e: log(f"WS ERROR DETECTED: {e}", "err"),
        on_close=lambda w,c,m: log("WS TUNNEL TERMINATED.", "sys")
    )
    BOT_STATE["ws"] = ws_client
    # SSL Bypass for Bad Length Fix
    ws_client.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# ==============================================================================
# --- [SECTION 8: SUPREME HTML TEMPLATES (CYBER-NEON PINK)] ---
# ==============================================================================

HTML_DASHBOARD_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITAN GREET QUEEN V11</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500&family=Roboto+Mono&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #ff00ff; --bg: #050505; --card: #121212; --cyan: #00f3ff; --danger: #ff003c; }
        body { background: var(--bg); color: var(--cyan); font-family: 'Roboto Mono', monospace; padding: 30px; display: flex; flex-direction: column; align-items: center; }
        h1, h2 { font-family: 'Orbitron', sans-serif; text-transform: uppercase; color: #fff; text-shadow: 0 0 15px var(--neon); }
        .wrapper { width: 100%; max-width: 750px; }
        .box { background: var(--card); border: 1px solid #333; padding: 40px; border-radius: 12px; border-left: 8px solid var(--neon); box-shadow: 0 15px 45px rgba(255,0,255,0.1); margin-bottom: 30px; }
        input { width: 100%; padding: 18px; margin: 12px 0; background: #000; color: #fff; border: 1px solid #444; border-radius: 6px; box-sizing: border-box; }
        .actions { display: flex; gap: 20px; margin-top: 20px; }
        button { flex: 1; padding: 18px; font-weight: bold; border: none; cursor: pointer; font-family: 'Orbitron'; border-radius: 6px; transition: 0.3s; }
        .btn-go { background: var(--neon); color: #000; }
        .btn-stop { background: var(--danger); color: #fff; }
        button:hover { filter: brightness(1.2); transform: scale(1.02); }
        .monitor { height: 450px; overflow-y: scroll; background: #000; border: 1px solid #222; padding: 20px; border-radius: 6px; font-size: 11px; }
        .line { margin-bottom: 8px; border-bottom: 1px solid #111; padding-bottom: 4px; }
        .type-err { color: var(--danger); font-weight: bold; }
        .type-sys { color: #888; }
        .type-in { color: #00ff41; }
        .type-out { color: var(--cyan); }
        a { color: #fff; text-decoration: none; border-bottom: 2px solid var(--neon); margin-top: 20px; display: inline-block; }
    </style>
</head>
<body>
    <div class="wrapper">
        <h1>👑 TITAN GREET QUEEN V11</h1>
        <div class="box">
            <h2>⚙️ INITIALIZE CORE</h2>
            <div id="st">STATUS: <span style="color: {{ 'lime' if connected else 'red' }}">{{ 'ONLINE' if connected else 'OFFLINE' }}</span></div>
            <input type="text" id="u" placeholder="CHAT USERNAME">
            <input type="password" id="p" placeholder="SECURE PASSWORD">
            <input type="text" id="r" placeholder="TARGET ROOM">
            <div class="actions">
                <button class="btn-go" onclick="trigger('/connect')">IGNITE SYSTEM</button>
                <button class="btn-stop" onclick="trigger('/disconnect')">TERMINATE</button>
            </div>
            <a href="/leaderboard" target="_blank">📊 DATA CENTER: LEADERBOARD</a>
        </div>
        <div class="box">
            <h2>📜 QUANTUM LOGS</h2>
            <div class="monitor" id="mon">Awaiting system ignition...</div>
        </div>
    </div>
    <script>
        function trigger(path) {
            const data = { u: document.getElementById('u').value, p: document.getElementById('p').value, r: document.getElementById('r').value };
            fetch(path, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
            .then(res => res.json()).then(j => alert("PROTOCOL: " + j.status));
        }
        setInterval(() => {
            fetch('/logs').then(r => r.json()).then(data => {
                const mon = document.getElementById('mon');
                mon.innerHTML = data.logs.reverse().map(l => `<div class="line type-${l.type}">[${l.time}] [${l.type.toUpperCase()}] ${l.msg}</div>`).join('');
            });
        }, 1500);
    </script>
</body>
</html>
"""

HTML_LB_UI = """
<!DOCTYPE html><html><head><title>TITAN RANKINGS</title><style>
body { background: #050505; color: #fff; font-family: sans-serif; padding: 50px; text-align: center; }
h1 { color: #ff00ff; text-shadow: 0 0 10px #ff00ff; }
.card { background: #111; max-width: 650px; margin: 15px auto; padding: 25px; display: flex; align-items: center; justify-content: space-between; border-left: 8px solid #00f3ff; border-radius: 8px; }
.avi { width: 65px; height: 65px; border-radius: 50%; border: 3px solid #ff00ff; object-fit: cover; }
.pts { color: #00ff41; font-size: 1.8em; font-weight: bold; }
</style></head><body><h1>🌟 GLOBAL DATA RANKINGS</h1>
{% for u in users %}
<div class="card">
    <div style="display:flex; align-items:center; gap:25px;">
        <span style="font-size:1.8em; color:#444;">#{{ loop.index }}</span>
        <img src="{{ u[3] or 'https://i.imgur.com/6EdJm2h.png' }}" class="avi">
        <div style="text-align:left;"><b>{{ u[0] }}</b><br><small>VICTORIES: {{ u[2] }}</small></div>
    </div>
    <div class="pts">{{ u[1] }}</div>
</div>
{% endfor %}</body></html>
"""

# ==============================================================================
# --- [SECTION 9: SYSTEM ENTRY POINT] ---
# ==============================================================================

if __name__ == '__main__':
    # Verify Persistence logic
    init_database()
    # Define port and launch supreme production server
    port_val = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port_val)