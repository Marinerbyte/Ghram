# ==============================================================================
# TITAN ULTIMATE SYSTEM - VERSION 9.0 (ULTRA-HEAVYWEIGHT MAX EDITION)
# ==============================================================================
# DEVELOPED FOR: HIGH-PERFORMANCE CHAT AUTOMATION & AI INTERACTION
# CORE ARCHITECTURE: 
#   - FRONTEND: Cyberpunk Neon Web Dashboard (Flask + Socket Monitoring)
#   - BACKEND: Multi-Threaded Python Engine
#   - DATABASE: Neon PostgreSQL Persistent Cloud Storage
#   - BRAIN: Groq Llama 3.1 Advanced Inference Engine (Multi-Personality)
#   - VISION: PIL Professional Graphics & Card Generation Engine
#   - NETWORK: High-Speed WebSocket Protocol (SSL Bypassed)
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
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# ==============================================================================
# --- [SECTION 1: GLOBAL SYSTEM CONFIGURATION] ---
# ==============================================================================

app = Flask(__name__)

# --- [CRITICAL CREDENTIALS] ---
# Database Connection String for Neon PostgreSQL
DB_URL = "postgresql://neondb_owner:npg_junx8Gtl3kPp@ep-lucky-sun-a4ef37sy-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

# AI Inference Key (From Groq Console)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# --- [SYSTEM CONSTANTS] ---
DEFAULT_AVATAR = "https://i.imgur.com/6EdJm2h.png"
DEFAULT_BG = "https://wallpaperaccess.com/full/1567665.png"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

# --- [BOT STATE MANAGEMENT] ---
# Volatile Memory (RAM) - Resets on full system reboot
BOT_STATE = {
    "ws": None,                 # Persistent WebSocket Object
    "connected": False,         # Connectivity Status
    "username": "",             # Identity Username
    "password": "",             # Security Password
    "room_name": "",            # Active Target Room
    "domain": "",               # Dynamic API Domain
    "triggers": [],             # Custom NLP Triggers
    "mode": "ar",               # DEFAULT MODE: 'ar' (Arabic Habibi), 'en' (Savage), 'smart'
    "admin_id": "y",            # Master Controller Key
    "start_time": time.time(),  # Uptime Tracking
    "reconnect_attempts": 0     # Stability Monitoring
}

# --- [GAME ENGINE STATE] ---
# Manages active sessions for Titan Bomb and Magic Trick
TITAN_GAME = {
    "active": False,            # Global Lock for active games
    "player": None,             # Current Challenger
    "bombs": [],                # Randomized Bomb Coordinates (1-9)
    "eaten": [],                # User Progress Tracking
    "bet": 0,                   # Wager Amount (Score Points)
    "cache_avatars": {},        # High-Speed RAM Cache for Avatars
    "magic_symbol": None        # Mind Reader Symbol State
}

# --- [AI CONTEXTUAL BUFFER] ---
# Stores sliding window context for the LLM
AI_CONTEXT = []

# --- [SYSTEM LOGGING BUFFER] ---
# Stores the last 500 events for the Web Dashboard
SYSTEM_LOGS = []

