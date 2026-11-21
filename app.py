import os, io, json, time, base64, random, urllib.parse, sqlite3, threading, subprocess, requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
db_lock = threading.Lock()
DB_PATH = "/tmp/dh_luxury.db"
MEDIA_DIR = "/tmp/dh_media"
os.makedirs(MEDIA_DIR, exist_ok=True)

def init_db():
    with db_lock:
        c = sqlite3.connect(DB_PATH)
        c.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, content TEXT, media TEXT)")
        c.commit(); c.close()
init_db()

def get_key(name):
    val = os.environ.get(name, "").strip()
    return next(iter([x.strip() for x in val.split(",") if x.strip()]), "")

def upload_cdn(local_path, filename, mime="image/jpeg"):
    su, sk = get_key("SUPABASE_URL").rstrip("/"), get_key("SUPABASE_SERVICE_KEY")
    if not su or not sk or not os.path.exists(local_path): return None
    try:
        hdrs = {"apikey": sk, "Authorization": f"Bearer {sk}", "Content-Type": mime, "x-upsert": "true"}
        r = requests.post(f"{su}/storage/v1/object/media/{filename}", headers=hdrs, data=open(local_path, "rb").read(), timeout=20)
        if r.status_code in (200, 201): return f"{su}/storage/v1/object/public/media/{filename}"
    except Exception: pass
    return None

def search_web(q):
    tv = get_key("TAVILY_API_KEY")
    if not tv: return ""
    try:
        r = requests.post("https://tavily.com", json={"api_key": tv, "query": q, "include_answer": True, "max_results": 3}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            res = [d["answer"]] if d.get("answer") else []
            for it in d.get("results", [])[:2]: res.append(f"- {it.get('title','')}: {it.get('content','')[:160]}")
            return "\n".join(res)
    except Exception: pass
    return ""

def ai_brain(messages, sys_override=None):
    sys_msg = sys_override or "أنت DARK HORIZON AI، مساعد ومخرج ذكي يتحدث بالعربية والدارجة والفرنسية والإنجليزية بطلاقة ووضوح وأسلوب إنساني راقٍ ومباشر."
    clean = [{"role": ("assistant" if m.get("role") == "AI" else "user"), "content": str(m.get("content", ""))} for m in messages if m.get("content")]
    if not clean: clean = [{"role": "user", "content": "مرحباً"}]
    pk = get_key("POLLINATIONS_API_KEY")
    if pk:
        try:
            r = requests.post("https://pollinations.ai", headers={"Authorization": f"Bearer {pk}", "Content-Type": "application/json"}, json={"model": "openai", "messages": [{"role": "system", "content": sys_msg}] + clean[-6:]}, timeout=14)
            if r.status_code == 200:
                txt = next(iter(r.json().get("choices", [])), {}).get("message", {}).get("content", "").strip()
                if txt: return txt
        except Exception: pass
    gq = get_key("GROQ_API_KEY")
    if gq:
        try:
            r = requests.post("https://groq.com", headers={"Authorization": f"Bearer {gq}"}, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}] + clean[-6:]}, timeout=12)
            if r.status_code == 200:
                txt = next(iter(r.json().get("choices", [])), {}).get("message", {}).get("content", "").strip()
                if txt: return txt
        except Exception: pass
    gk = get_key("GEMINI_API_KEY")
    if gk:
        try:
            gm = [{"role": ("model" if m["role"] == "assistant" else "user"), "parts": [{"text": m["content"]}]} for m in clean[-6:]]
            r = requests.post(f"https://googleapis.com{gk}", json={"systemInstruction": {"parts": [{"text": sys_msg}]}, "contents": gm}, timeout=15)
            if r.status_code == 200:
                c0 = next(iter(r.json().get("candidates", [])), {})
                txt = next(iter(c0.get("content", {}).get("parts", [])), {}).get("text", "").strip()
                if txt: return txt
        except Exception: pass
    return "تم استلام رسالتك، أعد المحاولة بعد لحظة."

