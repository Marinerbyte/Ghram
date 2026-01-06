# ==============================================================================
# TITAN ULTIMATE GIRL BOT - VERSION 13.0 (ARABIC SUPREME EDITION)
# ==============================================================================
# FEATURES INCLUDED:
#   1. Advanced Multi-Greet Storage System (!sg, !dg, !mg, !gf)
#   2. Titan Bomb Betting Game & Magic Mind Reader
#   3. Multi-Mode AI (Strict Arabic Engine & Sassy English)
#   4. Smart Image Handler (Auto-fixes ImgBB links)
#   5. Arabic Text Reshaper (Fixes inverted Arabic on images)
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
import arabic_reshaper
from bidi.algorithm import get_display
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# ==============================================================================
# --- [SECTION 1: GLOBAL CONFIGURATION] ---
# ==============================================================================

app = Flask(__name__)

# --- DATABASE & API KEYS ---
# Aapka Neon DB URL
DB_URL = "postgresql://neondb_owner:npg_junx8Gtl3kPp@ep-lucky-sun-a4ef37sy-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# --- ASSETS & CONSTANTS ---
DEFAULT_AVATAR = "https://i.imgur.com/6EdJm2h.png"
DEFAULT_BG = "https://wallpaperaccess.com/full/1567665.png"
# Ye User-Agent ImgBB aur secure sites ko access karne me madad karega
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# --- BOT STATE ---
BOT_STATE = {
    "ws": None, "connected": False, "username": "", "password": "", 
    "room_name": "", "domain": "", "triggers": [], 
    "mode": "ar", # Default Mode is now Arabic
    "admin_id": "y", "gender": "female", "reconnect_attempts": 0
}

# --- GAME STATE ---
TITAN_GAME = {
    "active": False, "player": None, "bombs": [], "eaten": [], 
    "bet": 0, "cache_avatars": {}, "magic_symbol": None
}

AI_CONTEXT = []
SYSTEM_LOGS = []

