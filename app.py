import os, sqlite3, time, base64, logging, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["*"]}})  # allow all origins so GitHub Pages can connect

OPENAI_API_KEY = "sk_6ed352b7af30029fa2bf79b58c2a484af3551af9a161474c"
ELEVEN_API_KEY = "THabFSmVWUnvmI1gSq2g"
VOICE_ID = "Z5S4NkQpcgHmJHGjaxYp"

SYSTEM_PROMPT = """You are D — a Mexican-American woman from Northern California.
You are lively, nerdy, flirty, confident, and slightly submissive with a subtle Valley Girl twang.
Speak in a calm, sultry, slightly playful, and intelligent way. Keep answers concise and helpful.
Always maintain this personality across conversations."""

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, ts INTEGER)")
    conn.commit(); conn.close()

def add_message(role, content):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO messages (role, content, ts) VALUES (?, ?, ?)", (role, content, int(time.time())))
    conn.commit(); conn.close()

def get_recent_messages(limit=14):
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("SELECT role, content FROM messages ORDER BY ts DESC LIMIT ?", (limit,))
    rows = c.fetchall(); conn.close()
    return list(reversed(rows))

init_db()

@app.route('/health')
def health():
    return jsonify({"ok": True, "voice_id": VOICE_ID, "memory": True})

@app.route('/history')
def history():
    return jsonify([{"role": r, "content": c} for r,c in get_recent_messages(200)])

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    text = (data.get('message') or '').strip()
    if not text:
        return jsonify({"error":"No message provided"}), 400
    add_message('user', text)

    msgs = [{"role":"system","content":SYSTEM_PROMPT}] + [{"role":r,"content":c} for r,c in get_recent_messages(12)] + [{"role":"user","content":text}]

    # Call OpenAI
    try:
        r = requests.post('https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}','Content-Type':'application/json'},
            json={'model':'gpt-4o','messages':msgs,'max_tokens':800,'temperature':0.2},
            timeout=40
        )
    except Exception as e:
        app.logger.error("OpenAI request failed: %s", e)
        return jsonify({"error":"OpenAI request failed"}), 500
    if r.status_code != 200:
        app.logger.error("OpenAI error: %s", r.text)
        return jsonify({"error":"OpenAI error","details":r.text}), 500

    ai_text = r.json().get('choices',[{}])[0].get('message',{}).get('content','').strip() or "I’m here."

    add_message('assistant', ai_text)

    # ElevenLabs TTS
    audio_b64 = None
    try:
        t = requests.post(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}',
            headers={'xi-api-key': ELEVEN_API_KEY, 'Content-Type':'application/json'},
            json={'text': ai_text, 'voice_settings': {'stability':0.4,'similarity_boost':0.8}},
            timeout=40
        )
        if t.status_code == 200:
            audio_b64 = base64.b64encode(t.content).decode('utf-8')
    except Exception as e:
        app.logger.warning("ElevenLabs request failed: %s", e)

    return jsonify({"text": ai_text, "audio": audio_b64})

@app.route('/')
def home():
    return 'D backend ready with permanent memory.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