def create_image(prompt):
    en_p = ai_brain([{"role": "user", "content": f"Convert into a modest, ultra-realistic 8K RAW DSLR English photo prompt (ONLY English words): {prompt}"}])
    if len(en_p) < 5 or "تم استلام" in en_p: en_p = "majestic cinematic 8k ultra realistic photography, natural lighting, sharp focus"
    fn = f"dh_img_{int(time.time())}.jpg"
    fpath = os.path.join(MEDIA_DIR, fn)
    pk = get_key("POLLINATIONS_API_KEY")
    for mdl in ("flux", "turbo"):
        try:
            base_u = "https://pollinations.ai" if pk else "https://pollinations.ai"
            hdrs = {"Authorization": f"Bearer {pk}"} if pk else {"User-Agent": "Mozilla/5.0"}
            r = requests.get(f"{base_u}{urllib.parse.quote(en_p[:220])}?width=1024&height=1024&model={mdl}&nologo=true&seed={random.randint(1,999999)}", headers=hdrs, timeout=28)
            if r.status_code == 200 and len(r.content) > 3000:
                open(fpath, "wb").write(r.content)
                return upload_cdn(fpath, fn, "image/jpeg") or ("data:image/jpeg;base64," + base64.b64encode(r.content).decode("utf-8"))
        except Exception: pass
    cf_id, cf_tok = get_key("CF_ACCOUNT_ID"), get_key("CF_API_TOKEN")
    if cf_id and cf_tok:
        try:
            r = requests.post(f"https://cloudflare.com{cf_id}/ai/run/@cf/black-forest-labs/flux-1-schnell", headers={"Authorization": f"Bearer {cf_tok}"}, json={"prompt": en_p[:240], "num_steps": 6}, timeout=25)
            if r.status_code == 200 and r.json().get("result", {}).get("image"):
                raw = base64.b64decode(r.json()["result"]["image"])
                open(fpath, "wb").write(raw)
                return upload_cdn(fpath, fn, "image/jpeg") or ("data:image/jpeg;base64," + r.json()["result"]["image"])
        except Exception: pass
    return None

def create_video(prompt):
    img_url = create_image(prompt)
    fn = f"dh_vid_{int(time.time())}.mp4"
    fpath = os.path.join(MEDIA_DIR, fn)
    imgs = sorted([f for f in os.listdir(MEDIA_DIR) if f.endswith(".jpg")])
    if imgs:
        last_img = os.path.join(MEDIA_DIR, imgs[-1])
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", last_img, "-vf", "scale=1280:720,zoompan=z='min(zoom+0.0015,1.25)':d=125:s=1280x720", "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p", fpath]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 4000:
            return upload_cdn(fpath, fn, "video/mp4") or ("data:video/mp4;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8"))
    return None