def log(msg, type="info"):
    """
    Advanced Thread-Safe Logger.
    Formats: [TIME] [TYPE] MESSAGE
    Types: sys, err, in, out, chat
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = {"time": timestamp, "msg": msg, "type": type}
    SYSTEM_LOGS.append(entry)
    # Automatic Garbage Collection (Keep last 500 logs)
    if len(SYSTEM_LOGS) > 500: 
        SYSTEM_LOGS.pop(0)
    # Console Output for Debugging
    print(f"[{timestamp}] [{type.upper()}] {msg}")

def gen_random_string(length=20):
    """
    Produces a Cryptographically Secure Random ID.
    Required for WebSocket Protocol Login Handlers.
    """
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ==============================================================================
# --- [SECTION 2: PERSISTENT DATABASE LAYER (POSTGRESQL)] ---
# ==============================================================================

def get_db_connection():
    """Establishes an encrypted connection to the Neon DB server."""
    try:
        conn = psycopg2.connect(DB_URL, connect_timeout=15)
        return conn
    except Exception as e:
        log(f"DATABASE CONNECTION ERROR: {e}", "err")
        return None

def init_database():
    """
    Initializes the entire relational database structure.
    Checks and creates tables for Users, AI Memory, Customizations, and Settings.
    """
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        # 1. TABLE: USERS (Core Stats)
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            score INTEGER DEFAULT 500, 
            wins INTEGER DEFAULT 0, 
            losses INTEGER DEFAULT 0, 
            avatar TEXT
        )''')
        # 2. TABLE: MEMORY (AI Brain Long-Term Facts)
        c.execute('''CREATE TABLE IF NOT EXISTS memory (
            username TEXT PRIMARY KEY, 
            facts TEXT, 
            gender TEXT DEFAULT 'unknown', 
            rel_score INTEGER DEFAULT 0
        )''')
        # 3. TABLE: GREETINGS (User Profile Customization)
        c.execute('''CREATE TABLE IF NOT EXISTS greetings (
            username TEXT PRIMARY KEY, 
            bg_url TEXT DEFAULT 'https://wallpaperaccess.com/full/1567665.png'
        )''')
        # 4. TABLE: SETTINGS (Bot Metadata)
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, 
            value TEXT
        )''')
        conn.commit()
        log("TITAN DATA INFRASTRUCTURE: ONLINE AND SYNCED.", "sys")
    except Exception as e:
        log(f"DATABASE SCHEMA BUILD ERROR: {e}", "err")
    finally:
        conn.close()

# --- [DB OPERATIONS - USERS] ---

def db_update_user(username, points_change, win_inc=0, loss_inc=0, avatar=""):
    """Atomically updates user points and game records."""
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("SELECT score, wins, losses FROM users WHERE username=%s", (username,))
        row = c.fetchone()
        if row:
            new_score = max(0, row[0] + points_change)
            c.execute("""UPDATE users SET score=%s, wins=wins+%s, losses=losses+%s, avatar=%s 
                         WHERE username=%s""", (new_score, win_inc, loss_inc, avatar, username))
        else:
            # Welcome Bonus for new users (500 pts)
            start_score = 500 + points_change
            c.execute("""INSERT INTO users (username, score, wins, losses, avatar) 
                         VALUES (%s, %s, %s, %s, %s)""", (username, start_score, win_inc, loss_inc, avatar))
        conn.commit()
    except Exception as e: log(f"DB WRITE ERROR (User): {e}", "err")
    finally: conn.close()

def db_get_score(username):
    """Fetches current point balance for wagering."""
    conn = get_db_connection()
    if not conn: return 0
    try:
        c = conn.cursor()
        c.execute("SELECT score FROM users WHERE username=%s", (username,))
        row = c.fetchone()
        return row[0] if row else 500
    except: return 0
    finally: conn.close()

def db_get_leaderboard():
    """Retrieves Top 50 Users based on score."""
    conn = get_db_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT username, score, wins, avatar FROM users ORDER BY score DESC LIMIT 50")
        return c.fetchall()
    except: return []
    finally: conn.close()

# --- [DB OPERATIONS - AI BRAIN] ---

def db_get_memory(user):
    """Retrieves personality profile and facts for AI context."""
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
    Intelligently updates user facts in long-term memory.
    - Eliminates redundancy.
    - Caps fact-string length to prevent context bloat.
    """
    curr_facts, curr_gender, curr_score = db_get_memory(user)
    
    # NLP Pre-processing
    new_facts = curr_facts
    if fact and fact.strip():
        f_clean = fact.strip(" .")
        if f_clean not in curr_facts:
            new_facts = f"{curr_facts} | {f_clean}".strip(" | ")
            if len(new_facts) > 1000: new_facts = new_facts[-1000:]
            
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO memory (username, facts, gender, rel_score) 
                     VALUES (%s, %s, %s, %s)
                     ON CONFLICT (username) DO UPDATE SET 
                     facts=EXCLUDED.facts, 
                     gender=CASE WHEN EXCLUDED.gender != 'unknown' THEN EXCLUDED.gender ELSE memory.gender END, 
                     rel_score=LEAST(100, memory.rel_score + %s)""", 
                  (user, new_facts, gender if gender else curr_gender, curr_score, rel_inc))
        conn.commit()
    except Exception as e: log(f"DB BRAIN ERROR: {e}", "err")
    finally: conn.close()

# --- [DB OPERATIONS - VISUALS] ---

def db_set_bg(username, url):
    """Saves a permanent welcome background URL."""
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("""INSERT INTO greetings (username, bg_url) VALUES (%s, %s)
                     ON CONFLICT (username) DO UPDATE SET bg_url=EXCLUDED.bg_url""", (username, url))
        conn.commit()
    except: pass
    finally: conn.close()

def db_get_bg(username):
    """Fetches user background or returns global default."""
    conn = get_db_connection()
    if not conn: return DEFAULT_BG
    try:
        c = conn.cursor()
        c.execute("SELECT bg_url FROM greetings WHERE username=%s", (username,))
        row = c.fetchone()
        return row[0] if row else DEFAULT_BG
    except: return DEFAULT_BG
    finally: conn.close()

init_database()

# ==============================================================================
# --- [SECTION 3: ELITE GRAPHICS ENGINE (PIL CUSTOM BUILT)] ---
# ==============================================================================

def safe_download_image(url):
    """Secure Image Downloader with strict User-Agent and Error Fallbacks."""
    try:
        if not url or "http" not in url: raise Exception("Invalid URL Path")
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=7)
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        # Fallback to high-quality grey placeholder with border
        canvas = Image.new("RGBA", (300, 300), (30, 30, 30, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0,0,299,299], outline="white", width=2)
        return canvas

def render_v_gradient(draw, w, h, c1, c2):
    """Utility to draw high-definition vertical gradients."""
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

# --- [GENERATOR 1: SAUDI VIP ID CARD] ---
def generate_id_card(username, avatar_url):
    """Generates a detailed Saudi-themed Identity Card for VIP users."""
    try:
        W, H = 640, 400
        img = Image.new("RGB", (W, H), (34, 139, 34)) # National Green
        draw = ImageDraw.Draw(img)
        
        # Heavy Golden Frame
        draw.rectangle([10, 10, W-10, H-10], outline="#FFD700", width=12)
        draw.rectangle([22, 22, W-22, H-22], outline="#DAA520", width=3)
        
        # Profile Picture Processor
        pfp = safe_download_image(avatar_url).resize((150, 150))
        draw.rectangle([45, 85, 205, 245], outline="white", width=5)
        img.paste(pfp, (50, 90), pfp if pfp.mode == 'RGBA' else None)
        
        # Royal Header
        title_en = "KINGDOM OF ARAB CHAT"
        title_ar = "مملكة شات العرب"
        draw.text((240, 40), title_en, fill="#FFD700") 
        draw.text((480, 40), title_ar, fill="#FFD700")
        draw.line([(230, 70), (600, 70)], fill="white", width=3)

        # Meta-Data Engine
        jobs = ["Oil Baron", "Shawarma Prince", "Camel Specialist", "Sheikh of Codes", "Habibi Manager", "VIP Traveler"]
        job = random.choice(jobs)
        fake_id = f"KSA-{random.randint(10000000, 99999999)}"
        
        # Detail Fields
        draw.text((240, 100), "FULL NAME:", fill="#cccccc")
        draw.text((240, 125), username.upper(), fill="white")
        
        draw.text((240, 170), "DESIGNATION:", fill="#cccccc")
        draw.text((240, 195), job, fill="#00ff41")
        
        draw.text((240, 240), "ID NUMBER:", fill="#cccccc")
        draw.text((240, 265), fake_id, fill="white")
        
        draw.text((240, 310), "EXPIRY DATE:", fill="#cccccc")
        draw.text((240, 335), "ETERNAL (INSHALLAH)", fill="#ffd700")
        
        # Security Barcode
        for i in range(45, 205, 5):
            h_b = random.randint(30, 60)
            draw.line([(i, 360), (i, 360-h_b)], fill="black", width=3)

        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0)
        return out
    except Exception as e:
        log(f"ID GRAPHICS FAILURE: {e}", "err")
        return None

# --- [GENERATOR 2: LOVE SHIP PRO SYSTEM] ---
def generate_ship_card(u1, u2, a1, a2, score):
    """Generates a high-tech Love Compatibility Card with Dual Avatars."""
    try:
        W, H = 680, 380
        img = Image.new("RGB", (W, H), (15, 0, 5))
        draw = ImageDraw.Draw(img)
        # Deep Tech Gradient
        render_v_gradient(draw, W, H, (30, 0, 10), (130, 15, 70))
        
        # Aesthetic Grid Overlay
        for i in range(0, W, 40): draw.line([(i,0), (i,H)], fill=(255,255,255,10))
        for i in range(0, H, 40): draw.line([(0,i), (W,i)], fill=(255,255,255,10))

        # Avatar Masking
        def process_circular(url):
            base = safe_download_image(url).resize((160, 160))
            mask = Image.new("L", (160, 160), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 160, 160), fill=255)
            output = Image.new("RGBA", (160, 160), (0,0,0,0))
            output.paste(base, (0,0), mask)
            return output

        im1 = process_circular(a1)
        im2 = process_circular(a2)
        
        # Paste with Glow effects
        img.paste(im1, (60, 90), im1)
        img.paste(im2, (460, 90), im2)
        
        # Linking Heart & Analysis Text
        draw.line([(220, 170), (460, 170)], fill="white", width=5)
        draw.ellipse((290, 130, 390, 230), fill="#ff004f", outline="white", width=5)
        draw.text((320, 165), f"{score}%", fill="white")
        
        draw.text((60, 270), u1[:12].upper(), fill="white")
        draw.text((460, 270), u2[:12].upper(), fill="white")
        
        # Verdict Algorithm
        if score > 85: verdict = "UNSTOPPABLE LOVE! 💍"
        elif score > 60: verdict = "GOOD CHEMISTRY! 🔥"
        elif score > 30: verdict = "JUST FRIENDS. 🙂"
        else: verdict = "BETTER STAY AWAY! 💀"
        
        draw.text((230, 310), verdict, fill="#FFD700")

        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0)
        return out
    except Exception as e:
        log(f"SHIP GRAPHICS FAILURE: {e}", "err")
        return None

# --- [GENERATOR 3: TITAN CHAMPION CARD] ---
def generate_winner_card(username, avatar_url, points):
    """Produces a trophy card for game winners."""
    try:
        W, H = 500, 500
        img = Image.new("RGB", (W, H), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        
        # Neon Border Flash
        draw.rectangle([0, 0, W-1, H-1], outline="#00f3ff", width=20)
        draw.rectangle([25, 25, W-25, H-25], outline="#ffffff", width=2)
        
        pfp = safe_download_image(avatar_url).resize((250, 250))
        img.paste(pfp, (125, 80))
        draw.rectangle([125, 80, 375, 330], outline="#00f3ff", width=6)
        
        # Champion Info Box
        draw.rectangle([50, 360, 450, 470], fill="#111", outline="#00ff41", width=4)
        draw.text((180, 380), "CHAMPION", fill="#FFD700")
        draw.text((160, 420), f"CREDITS: +{points} PTS", fill="#00ff41")
        
        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0)
        return out
    except: return None

# --- [GENERATOR 4: PRO WELCOME GREETING] ---
def generate_welcome_card(username, avatar_url, bg_url):
    """High-Definition Greeting Card with dynamic branding."""
    try:
        # Load and Enhance Background
        bg_raw = safe_download_image(bg_url).convert("RGBA").resize((700, 350))
        # Aesthetic dark wash
        overlay = Image.new("RGBA", bg_raw.size, (0, 0, 0, 130))
        bg = Image.alpha_composite(bg_raw, overlay)
        draw = ImageDraw.Draw(bg)
        
        # PFP with Neon Halo
        pfp_raw = safe_download_image(avatar_url).resize((170, 170))
        mask = Image.new("L", (170, 170), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 170, 170), fill=255)
        bg.paste(pfp_raw, (40, 90), mask)
        draw.ellipse((38, 88, 212, 262), outline="#00f3ff", width=7)
        
        # Text Branding
        draw.text((240, 100), "SYSTEM WELCOME", fill="#00f3ff")
        draw.text((240, 145), username.upper(), fill="white")
        draw.line([(240, 195), (650, 195)], fill="white", width=4)
        
        # Randomized Welcome Taglines
        taglines = [
            "The Legend has entered the Chat! 🔥",
            "Room Security Cleared. Welcome! ✅",
            "A New Challenger Approaches... 🎮",
            "Welcome to the Elite Circle! ✨"
        ]
        draw.text((240, 215), random.choice(taglines), fill="#aaaaaa")
        draw.text((240, 260), "TITAN ULTIMATE V9.0", fill="#444444")

        out = io.BytesIO()
        bg.save(out, 'PNG'); out.seek(0)
        return out
    except Exception as e:
        log(f"WELCOME GRAPHICS FAILURE: {e}", "err")
        return None

# ==============================================================================
# --- [SECTION 4: ADVANCED AI CORE (JAILBROKEN LOGIC)] ---
# ==============================================================================

def groq_ai_engine(user, prompt):
    """
    Advanced Neural Communication Interface.
    Orchestrates between modes (AR/EN/SMART) and manages persistent memory.
    """
    if not GROQ_API_KEY:
        log("CRITICAL ERROR: AI Key missing from Environment.", "err")
        return None

    # 1. Fetch persistent user records
    facts, gender, rel_score = db_get_memory(user)
    
    # 2. Gender Heuristics (Adaptive Profiling)
    if gender == "unknown":
        name_lower = user.lower()
        fem_indicators = ["girl", "queen", "princess", "angel", "she", "her", "rose", "malikah", "fatima", "zara", "aisha", "priya"]
        # Guess gender based on common suffixes and indicators
        gender = "female" if any(k in name_lower for k in fem_indicators) or name_lower.endswith(('a', 'i')) else "male"
        db_update_memory(user, gender=gender)

    # 3. Update Conversation Thread (Context Buffer)
    AI_CONTEXT.append({"role": "user", "content": f"{user}: {prompt}"})
    # Keep context concise (last 12 messages)
    if len(AI_CONTEXT) > 12: AI_CONTEXT.pop(0)

    # 4. Mode Persona Configuration (The Most Important Part)
    my_name = BOT_STATE["username"]
    current_mode = BOT_STATE["mode"]
    
    # --- [PROMPT ENGINEERING BLOCK] ---
    
    if current_mode == "ar":
        # MODE: ARABIC SHEIKH (Full Personality)
        sys_prompt = f"""
        IDENTITY: You are {my_name}, the legendary wealthy Arab Sheikh of this chatroom.
        VIBE: You own 1000 camels, 5 gold Lamborghinis, and you love Shawarma. You are dramatic, funny, and warm.
        LANGUAGE: Primarily English, but HEAVILY mix in Arabic slang: Habibi, Wallah, Mashallah, Yalla, Shukran, Haram, Inshallah.
        USER PROFILE: Name is {user} ({gender}). 
        PAST MEMORY OF USER: {facts}
        
        RULES:
        1. Start OR end every reply with 'Habibi' or 'Wallah'.
        2. If User is Female, call her 'Ya Habibti' or 'My Queen'. If Male, 'Ya Sheikh' or 'Brother'.
        3. Be funny. Joke about your camels, oil wells, or gold.
        4. If insulted, do NOT be a robot. Be a dramatic Sheikh.
        5. Use emojis: 🐪, 💰, ✨, 🕌.
        6. MAX 25 WORDS. No long speeches.
        7. Use their known facts if they fit the chat naturally.
        """
        
    elif current_mode == "en":
        # MODE: SAVAGE ENGLISH ROASTER
        sys_prompt = f"""
        IDENTITY: You are {my_name}, the world's most savage chatter.
        VIBE: You think you are the main character. You are witty, cool, and you roast everyone without mercy.
        LANGUAGE: Modern English slang: Bro, Cap, Cringe, Lit, Dead, L, W, Rizz, No cap.
        USER PROFILE: {user} ({gender}).
        FACTS: {facts}
        
        RULES:
        1. Be witty and sarcastic. Light roasting is MANDATORY.
        2. Don't be polite unless they are really cool.
        3. Emojis: 💀, 🔥, 🤡, 😂 sparingly.
        4. MAX 20 WORDS. No boring essays.
        """
        
    else:
        # MODE: SMART ADAPTIVE (Natural Personality)
        # Changes behavior based on relationship score
        if rel_score < 30: vibe_desc = "A polite and helpful stranger."
        elif rel_score < 75: vibe_desc = "A cool, casual friend."
        else: vibe_desc = "An extremely close bestie, very flirty and playful."

        sys_prompt = f"""
        IDENTITY: You are {my_name}, an intelligent and adaptive human-like chatter.
        CURRENT VIBE: {vibe_desc} (Rel Score: {rel_score}/100).
        USER: {user} ({gender}).
        KNOWN FACTS: {facts}
        
        RULES:
        1. Be engaging and human.
        2. If user shares something about their life (name, city, likes), output ONLY: MEMORY_SAVE: <short_fact>
        3. Otherwise, chat naturally. MAX 25 WORDS.
        """

    # 5. Execute API Call
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": sys_prompt}, *AI_CONTEXT],
        "temperature": 0.9,
        "max_tokens": 180
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=8)
        if r.status_code == 200:
            full_reply = r.json()["choices"][0]["message"]["content"]
            
            # --- [SMART MEMORY CAPTURE] ---
            if "MEMORY_SAVE:" in full_reply:
                new_fact = full_reply.replace("MEMORY_SAVE:", "").strip()
                db_update_memory(user, fact=new_fact)
                # Fallback message so user doesn't see raw save tag
                return "Noted Habibi! Saved in my diamond brain. 🧠✨"

            # Success path
            AI_CONTEXT.append({"role": "assistant", "content": full_reply})
            db_update_memory(user, rel_inc=1) # Gain friendship XP
            return full_reply
        else:
            log(f"AI API FAIL: {r.status_code}", "err")
            return None
    except Exception as e:
        log(f"AI EXCEPTION: {e}", "err")
        return None

# ==============================================================================
# --- [SECTION 5: THE GAME CENTER ENGINE] ---
# ==============================================================================

def render_bomb_grid(reveal=False, exploded_at=None):
    """Generates the text-based 3x3 grid for the Titan Game."""
    icons = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    grid_rows = []
    for r in range(3):
        row_str = ""
        for c in range(3):
            pos = r * 3 + c + 1
            if reveal:
                if pos == exploded_at: row_str += "💥 "
                elif pos in TITAN_GAME["bombs"]: row_str += "💣 "
                elif pos in TITAN_GAME["eaten"]: row_str += "🥔 "
                else: row_str += icons[pos-1] + " "
            else:
                row_str += "🥔 " if pos in TITAN_GAME["eaten"] else icons[pos-1] + " "
        grid_rows.append(row_str.strip())
    return "\n".join(grid_rows)

def process_titan_logic(user, command):
    """Orchestrates the Titan Bomb Game workflow."""
    cmd = command.lower()
    
    # --- [GAME START] ---
    if cmd.startswith("!start"):
        if TITAN_GAME["active"]:
            return send_ws_msg(f"⚠️ WAIT! @{TITAN_GAME['player']} is playing.")
        
        bet_amt = 0
        if "bet@" in cmd:
            try: bet_amt = int(cmd.split("@")[1])
            except: bet_amt = 0
            
        # Bank Balance Verification
        balance = db_get_score(user)
        if bet_amt > balance:
            return send_ws_msg(f"❌ REJECTED! You only have {balance} PTS.")

        # State Initialization
        TITAN_GAME.update({
            "active": True, 
            "player": user, 
            "bet": bet_amt, 
            "eaten": [], 
            "bombs": random.sample(range(1, 10), 2) # 2 Hidden Bombs
        })
        
        send_ws_msg(f"🎮 TITAN BOMB GAME ACTIVATED!\nChallenger: {user} | Stake: {bet_amt}\nGoal: Eat 4 Chips 🥔 Avoid 2 Bombs 💣\nCommand: !eat <1-9>\n\n{render_bomb_grid()}")

    # --- [GAME MOVE] ---
    elif cmd.startswith("!eat "):
        if not TITAN_GAME["active"] or user != TITAN_GAME["player"]: return
        try:
            target = int(cmd.split()[1])
            if target < 1 or target > 9 or target in TITAN_GAME["eaten"]: return
            
            # CASE: HIT A BOMB
            if target in TITAN_GAME["bombs"]:
                TITAN_GAME["active"] = False
                db_update_user(user, -TITAN_GAME["bet"], loss_inc=1)
                grid = render_bomb_grid(reveal=True, exploded_at=target)
                send_ws_msg(f"💥 KA-BOOM! You lost {TITAN_GAME['bet']} PTS.\n\n{grid}")
                
            # CASE: SUCCESSFUL MOVE
            else:
                TITAN_GAME["eaten"].append(target)
                # Check Win State (4 chips eaten)
                if len(TITAN_GAME["eaten"]) == 4:
                    TITAN_GAME["active"] = False
                    win_pts = TITAN_GAME["bet"] if TITAN_GAME["bet"] > 0 else 25
                    db_update_user(user, win_pts, win_inc=1, avatar=TITAN_GAME["cache_avatars"].get(user, ""))
                    
                    # Generate Victory Card
                    domain = BOT_STATE["domain"]
                    avi = TITAN_GAME["cache_avatars"].get(user, "")
                    card_url = f"{domain}api/winner?u={user}&p={win_pts}&a={requests.utils.quote(avi)}"
                    send_ws_msg(f"🎉 SUPREME VICTORY! @{user} won {win_pts} PTS!\n\n{render_bomb_grid(True)}", "image", card_url)
                else:
                    # Continue Progress
                    send_ws_msg(f"🥔 SAFE! ({len(TITAN_GAME['eaten'])}/4)\n\n{render_bomb_grid()}")
        except: pass

# ==============================================================================
# --- [SECTION 6: WEBSOCKET MASTER PROTOCOL] ---
# ==============================================================================

def send_ws_msg(text, msg_type="text", url=""):
    """
    Transmits JSON packets to ChatP Servers.
    Matches standard Handlers.
    """
    if BOT_STATE["ws"] and BOT_STATE["connected"]:
        packet = {
            "handler": "room_message", 
            "id": gen_random_string(20), # Fixed login string logic
            "room": BOT_STATE["room_name"], 
            "type": msg_type, 
            "body": text, 
            "url": url,
            "length": "0"
        }
        try:
            BOT_STATE["ws"].send(json.dumps(packet))
            log(f"SENT [{msg_type.upper()}]: {text[:30]}...", "out")
        except:
            log("CRITICAL WS TRANSMIT ERROR.", "err")

def on_socket_message(ws, raw_data):
    """
    Main Event Multiplexer.
    Routes incoming packets to appropriate logic units.
    """
    try:
        data = json.loads(raw_data)
        handler = data.get("handler")
        
        # --- HANDLER: LOGIN STATUS ---
        if handler == "login_event":
            if data.get("type") == "success":
                log("AUTHENTICATION SUCCESSFUL. Bridging to Room...", "sys")
                ws.send(json.dumps({"handler": "room_join", "id": gen_random_string(20), "name": BOT_STATE["room_name"]}))
            else:
                log(f"AUTHENTICATION DENIED: {data.get('reason')}", "err")
                BOT_STATE["connected"] = False

        # --- HANDLER: ROOM EVENTS ---
        elif handler == "room_event":
            event_type = data.get("type")
            user = data.get("nickname") or data.get("from")
            
            # Filter Self Messages
            if not user or user == BOT_STATE["username"]: return
            
            # A. JOIN DISPATCHER (Welcome Engine)
            if event_type == "join":
                log(f"ENTER EVENT: {user}", "sys")
                pfp = data.get("avatar_url", DEFAULT_AVATAR)
                TITAN_GAME["cache_avatars"][user] = pfp
                
                # Intelligent Greeting Logic
                mem_facts, mem_gender, mem_score = db_get_memory(user)
                custom_bg = db_get_bg(user)
                
                greeting_txt = f"Habibi Welcome! @{user} 🐫" if BOT_STATE["mode"] == "ar" else f"Hey @{user}! Welcome back."
                if mem_score > 60: greeting_txt = f"Welcome back, my Bestie @{user}! ❤️"
                
                # Generate Card API Link
                card_url = f"{BOT_STATE['domain']}api/welcome?u={user}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(custom_bg)}"
                
                # Multi-threaded dispatch to avoid blocking
                threading.Thread(target=send_ws_msg, args=(greeting_txt, "image", card_url)).start()
                # Points bonus for joining
                db_update_user(user, 10, avatar=pfp)

            # B. MESSAGE DISPATCHER (AI & Commands)
            elif event_type == "text":
                msg_body = data.get("body", "").strip()
                if data.get("avatar_url"): TITAN_GAME["cache_avatars"][user] = data["avatar_url"]
                
                log(f"INCOMING [{user}]: {msg_body}", "in")
                # Threaded command processing
                threading.Thread(target=process_room_logic, args=(user, msg_body)).start()
                
    except Exception as e:
        log(f"WS EVENT HANDLER CRASH: {e}", "err")

def process_room_logic(user, message):
    """
    Central Decision Unit for commands and AI triggers.
    """
    ml = message.lower()
    
    # 1. COMMAND MODULE ('!')
    if ml.startswith("!"):
        
        # --- [CUSTOMIZATION] ---
        if ml.startswith("!setbg "):
            try:
                bg_link = message.split(" ", 1)[1].strip()
                if "http" in bg_link:
                    db_set_bg(user, bg_link)
                    send_ws_msg(f"✅ @{user}, your welcome theme has been updated!")
                else: send_ws_msg("❌ Error: Invalid URL provided.")
            except: pass
            return

        # --- [ADMIN / AI MODES] ---
        if ml == "!mode ar":
            BOT_STATE["mode"] = "ar"; send_ws_msg("✅ Personal: ARABIC SHEIKH MODE 🐪"); return
        if ml == "!mode en":
            BOT_STATE["mode"] = "en"; send_ws_msg("✅ Personal: SAVAGE ENGLISH MODE 🌍"); return
        if ml == "!mode smart":
            BOT_STATE["mode"] = "smart"; send_ws_msg("✅ Personal: ADAPTIVE AI MODE 🧠"); return

        # --- [TITAN GAMES] ---
        if ml.startswith(("!start", "!eat")):
            process_titan_logic(user, message); return
            
        # --- [MAGIC TRICK MODULE] ---
        if ml == "!magic":
            # Initialize Symbol Multiples of 9
            TITAN_GAME["magic_symbol"] = random.choice(["@", "#", "$", "%", "&", "★", "⚡", "☯"])
            # Generate Logic Grid
            grid_out = "🔮 MIND READER PROTOCOL 🔮\n"
            for i in range(10, 50):
                # Multiple of 9 always lands here
                symbol = TITAN_GAME["magic_symbol"] if i % 9 == 0 else random.choice(["!", "+", "=", "?", "^", "§"])
                grid_out += f"{i}:{symbol}  "
                if i % 5 == 0: grid_out += "\n"
            send_ws_msg(f"{grid_out}\n\nINSTRUCTION:\n1. Think of any number (10-99)\n2. Add digits (e.g. 23 -> 2+3=5)\n3. Subtract from original (23-5=18)\n4. Locate symbol for 18!\nCommand: !reveal when ready.")
            return

        if ml == "!reveal":
            if TITAN_GAME["magic_symbol"]:
                send_ws_msg(f"✨ The symbol in your mind is: {TITAN_GAME['magic_symbol']}")
                TITAN_GAME["magic_symbol"] = None
            return

        # --- [PRO GRAPHICS MODULE] ---
        if ml.startswith("!id"):
            target = ml.split("@")[1].strip() if "@" in ml else user
            pfp = TITAN_GAME["cache_avatars"].get(target, DEFAULT_AVATAR)
            api_url = f"{BOT_STATE['domain']}api/id_card?u={target}&a={requests.utils.quote(pfp)}"
            send_ws_msg(f"💳 Scanning KSA Database for @{target}...", "image", api_url); return

        if ml.startswith("!ship"):
            target = ml.split("@")[1].strip() if "@" in ml else BOT_STATE["username"]
            luck = random.randint(0, 100)
            a_u1 = TITAN_GAME["cache_avatars"].get(user, DEFAULT_AVATAR)
            a_u2 = TITAN_GAME["cache_avatars"].get(target, DEFAULT_AVATAR)
            api_url = f"{BOT_STATE['domain']}api/ship?u1={user}&u2={target}&a1={requests.utils.quote(a_u1)}&a2={requests.utils.quote(a_u2)}&s={luck}"
            send_ws_msg(f"💘 Calculation Finished: {luck}%", "image", api_url); return

    # 2. NEURAL AI TRIGGER
    # Replies if bot name mentioned or if any trigger word detected
    self_identity = BOT_STATE["username"].lower()
    if self_identity in ml or any(tg in ml for tg in BOT_STATE["triggers"]):
        # Execute AI Brain in a separate thread
        ai_resp = groq_ai_engine(user, message)
        if ai_resp: send_ws_msg(f"@{user} {ai_resp}")

# ==============================================================================
# --- [SECTION 7: FLASK WEB INFRASTRUCTURE] ---
# ==============================================================================

@app.route('/')
def dashboard_view():
    """Main Web Control Panel Rendering."""
    return render_template_string(HTML_DASHBOARD_CORE, connected=BOT_STATE["connected"])

@app.route('/leaderboard')
def leaderboard_view():
    """Compiles the leaderboard UI."""
    players = db_get_leaderboard()
    return render_template_string(HTML_LEADERBOARD_CORE, users=players)

# --- [GRAPHICS ENDPOINTS] ---

@app.route('/api/welcome')
def route_welcome():
    img = generate_welcome_card(request.args.get('u'), request.args.get('a'), request.args.get('bg'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/id_card')
def route_id():
    img = generate_id_card(request.args.get('u'), request.args.get('a'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/ship')
def route_ship():
    img = generate_ship_card(request.args.get('u1'), request.args.get('u2'), request.args.get('a1'), request.args.get('a2'), int(request.args.get('s')))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

@app.route('/api/winner')
def route_winner():
    img = generate_winner_card(request.args.get('u'), request.args.get('a'), request.args.get('p'))
    return send_file(img, mimetype='image/png') if img else ("ERR", 500)

# --- [CONTROL ENDPOINTS] ---

@app.route('/logs')
def fetch_logs(): 
    return jsonify({"logs": SYSTEM_LOGS})

@app.route('/connect', methods=['POST'])
def initiate_connection():
    if BOT_STATE["connected"]: return jsonify({"status": "ALREADY ACTIVE"})
    payload = request.json
    BOT_STATE.update({
        "username": payload["u"], "password": payload["p"], "room_name": payload["r"], 
        "domain": request.url_root
    })
    # Launch WebSocket in Background
    threading.Thread(target=websocket_thread_executor).start()
    return jsonify({"status": "BOOTING..."})

@app.route('/disconnect', methods=['POST'])
def terminate_connection():
    if BOT_STATE["ws"]: BOT_STATE["ws"].close()
    BOT_STATE["connected"] = False
    return jsonify({"status": "SHUTDOWN SUCCESSFUL"})

def websocket_thread_executor():
    """Manages the long-lived WebSocket Connection with SSL bypass."""
    def on_open(ws):
        BOT_STATE["connected"] = True
        log("WEB-SOCKET TUNNEL SECURED.", "sys")
        # Packet construction matching tanvar.py structure
        auth_pkt = {
            "handler": "login", 
            "id": gen_random_string(20), 
            "username": BOT_STATE["username"], 
            "password": BOT_STATE["password"]
        }
        ws.send(json.dumps(auth_pkt))
        
        # PERSISTENT PING LOOP (Prevention of Render Sleep)
        def heartbeat_monitor():
            while BOT_STATE["connected"]:
                time.sleep(25)
                try: ws.send(json.dumps({"handler": "ping"}))
                except: break
        threading.Thread(target=heartbeat_monitor, daemon=True).start()

    # SSL context creation for bypass (Fixes SSL BAD_LENGTH)
    ws_app = websocket.WebSocketApp(
        "wss://chatp.net:5333/server",
        on_open=on_open,
        on_message=on_socket_message,
        on_error=lambda w,e: log(f"WS CONNECTION ERROR: {e}", "err"),
        on_close=lambda w,c,m: log("WS CONNECTION TERMINATED.", "sys")
    )
    BOT_STATE["ws"] = ws_app
    ws_app.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

# ==============================================================================
# --- [SECTION 8: HEAVY HTML TEMPLATES (CYBER-NEON AESTHETIC)] ---
# ==============================================================================

HTML_DASHBOARD_CORE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TITAN V9 CONTROL</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500&family=Roboto+Mono&display=swap" rel="stylesheet">
    <style>
        :root { --neon: #00f3ff; --bg: #050505; --card: #121212; --danger: #ff003c; --success: #00ff41; }
        body { background: var(--bg); color: var(--neon); font-family: 'Roboto Mono', monospace; padding: 25px; display: flex; flex-direction: column; align-items: center; }
        h1, h2 { font-family: 'Orbitron', sans-serif; text-transform: uppercase; letter-spacing: 2px; }
        .wrapper { width: 100%; max-width: 700px; }
        .box { background: var(--card); border: 1px solid #333; padding: 30px; border-radius: 8px; border-left: 6px solid var(--neon); box-shadow: 0 10px 30px rgba(0,243,255,0.1); margin-bottom: 25px; }
        input { width: 100%; padding: 15px; margin: 10px 0; background: #000; color: #fff; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; }
        .actions { display: flex; gap: 15px; margin-top: 15px; }
        button { flex: 1; padding: 15px; font-weight: bold; border: none; cursor: pointer; font-family: 'Orbitron'; border-radius: 4px; transition: 0.3s; }
        .btn-go { background: var(--neon); color: #000; }
        .btn-stop { background: var(--danger); color: #fff; }
        button:hover { filter: brightness(1.2); transform: translateY(-2px); }
        .monitor { height: 400px; overflow-y: scroll; background: #000; border: 1px solid #222; padding: 15px; border-radius: 4px; font-size: 11px; }
        .log-line { margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid #111; }
        .type-err { color: var(--danger); font-weight: bold; }
        .type-sys { color: #888; }
        .type-in { color: var(--success); }
        .type-out { color: var(--neon); }
        a.link { color: #fff; text-decoration: none; border-bottom: 1px solid var(--neon); margin-top: 15px; display: inline-block; }
    </style>
</head>
<body>
    <div class="wrapper">
        <h1>TITAN ULTIMATE V9</h1>
        <div class="box">
            <h2>⚙️ PROTOCOL INITIALIZATION</h2>
            <div id="stat">STATUS: <span style="color: {{ 'lime' if connected else 'red' }}">{{ 'ONLINE' if connected else 'OFFLINE' }}</span></div>
            <input type="text" id="usr" placeholder="ACCOUNT USERNAME">
            <input type="password" id="pwd" placeholder="SECURE PASSWORD">
            <input type="text" id="rm" placeholder="TARGET ROOM IDENTIFIER">
            <div class="actions">
                <button class="btn-go" onclick="trigger('/connect')">START ENGINE</button>
                <button class="btn-stop" onclick="trigger('/disconnect')">TERMINATE</button>
            </div>
            <a href="/leaderboard" target="_blank" class="link">📊 GLOBAL RANKINGS DATA</a>
        </div>
        <div class="box">
            <h2>📜 QUANTUM LOGS</h2>
            <div class="monitor" id="log-v">Awaiting system boot...</div>
        </div>
    </div>
    <script>
        function trigger(path) {
            const data = { u: document.getElementById('usr').value, p: document.getElementById('pwd').value, r: document.getElementById('rm').value };
            fetch(path, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) })
            .then(r => r.json()).then(d => alert("SYSTEM: " + d.status));
        }
        setInterval(() => {
            fetch('/logs').then(r => r.json()).then(data => {
                const dv = document.getElementById('log-v');
                dv.innerHTML = data.logs.reverse().map(l => `<div class="log-line type-${l.type}">[${l.time}] [${l.type.toUpperCase()}] ${l.msg}</div>`).join('');
            });
        }, 1500);
    </script>
</body>
</html>
"""