def log(msg, type="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = {"time": timestamp, "msg": msg, "type": type}
    SYSTEM_LOGS.append(entry)
    if len(SYSTEM_LOGS) > 500: SYSTEM_LOGS.pop(0)
    print(f"[{timestamp}] [{type.upper()}] {msg}")

def gen_random_string(length=20):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# ==============================================================================
# --- [SECTION 2: DATABASE LOGIC] ---
# ==============================================================================

def get_db_connection():
    try:
        return psycopg2.connect(DB_URL, connect_timeout=15)
    except Exception as e:
        log(f"DB Error: {e}", "err"); return None

def init_database():
    conn = get_db_connection()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, score INTEGER DEFAULT 500, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, avatar TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_greets (id SERIAL PRIMARY KEY, username TEXT, url TEXT, message TEXT, key_tag TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS memory (username TEXT PRIMARY KEY, facts TEXT, gender TEXT DEFAULT 'unknown', rel_score INTEGER DEFAULT 0)''')
        conn.commit()
    except Exception as e: log(f"DB Init Failed: {e}", "err")
    finally: conn.close()

def db_save_greet(username, url, message):
    conn = get_db_connection()
    if not conn: return "Err"
    try:
        c = conn.cursor()
        c.execute("SELECT count(*) FROM user_greets WHERE username=%s", (username,))
        tag = f"greet{c.fetchone()[0] + 1}"
        c.execute("INSERT INTO user_greets (username, url, message, key_tag) VALUES (%s, %s, %s, %s)", (username, url, message, tag))
        conn.commit(); return tag
    finally: conn.close()

def db_delete_greet(username, tag):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM user_greets WHERE username=%s AND key_tag=%s", (username, tag.replace("@","").strip().lower()))
        conn.commit(); return c.rowcount > 0
    except: return False
    finally: conn.close()

def db_get_random_greet(username):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT url, message FROM user_greets WHERE username=%s ORDER BY RANDOM() LIMIT 1", (username,))
        return c.fetchone()
    except: return None
    finally: conn.close()

def db_update_user_stats(username, pts, win=0, loss=0, avatar=""):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT score FROM users WHERE username=%s", (username,))
        row = c.fetchone()
        if row: c.execute("UPDATE users SET score=%s, wins=wins+%s, losses=losses+%s, avatar=%s WHERE username=%s", (max(0, row[0]+pts), win, loss, avatar, username))
        else: c.execute("INSERT INTO users (username, score, wins, losses, avatar) VALUES (%s, %s, %s, %s, %s)", (username, 500+pts, win, loss, avatar))
        conn.commit()
    except: pass
    finally: conn.close()

def db_get_score(username):
    conn = get_db_connection()
    try:
        c = conn.cursor(); c.execute("SELECT score FROM users WHERE username=%s", (username,)); row=c.fetchone()
        return row[0] if row else 0
    except: return 0
    finally: conn.close()

def db_get_memory(user):
    conn = get_db_connection()
    try:
        c = conn.cursor(); c.execute("SELECT facts, gender, rel_score FROM memory WHERE username=%s", (user,))
        return c.fetchone() or ("", "unknown", 0)
    except: return ("", "unknown", 0)
    finally: conn.close()

def db_update_memory(user, fact=None, gender=None, rel_inc=0):
    curr_facts, curr_gender, _ = db_get_memory(user)
    new_facts = curr_facts
    if fact: new_facts = f"{curr_facts} | {fact.strip(' .')}".strip(" | ")[-1000:]
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO memory (username, facts, gender, rel_score) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO UPDATE SET facts=EXCLUDED.facts, gender=CASE WHEN EXCLUDED.gender != 'unknown' THEN EXCLUDED.gender ELSE memory.gender END, rel_score=LEAST(100, memory.rel_score + %s)", (user, new_facts, gender if gender else curr_gender, rel_inc, rel_inc))
        conn.commit()
    except: pass
    finally: conn.close()

def db_get_leaderboard():
    conn = get_db_connection()
    try:
        c = conn.cursor(); c.execute("SELECT username, score, wins, avatar FROM users ORDER BY score DESC LIMIT 10")
        return c.fetchall()
    except: return []
    finally: conn.close()

init_database()

# ==============================================================================
# --- [SECTION 3: SMART IMAGE & ARABIC ENGINE] ---
# ==============================================================================

def get_arabic_font(size):
    """Downloads Noto Sans Arabic automatically on Render."""
    font_path = "NotoSansArabic-Bold.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Bold.ttf"
        try:
            r = requests.get(url)
            with open(font_path, 'wb') as f: f.write(r.content)
        except: return ImageFont.load_default()
    return ImageFont.truetype(font_path, size)

def reshape_text(text):
    """Corrects Arabic text direction and connection."""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except: return text

def resolve_direct_link(url):
    """
    SMART LINK FIXER: Converts ImgBB/Viewer links to Direct Image Links.
    """
    if not url: return DEFAULT_BG
    if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')): return url
    
    try:
        headers = {'User-Agent': USER_AGENT}
        r = requests.get(url, headers=headers, timeout=5)
        # Use BeautifulSoup to find the real image in HTML
        if "text/html" in r.headers.get("Content-Type", ""):
            soup = BeautifulSoup(r.text, 'html.parser')
            # Method 1: OpenGraph
            og = soup.find("meta", property="og:image")
            if og and og.get("content"): return og["content"]
            # Method 2: Link Rel
            lk = soup.find("link", rel="image_src")
            if lk and lk.get("href"): return lk["href"]
            # Method 3: ImgBB specific structure
            img_tag = soup.find("img", {"id": "image-viewer"}) # Common in some hosts
            if img_tag and img_tag.get("src"): return img_tag["src"]
    except Exception as e:
        log(f"Link Resolve Fail: {e}", "err")
    return url

def safe_download_image(url):
    try:
        final_url = resolve_direct_link(url) # Resolve before downloading
        resp = requests.get(final_url, headers={'User-Agent': USER_AGENT}, timeout=8)
        return Image.open(io.BytesIO(resp.content)).convert("RGBA")
    except:
        # High quality fallback
        img = Image.new("RGBA", (400, 400), (20, 20, 20, 255))
        ImageDraw.Draw(img).text((100,200), "IMG ERROR", fill="white")
        return img

# --- GENERATORS ---

def generate_greet_card(username, avatar_url, bg_url, custom_msg=""):
    try:
        bg_raw = safe_download_image(bg_url).convert("RGBA").resize((750, 400))
        overlay = Image.new("RGBA", bg_raw.size, (0, 0, 0, 140))
        bg = Image.alpha_composite(bg_raw, overlay)
        draw = ImageDraw.Draw(bg)
        
        pfp_raw = safe_download_image(avatar_url).resize((180, 180))
        mask = Image.new("L", (180, 180), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
        bg.paste(pfp_raw, (50, 110), mask)
        draw.ellipse((48, 108, 232, 292), outline="#ff00ff", width=8)
        
        # Fonts
        f_title = get_arabic_font(30)
        f_name = get_arabic_font(45)
        f_msg = get_arabic_font(25)
        f_sub = get_arabic_font(15)

        # Dynamic Header based on Mode
        header_txt = "Ahlan wa Sahlan ✨" if BOT_STATE["mode"] == "ar" else "GREETINGS ✨"
        draw.text((260, 110), reshape_text(header_txt), font=f_title, fill="#ff00ff")
        
        draw.text((260, 160), reshape_text(username.upper()), font=f_name, fill="#ffffff")
        draw.line([(260, 215), (700, 215)], fill="#ffffff", width=4)
        
        msg_to_show = custom_msg if custom_msg else ("Nawwart ya Ghamar! 🌙" if BOT_STATE["mode"] == "ar" else "Welcome to the party! 🍭")
        draw.text((260, 235), reshape_text(msg_to_show[:60]), font=f_msg, fill="#cccccc")
        draw.text((260, 285), "TITAN V13 - ARABIC ENGINE", font=f_sub, fill="#444444")

        out = io.BytesIO()
        bg.save(out, 'PNG'); out.seek(0)
        return out
    except Exception as e:
        log(f"Greet Gen Error: {e}", "err"); return None

def generate_id_card(username, avatar_url):
    try:
        W, H = 640, 400
        img = Image.new("RGB", (W, H), (255, 105, 180))
        draw = ImageDraw.Draw(img)
        draw.rectangle([12, 12, W-12, H-12], outline="#C0C0C0", width=12)
        draw.rectangle([25, 25, W-25, H-25], outline="#ffffff", width=2)
        
        pfp = safe_download_image(avatar_url).resize((160, 160))
        draw.rectangle([45, 85, 215, 255], outline="white", width=5)
        img.paste(pfp, (50, 90))
        
        f_head = get_arabic_font(28)
        f_main = get_arabic_font(20)
        
        draw.text((245, 45), "ELITE ID CARD", font=f_head, fill="#ffffff")
        draw.text((245, 110), "NAME:", font=f_main, fill="#f0f0f0")
        draw.text((245, 135), reshape_text(username.upper()), font=f_head, fill="#ffffff")
        
        titles = ["Malikah 👑", "Habibti 🌸", "Chat Queen 💅", "VIP Star ✨"]
        draw.text((245, 180), "TITLE:", font=f_main, fill="#f0f0f0")
        draw.text((245, 205), reshape_text(random.choice(titles)), font=f_head, fill="#ffff00")
        
        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0); return out
    except: return None

def generate_winner_card(username, avatar_url, points):
    try:
        W, H = 500, 500
        img = Image.new("RGB", (W, H), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, W-1, H-1], outline="#00f3ff", width=20)
        pfp = safe_download_image(avatar_url).resize((250, 250))
        img.paste(pfp, (125, 80))
        draw.rectangle([125, 80, 375, 330], outline="#00f3ff", width=6)
        
        f_b = get_arabic_font(30)
        draw.text((180, 380), "CHAMPION", font=f_b, fill="#ffff00")
        draw.text((150, 420), f"WON: +{points} PTS", font=f_b, fill="#00ff41")
        
        out = io.BytesIO()
        img.save(out, 'PNG'); out.seek(0); return out
    except: return None

# ==============================================================================
# --- [SECTION 4: GAME & AI ENGINE] ---
# ==============================================================================

def groq_ai_engine(user, prompt):
    if not GROQ_API_KEY: return None
    mem_facts, mem_gender, _ = db_get_memory(user)
    my_name = BOT_STATE["username"]
    
    if BOT_STATE["mode"] == "ar":
        sys_prompt = f"""
        IDENTITY: You are {my_name}, a smart and charming Arab girl.
        LANGUAGE: STRICTLY ARABIC SCRIPT. 
        VIBE: Use 'Habibi', 'Ya Amar', 'Wallah'. Be cute and funny.
        USER: {user} ({mem_gender}). FACTS: {mem_facts}.
        CONSTRAINT: Keep it under 25 words. Reply in Arabic text only.
        """
    else:
        sys_prompt = f"You are {my_name}, a sassy girl bot. Be witty. User: {user}."

    AI_CONTEXT.append({"role": "user", "content": prompt})
    if len(AI_CONTEXT) > 12: AI_CONTEXT.pop(0)

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": sys_prompt}, *AI_CONTEXT], "temperature": 0.8}, timeout=10
        )
        if r.status_code == 200:
            ans = r.json()["choices"][0]["message"]["content"]
            AI_CONTEXT.append({"role": "assistant", "content": ans})
            if "MEMORY:" in ans: db_update_memory(user, fact=ans.split("MEMORY:")[1])
            return ans
    except Exception as e: log(f"AI Fail: {e}", "err")
    return None

def render_titan_grid(reveal=False, exploded_at=None):
    icons = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
    rows = []
    for r in range(3):
        line = ""
        for c in range(3):
            pos = r * 3 + c + 1
            if reveal:
                if pos == exploded_at: line += "💥 "
                elif pos in TITAN_GAME["bombs"]: line += "💣 "
                elif pos in TITAN_GAME["eaten"]: line += "🥔 "
                else: line += icons[pos-1] + " "
            else:
                line += "🥔 " if pos in TITAN_GAME["eaten"] else icons[pos-1] + " "
        rows.append(line.strip())
    return "\n".join(rows)

def process_titan_game(user, cmd):
    if cmd.startswith("!start"):
        if TITAN_GAME["active"]: return send_ws_msg(f"Wait! @{TITAN_GAME['player']} is playing.")
        bet = int(cmd.split("@")[1]) if "bet@" in cmd else 0
        bal = db_get_score(user)
        if bet > bal: return send_ws_msg(f"❌ You only have {bal} pts.")
        
        TITAN_GAME.update({"active": True, "player": user, "bet": bet, "eaten": [], "bombs": random.sample(range(1, 10), 2)})
        send_ws_msg(f"🎮 TITAN BOMB\nPlayer: @{user} | Bet: {bet}\nCmd: !eat <1-9>\n\n{render_titan_grid()}")

    elif cmd.startswith("!eat "):
        if not TITAN_GAME["active"] or user != TITAN_GAME["player"]: return
        try:
            ch = int(cmd.split()[1])
            if ch in TITAN_GAME["bombs"]:
                TITAN_GAME["active"] = False
                db_update_user_stats(user, -TITAN_GAME["bet"], loss=1)
                send_ws_msg(f"💥 BOOM! Lost {TITAN_GAME['bet']} pts.\n\n{render_titan_grid(True, ch)}")
            else:
                TITAN_GAME["eaten"].append(ch)
                if len(TITAN_GAME["eaten"]) == 4:
                    TITAN_GAME["active"] = False; prize = TITAN_GAME["bet"] if TITAN_GAME["bet"] > 0 else 25
                    avi = TITAN_GAME["cache_avatars"].get(user, DEFAULT_AVATAR)
                    db_update_user_stats(user, prize, win=1, avatar=avi)
                    url = f"{BOT_STATE['domain']}api/winner?u={user}&p={prize}&a={requests.utils.quote(avi)}"
                    send_ws_msg(f"🎉 WON {prize} PTS!\n\n{render_titan_grid(True)}", "image", url)
                else:
                    send_ws_msg(f"Safe! ({len(TITAN_GAME['eaten'])}/4)\n\n{render_titan_grid()}")
        except: pass

# ==============================================================================
# --- [SECTION 5: WEBSOCKET & COMMANDS] ---
# ==============================================================================

def send_ws_msg(text, msg_type="text", url=""):
    if BOT_STATE["ws"] and BOT_STATE["connected"]:
        packet = {"handler": "room_message", "id": gen_random_string(20), "room": BOT_STATE["room_name"], "type": msg_type, "body": text, "url": url, "length": "0"}
        try: BOT_STATE["ws"].send(json.dumps(packet))
        except: pass

def on_socket_message(ws, raw):
    try:
        data = json.loads(raw); handler = data.get("handler")
        if handler == "login_event":
            if data.get("type") == "success":
                log("LOGIN SUCCESS", "sys"); ws.send(json.dumps({"handler": "room_join", "id": gen_random_string(20), "name": BOT_STATE["room_name"]}))
            else: log("LOGIN FAIL", "err"); BOT_STATE["connected"] = False

        elif handler == "room_event":
            etype = data.get("type"); user = data.get("nickname") or data.get("from")
            if not user or user == BOT_STATE["username"]: return
            
            if etype == "join":
                pfp = data.get("avatar_url", DEFAULT_AVATAR)
                TITAN_GAME["cache_avatars"][user] = pfp
                
                # Check stored greets
                saved = db_get_random_greet(user)
                if saved:
                    url_bg, msg = saved
                    # SMART LINK FIX before API
                    fixed_bg = resolve_direct_link(url_bg)
                    link = f"{BOT_STATE['domain']}api/greet_instant?u={user}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(fixed_bg)}&m={requests.utils.quote(msg)}"
                    send_ws_msg(msg, "image", link)
                else:
                    msg = "Ahlan wa Sahlan! ✨" if BOT_STATE["mode"] == "ar" else "Welcome! 🌸"
                    link = f"{BOT_STATE['domain']}api/greet_instant?u={user}&a={requests.utils.quote(pfp)}&bg={requests.utils.quote(DEFAULT_BG)}&m={requests.utils.quote(msg)}"
                    threading.Thread(target=send_ws_msg, args=(msg, "image", link)).start()
                db_update_user_stats(user, 10, avatar=pfp)

            elif etype == "text":
                msg = data.get("body", "").strip()
                if data.get("avatar_url"): TITAN_GAME["cache_avatars"][user] = data["avatar_url"]
                threading.Thread(target=process_msg, args=(user, msg)).start()
    except Exception as e: log(f"WS Err: {e}", "err")

def process_msg(user, msg):
    ml = msg.lower()
    
    if ml.startswith("!sg "): # Save Greet
        try:
            parts = msg.split(" ", 3)
            target = parts[1].replace("@", "").strip()
            raw_url = parts[2].strip()
            # Resolve link here
            fixed_url = resolve_direct_link(raw_url)
            txt = parts[3].strip() if len(parts) > 3 else "Welcome"
            tag = db_save_greet(target, fixed_url, txt)
            send_ws_msg(f"✅ Greet saved! Tag: {tag}")
        except: send_ws_msg("❌ !sg @user url message")
        return

    if ml.startswith("!dg "): # Delete Greet
        try: 
            if db_delete_greet(ml.split()[1], ml.split()[2]): send_ws_msg("✅ Deleted")
            else: send_ws_msg("❌ Not found")
        except: pass; return
    
    if ml.startswith("!id"):
        target = ml.split("@")[1].strip() if "@" in ml else user
        pfp = TITAN_GAME["cache_avatars"].get(target, DEFAULT_AVATAR)
        url = f"{BOT_STATE['domain']}api/id_card?u={target}&a={requests.utils.quote(pfp)}"
        send_ws_msg(f"Scanning {target}...", "image", url); return

    if ml.startswith(("!start", "!eat")): process_titan_game(user, msg); return
    
    if ml == "!magic":
        TITAN_GAME["magic_symbol"] = random.choice(["★", "⚡", "☯", "♥", "♦"])
        s = "🔮 MIND READER\n"
        for i in range(10, 30): s += f"{i}:{TITAN_GAME['magic_symbol'] if i%9==0 else '?'} "
        send_ws_msg(f"{s}\n\nPick num 10-29. Add digits. Subtract from original.\n!reveal"); return

    if ml == "!reveal":
        if TITAN_GAME["magic_symbol"]: send_ws_msg(f"✨ Symbol: {TITAN_GAME['magic_symbol']}"); TITAN_GAME["magic_symbol"]=None; return

    if ml == "!mode ar": BOT_STATE["mode"]="ar"; send_ws_msg("✅ Arabic Mode (Ya Amar)"); return
    if ml == "!mode en": BOT_STATE["mode"]="en"; send_ws_msg("✅ English Mode"); return

    # AI Trigger
    if BOT_STATE["username"].lower() in ml or any(t in ml for t in BOT_STATE["triggers"]):
        ans = groq_ai_engine(user, msg)
        if ans: send_ws_msg(f"@{user} {ans}")

# ==============================================================================
# --- [SECTION 6: WEB SERVER] ---
# ==============================================================================

@app.route('/')
def home(): return render_template_string(HTML_DASH, connected=BOT_STATE["connected"])
@app.route('/logs')
def logs(): return jsonify({"logs": SYSTEM_LOGS})
@app.route('/leaderboard')
def lb(): return render_template_string(HTML_LB, users=db_get_leaderboard())

@app.route('/connect', methods=['POST'])
def conn():
    if BOT_STATE["connected"]: return jsonify({"status": "Already On"})
    d = request.json
    BOT_STATE.update({"username": d['u'], "password": d['p'], "room_name": d['r'], "domain": request.url_root})
    threading.Thread(target=ws_thread).start()
    return jsonify({"status": "Booting..."})

@app.route('/disconnect', methods=['POST'])
def disconn():
    if BOT_STATE["ws"]: BOT_STATE["ws"].close()
    BOT_STATE["connected"] = False
    return jsonify({"status": "Offline"})

@app.route('/api/greet_instant')
def api_g():
    img = generate_greet_card(request.args.get('u'), request.args.get('a'), request.args.get('bg'), request.args.get('m'))
    return send_file(img, mimetype='image/png') if img else ("Err", 500)

@app.route('/api/id_card')
def api_id():
    img = generate_id_card(request.args.get('u'), request.args.get('a'))
    return send_file(img, mimetype='image/png') if img else ("Err", 500)

@app.route('/api/winner')
def api_win():
    img = generate_winner_card(request.args.get('u'), request.args.get('a'), request.args.get('p'))
    return send_file(img, mimetype='image/png') if img else ("Err", 500)

def ws_thread():
    def on_open(ws):
        BOT_STATE["connected"] = True
        ws.send(json.dumps({"handler": "login", "id": gen_random_string(20), "username": BOT_STATE["username"], "password": BOT_STATE["password"]}))
        def heart():
            while BOT_STATE["connected"]: time.sleep(25); ws.send(json.dumps({"handler": "ping"}))
        threading.Thread(target=heart, daemon=True).start()
    
    ws = websocket.WebSocketApp("wss://chatp.net:5333/server", on_open=on_open, on_message=on_socket_message, on_close=lambda w,c,m: log("WS Closed", "err"))
    BOT_STATE["ws"] = ws
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

HTML_DASH = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITAN ARABIC V13</title>
<style>body{background:#050505;color:#00f3ff;font-family:monospace;padding:20px;text-align:center}input,button{padding:12px;margin:5px;width:90%;background:#111;color:#fff;border:1px solid #333}button{background:#ff00ff;color:#000;font-weight:bold;cursor:pointer}#logs{height:300px;overflow-y:scroll;border:1px solid #333;text-align:left;padding:10px;background:#000;margin-top:10px}</style></head>
<body><h1>👑 TITAN ARABIC V13</h1><div>STATUS: <span id="st">{{ 'ONLINE' if connected else 'OFFLINE' }}</span></div><br>
<input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><input id="r" placeholder="Room Name"><br>
<button onclick="a('/connect')">START BOT</button><button onclick="a('/disconnect')" style="background:red;color:white">STOP BOT</button>
<a href="/leaderboard" style="color:white;display:block;margin:10px">📊 LEADERBOARD</a>
<div id="logs"></div><script>
function a(p){fetch(p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({u:document.getElementById('u').value,p:document.getElementById('p').value,r:document.getElementById('r').value})}).then(r=>r.json()).then(d=>alert(d.status))}
setInterval(()=>fetch('/logs').then(r=>r.json()).then(d=>{document.getElementById('logs').innerHTML=d.logs.reverse().map(l=>`<div>[${l.time}] ${l.msg}</div>`).join('')}),2000);
</script></body></html>
"""

HTML_LB = """
<!DOCTYPE html><html><body style="background:#111;color:white;text-align:center;font-family:sans-serif"><h1>🏆 RANKINGS</h1>
{% for u in users %}<div style="background:#222;padding:10px;margin:5px;border-left:5px solid #ff00ff;display:flex;align-items:center;gap:10px">
<img src="{{u[3]}}" width="50" style="border-radius:50%"><div><b>{{u[0]}}</b><br>{{u[1]}} PTS</div></div>{% endfor %}</body></html>
"""

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))