HTML_UI = """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DARK HORIZON AI</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top,#181b22 0%,#0b0c0e 100%);color:#f1f3f4;font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;height:100vh}
header{padding:14px 18px;background:rgba(20,22,27,0.85);backdrop-filter:blur(12px);display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.08)}
.brand{font-weight:800;font-size:16px;letter-spacing:0.5px;background:linear-gradient(90deg,#a8c7fa,#d2e3fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.top-btn{background:rgba(255,255,255,0.06);color:#e3e3e3;border:1px solid rgba(255,255,255,0.12);border-radius:20px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;transition:0.2s}
.top-btn:active{transform:scale(0.96);background:rgba(168,199,250,0.18)}
#chat{flex:1;overflow-y:auto;padding:18px 14px;display:flex;flex-direction:column;gap:14px}
.msg{max-width:86%;padding:13px 17px;border-radius:20px;line-height:1.65;font-size:15px;word-wrap:break-word;box-shadow:0 4px 16px rgba(0,0,0,0.25)}
.USER{align-self:flex-start;background:linear-gradient(135deg,#262932,#1e2028);border:1px solid rgba(255,255,255,0.08);border-bottom-right-radius:6px}
.AI{align-self:flex-end;background:rgba(24,26,32,0.9);border:1px solid rgba(168,199,250,0.14);border-bottom-left-radius:6px;width:92%}
.dock{padding:12px 14px 16px;background:linear-gradient(to top,#0b0c0e 70%,transparent)}
.bar{display:flex;align-items:center;gap:8px;background:#181a20;border:1px solid rgba(255,255,255,0.14);border-radius:30px;padding:6px 10px 6px 6px;box-shadow:0 8px 28px rgba(0,0,0,0.45);transition:border 0.2s}
.bar:focus-within{border-color:#8ab4f8}
.plus{width:38px;height:38px;border-radius:50%;border:none;background:rgba(255,255,255,0.07);color:#c4c7c5;font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center}
input{flex:1;background:transparent;border:none;color:#fff;font-size:15px;padding:8px 6px;outline:none}
.send{width:42px;height:42px;border-radius:50%;border:none;background:linear-gradient(135deg,#a8c7fa,#669df6);color:#041e49;font-size:17px;font-weight:bold;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(138,180,248,0.35);transition:0.2s}
.send:active{transform:scale(0.92)}
img,video{max-width:100%;border-radius:14px;margin-top:12px;display:block;border:1px solid rgba(255,255,255,0.1)}
.actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.act{background:rgba(168,199,250,0.12);color:#a8c7fa;border:1px solid rgba(168,199,250,0.25);padding:6px 13px;border-radius:14px;text-decoration:none;font-size:12px;font-weight:600;cursor:pointer}
</style></head>
<body>
<header><div class="brand">✦ DARK HORIZON AI</div><button class="top-btn" onclick="sid=null;document.getElementById('chat').innerHTML=''">+ محادثة جديدة</button></header>
<div id="chat"></div>
<div class="dock"><div class="bar"><button class="plus" onclick="document.getElementById('q').focus()" title="إدراج">+</button><input id="q" placeholder="اسأل، أو اطلب تصميم صورة أو فيديو..." onkeydown="if(event.key==='Enter')send()"><button class="send" onclick="send()">➤</button></div></div>
<script>
let sid=null;
function copyTxt(btn){const t=btn.closest('.msg').innerText.replace(/📋 نسخ|⬇️ تحميل.*/g,'').trim();navigator.clipboard.writeText(t);btn.textContent='✅ تم النسخ';setTimeout(()=>btn.textContent='📋 نسخ',1500);}
function addMsg(r,t,m){
  const d=document.createElement('div');d.className='msg '+r;
  d.innerHTML=t.replace(/\\n/g,'<br>');
  if(m&&m.img)d.innerHTML+=`<img src="${m.img}"><div class="actions"><a class="act" href="${m.img}" download="DarkHorizon_8K.jpg" target="_blank">⬇️ تحميل الصورة</a></div>`;
  if(m&&m.vid)d.innerHTML+=`<video controls autoplay loop src="${m.vid}"></video><div class="actions"><a class="act" href="${m.vid}" download="DarkHorizon_Video.mp4" target="_blank">⬇️ تحميل الفيديو</a></div>`;
  if(r==='AI'&&(!m||(!m.img&&!m.vid)))d.innerHTML+=`<div class="actions"><button class="act" onclick="copyTxt(this)">📋 نسخ</button></div>`;
  const c=document.getElementById('chat');c.appendChild(d);c.scrollTop=c.scrollHeight;return d;
}
async function send(){
  const i=document.getElementById('q'),t=i.value.trim();if(!t)return;i.value='';
  addMsg('USER',t);const w=addMsg('AI','⏳ جاري التنفيذ...');
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid,text:t})});
    const d=await r.json();sid=d.sid;w.remove();addMsg('AI',d.reply,d.media);
  }catch(e){w.innerHTML='⚠️ تعذر الاتصال، أعد المحاولة.';}
}
</script></body></html>"""

@app.route("/")
def index(): return render_template_string(HTML_UI)

@app.route("/health")
def health(): return jsonify({"status": "ok"})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        d = request.json or {}
        text, sid = d.get("text", "").strip(), d.get("sid")
        with db_lock:
            c = sqlite3.connect(DB_PATH)
            if not sid: sid = c.execute("INSERT INTO sessions (title) VALUES (?)", (text[:30],)).lastrowid
            c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, 'USER', ?)", (sid, text))
            rows = c.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
            c.commit(); c.close()
        hist = [{"role": r[0], "content": r[1]} for r in rows]
        low, media = text.lower(), {}
        if any(w in low for w in ("فيديو", "مقطع", "انميشن", "تحريك", "video", "cinema")):
            vid = create_video(text)
            reply, media = ("🎬 <b>تم إنتاج الفيديو بنجاح:</b>", {"vid": vid}) if vid else ("⚠️ تعذر إنتاج الفيديو حالياً، أعد المحاولة.", {})
        elif any(w in low for w in ("صورة", "صور", "ارسم", "صمم", "تصويرة", "image", "draw", "photo")):
            img = create_image(text)
            reply, media = ("🎨 <b>تم تصميم الصورة بدقة عالية:</b>", {"img": img}) if img else ("⚠️ تعذر تصميم الصورة حالياً، أعد المحاولة.", {})
        else:
            ctx = search_web(text) if any(w in low for w in ("ابحث", "أخبار", "طقس", "من هو", "ما هو", "اليوم", "2026")) else ""
            if ctx: hist[-1]["content"] = f"معلومات محدثة:\n{ctx}\n\nسؤال المستخدم: {text}"
            reply = ai_brain(hist)
        with db_lock:
            c = sqlite3.connect(DB_PATH)
            c.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, reply, json.dumps(media)))
            c.commit(); c.close()
        return jsonify({"sid": sid, "reply": reply, "media": media})
    except Exception as e:
        return jsonify({"sid": 1, "reply": f"⚠️ تنبيه: {str(e)}", "media": {}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