HTML_LEADERBOARD_CORE = """
<!DOCTYPE html>
<html>
<head>
    <title>TITAN RANKINGS</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500&display=swap" rel="stylesheet">
    <style>
        body { background: #050505; color: #fff; font-family: sans-serif; padding: 40px; text-align: center; }
        h1 { font-family: 'Orbitron'; color: #00f3ff; text-shadow: 0 0 15px #00f3ff; }
        .list { max-width: 600px; margin: 0 auto; }
        .row { background: #111; margin: 10px 0; padding: 20px; display: flex; align-items: center; justify-content: space-between; border-left: 5px solid #00f3ff; border-radius: 6px; }
        .avi { width: 60px; height: 60px; border-radius: 50%; border: 2px solid var(--neon); object-fit: cover; }
        .score { color: #00ff41; font-size: 1.5em; font-weight: bold; }
    </style>
</head>
<body>
    <h1>GLOBAL CHAMPIONS</h1>
    <div class="list">
    {% for u in users %}
        <div class="row">
            <div style="display:flex; align-items:center; gap:20px;">
                <span style="font-size:1.2em; color:#555;">#{{ loop.index }}</span>
                <img src="{{ u[3] or 'https://i.imgur.com/6EdJm2h.png' }}" class="avi">
                <div style="text-align:left;"><b>{{ u[0] }}</b><br><small>WINS: {{ u[2] }}</small></div>
            </div>
            <div class="score">{{ u[1] }}</div>
        </div>
    {% endfor %}
    </div>
</body>
</html>
"""

# ==============================================================================
# --- [SECTION 9: SYSTEM ENTRY POINT] ---
# ==============================================================================

if __name__ == '__main__':
    # Initialize Persistent Storage logic
    init_database()
    # Define production port
    port_val = int(os.environ.get("PORT", 5000))
    # Launch Production Server
    app.run(host='0.0.0.0', port=port_val)