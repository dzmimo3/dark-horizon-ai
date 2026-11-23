import os, io, base64, asyncio, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}

def save_db(q, a):
    u, k = os.environ.get("SUPABASE_URL", "").strip(), os.environ.get("SUPABASE_KEY", "").strip()
    if not u or not k: return
    try:
        requests.post(f"{u}/rest/v1/archives",
            headers={"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={"prompt": q[:1500], "response": a[:4000]}, timeout=4)
    except Exception: pass

def translate_prompt(raw_q):
    if "مقام الشهيد" in raw_q:
        return "Maqam Echahid Martyrs Memorial monument in Algiers Algeria, three iconic curving concrete palm leaves meeting at the top, golden sunset, photorealistic 8k, no text"
    sl, gk = chr(47), os.environ.get("GROQ_API_KEY", "").strip()
    if gk and any(ord(c) > 127 for c in raw_q):
        try:
            u = "https:" + sl + sl + "api." + "groq.com" + sl + "openai" + sl + "v1" + sl + "chat" + sl + "completions"
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [
                    {"role": "system", "content": "Translate to a vivid English image prompt (max 20 words, photorealistic 8k, no text). Output ONLY the prompt."},
                    {"role": "user", "content": raw_q}
                ], "temperature": 0.2}, timeout=6)
            if r.status_code == 200:
                t = (next(iter(r.json().get("choices") or []), {}).get("message") or {}).get("content", "").strip()
                if len(t) > 4: return t.replace('"', '') + ", no text"
        except Exception: pass
    return raw_q + ", photorealistic 8k, cinematic, no text"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON FILMS ONLINE"}), 200, cors()

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    sl, gk = chr(47), os.environ.get("GROQ_API_KEY", "").strip()
    sys_msg = "أنت المخرج والمساعد الذكي لموقع DARK HORIZON FILMS. تفهم جميع اللغات واللهجات ولغات البرمجة وتجيب بدقة."
    if gk:
        try:
            u = "https:" + sl + sl + "api." + "groq.com" + sl + "openai" + sl + "v1" + sl + "chat" + sl + "completions"
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]}, timeout=12)
            if r.status_code == 200:
                rep = (next(iter(r.json().get("choices") or []), {}).get("message") or {}).get("content", "").strip()
                if rep:
                    save_db(prompt, rep)
                    return jsonify({"reply": rep}), 200, cors()
        except Exception: pass
    return jsonify({"reply": "⚠️ تعذر الاتصال بالمحرك لحظياً."}), 200, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = translate_prompt(data.get("prompt", "cinematic masterpiece"))
    cid, ctok, sl = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip(), chr(47)
    if cid and ctok:
        u = "https:" + sl + sl + "api." + "cloudflare.com" + sl + "client" + sl + "v4" + sl + "accounts" + sl + cid + sl + "ai" + sl + "run" + sl + "@cf" + sl + "black-forest-labs" + sl + "flux-1-schnell"
        try:
            r = requests.post(u, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt}, timeout=15)
            if r.status_code == 200:
                ct = r.headers.get("Content-Type", "")
                if "image" in ct and len(r.content) > 4000: return Response(r.content, mimetype=ct, headers=cors())
                b64 = (r.json().get("result") or {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass
    return jsonify({"error": "img_busy"}), 503, cors()

@app.route("/api/tts", methods=["POST", "OPTIONS"])
def api_tts():
    if request.method == "OPTIONS": return ("", 204, cors())
    txt = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not txt: return ("", 400, cors())
    voice = "ar-SA-HamedNeural" if any("\u0600" <= c <= "\u06FF" for c in txt) else "en-US-AndrewNeural"
    try:
        import edge_tts
        async def gen():
            comm = edge_tts.Communicate(txt[:1000], voice)
            buf = io.BytesIO()
            async for ch in comm.stream():
                if ch["type"] == "audio": buf.write(ch["data"])
            return buf.getvalue()
        return Response(asyncio.run(gen()), mimetype="audio/mpeg", headers=cors())
    except Exception: return ("", 500, cors())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
