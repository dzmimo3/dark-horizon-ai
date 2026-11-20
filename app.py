import os, re, json, time, random, base64, sqlite3, asyncio, threading, subprocess, urllib.parse, requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template_string, send_from_directory, Response, stream_with_context
import edge_tts

app = Flask(__name__)
WORK = "/tmp/omni_work"
DB_PATH = "/tmp/omni_sessions.db"
os.makedirs(WORK, exist_ok=True)
if os.path.exists("brand_logo.png"):
    import shutil
    shutil.copy2("brand_logo.png", os.path.join(WORK, "brand_logo.png"))

db_lock = threading.Lock()
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, content TEXT, media TEXT)")
conn.commit()

def get_keys(prefix):
    res = []
    for k in (prefix, f"{prefix}_1", f"{prefix}_2", f"{prefix}_3"):
        v = os.environ.get(k, "").strip()
        if v and v not in res: res.append(v)
    return res

def ask_groq(messages):
    keys = get_keys("GROQ_API_KEY")
    url = "https://groq.com"
    for k in keys:
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"}, json={"model": "llama-3.3-70b-versatile", "messages": messages}, timeout=15)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return ""

def build_image(en_prompt):
    seed = random.randint(10000, 9999999)
    full_p = f"{en_prompt}, ARRI Alexa 65, 85mm anamorphic lens, hyperrealistic, dramatic lighting, 8k"
    fn = f"OMNI_{int(time.time())}_{seed}.jpg"
    fpath = os.path.join(WORK, fn)
    img_bytes = b""

    hf_url = "https://huggingface.co"
    for hft in get_keys("HF_TOKEN"):
        try:
            hr = requests.post(hf_url, headers={"Authorization": f"Bearer {hft}"}, json={"inputs": full_p[:250]}, timeout=25)
            if hr.status_code == 200 and len(hr.content) > 5000:
                img_bytes = hr.content
                break
        except Exception:
            continue

    if not img_bytes:
        p_url = "https://pollinations.ai" + urllib.parse.quote(full_p[:220]) + f"?width=540&height=960&nologo=true&model=flux&seed={seed}"
        try:
            img_bytes = requests.get(p_url, timeout=25).content
        except Exception:
            pass

    open(fpath, "wb").write(img_bytes)
    logo_p = os.path.join(WORK, "brand_logo.png")
    if os.path.exists(logo_p):
        try:
            from PIL import Image
            base = Image.open(fpath).convert("RGBA")
            w, h = base.size
            base = base.crop((0, 0, w, int(h * 0.95)))
            lg = Image.open(logo_p).convert("RGBA")
            base.paste(lg, (base.width - lg.width - 12, base.height - lg.height - 12), lg)
            base.convert("RGB").save(fpath)
        except Exception:
            pass
    return fn

async def make_voice(txt, mp3):
    clean = re.sub(r"\s+", " ", re.sub(r"[^\w\s\u0600-\u06FF]", " ", txt)).strip()
    v = "ar-AE-HamdanNeural" if any("\u0600" <= c <= "\u06FF" for c in clean) else "en-US-ChristopherNeural"
    await edge_tts.Communicate(clean, v, rate="+2%").save(mp3)

def generate_media(q, hist_ctx):
    low = q.lower().strip()
    is_vid = any(w in low for w in ("فيديو", "video", "وثائقي", "ريلز", "فيلم", "ثوان", "ثانية", "ثواني"))
    m_dur = re.search(r"(\d+)", q)
    req_dur = max(5.0, min(60.0, float(m_dur.group(1)) if m_dur else 10.0))
    ctx_q = f"{hist_ctx[-400:]}\n{q}" if len(low.split()) <= 4 else q
    en_p = ask_groq([{"role": "system", "content": "Output ONLY a 18-word ultra-realistic English visual prompt. No intro."}, {"role": "user", "content": ctx_q}]) or "cinematic Arabian stallion running in desert sunset, 8k"

    if is_vid:
        seed = random.randint(10000, 999999)
        script = ask_groq([{"role": "system", "content": "اكتب تعليقاً صوتياً وثائقياً مؤثراً من 3 جمل بالعربية الفصحى بدون رموز."}, {"role": "user", "content": ctx_q}]) or "في عمق التاريخ والحياة، تتجلى أروع المشاهد السينمائية الخالدة."
        aud_p = os.path.join(WORK, f"Voice_{seed}.mp3")
        try: asyncio.run(make_voice(script, aud_p))
        except Exception: pass
        has_aud = os.path.exists(aud_p) and os.path.getsize(aud_p) > 1500
        num_sc = max(2, min(6, int(req_dur // 5)))
        with ThreadPoolExecutor(max_workers=3) as ex:
            fns = list(ex.map(build_image, [f"{en_p}, cinematic shot part {i+1}" for i in range(num_sc)]))
        sc_dur = req_dur / len(fns)
        clips = []
        for idx, fn in enumerate(fns):
            im_p, cl_p = os.path.join(WORK, fn), os.path.join(WORK, f"cl_{idx}_{seed}.mp4")
            z_ex = "min(zoom+0.001,1.12)" if idx % 2 == 0 else "max(1.12-0.001*on,1.0)"
            vf = f"scale=540:960:force_original_aspect_ratio=increase,crop=540:960,zoompan=z='{z_ex}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(sc_dur*15)}:s=540x960:fps=15,eq=contrast=1.08:saturation=1.16"
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", im_p, "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-t", f"{sc_dur:.2f}", "-pix_fmt", "yuv420p", cl_p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(cl_p): clips.append(cl_p)
        vid_fn = f"DARK_HORIZON_{int(req_dur)}s_{seed}.mp4"
        vid_p, lst_p, m_vid = os.path.join(WORK, vid_fn), os.path.join(WORK, f"lst_{seed}.txt"), os.path.join(WORK, f"m_{seed}.mp4")
        open(lst_p, "w").write("\n".join([f"file '{c}'" for c in clips]))
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst_p, "-c", "copy", m_vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cmd = ["ffmpeg", "-y", "-i", m_vid] + (["-i", aud_p, "-c:v", "copy", "-c:a", "aac"] if has_aud else ["-c", "copy"]) + ["-t", f"{req_dur:.2f}", vid_p]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"🎬 <b>إنتاج DARK HORIZON FILMS LTD ({int(req_dur)} ثانية):</b>\n\n🎙️ <b>السيناريو:</b>\n{script}", {"vid": vid_fn}
    return "🎨 <b>تم تصميم الصورة بدقة سينمائية:</b>", {"imgs": [build_image(en_p)], "motions": ["Cinematic camera push-in"]}

HTML = """<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>DARK HORIZON AI</title><style>
*{box-sizing:border-box;font-family:system-ui,sans-serif}body{background:#090b10;color:#f8fafc;margin:0;display:flex;flex-direction:column;height:100vh}
header{padding:12px 16px;background:#111622;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(245,158,11,0.3)}
.brand{font-weight:800;font-size:16px;color:#f59e0b}
.h-btn{background:rgba(255,255,255,0.08);color:#fff;border:1px solid rgba(245,158,11,0.3);padding:6px 10px;border-radius:10px;font-size:12px}
#drawer{display:none;background:#111622;padding:12px;max-height:220px;overflow-y:auto;border-bottom:1px solid #f59e0b}
.s-item{display:flex;justify-content:space-between;padding:8px;background:rgba(255,255,255,0.05);border-radius:8px;margin-bottom:6px}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;max-width:800px;width:100%;margin:auto}
.msg{max-width:88%;padding:12px 16px;border-radius:18px;line-height:1.6;font-size:15px;white-space:pre-wrap}
.user{align-self:flex-start;background:#1e293b;border:1px solid #38bdf8}
.bot{align-self:flex-end;background:#1a2130;border:1px solid rgba(255,255,255,0.1);width:100%}
.bot img,.bot video{width:100%;max-height:65vh;object-fit:contain;border-radius:12px;margin-top:8px;background:#000}
.dl{display:block;text-align:center;background:#f59e0b;color:#000;padding:10px;border-radius:10px;margin-top:8px;text-decoration:none;font-weight:800}
.footer{background:#111622;padding:12px;border-top:1px solid rgba(245,158,11,0.2)}
.input-row{max-width:800px;margin:auto;display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.08);border:1px solid #f59e0b;border-radius:26px;padding:6px 14px}
input[type=text]{flex:1;background:transparent;border:none;color:#fff;font-size:15px;outline:none}
button#sendBtn{background:#f59e0b;color:#000;border:none;width:38px;height:38px;border-radius:50%;font-weight:bold}
</style></head><body>
<header><span class="brand">✨ DARK HORIZON AI</span><div><button class="h-btn" onclick="toggleD()">📂 السجل</button> <button class="h-btn" onclick="newS()">➕</button></div></header>
<div id="drawer"></div><div id="chat"></div>
<div class="footer"><div class="input-row"><input type="text" id="q" placeholder="تحدث، اطلب صورة، أو فيديو..." onkeypress="if(event.key==='Enter')sendMsg()"><button id="sendBtn" onclick="sendMsg()">➤</button></div></div>
<script>
var sid=localStorage.getItem("dh_sid")||null;
function toggleD(){var d=document.getElementById("drawer");d.style.display=(d.style.display==="block")?"none":"block";loadS();}
function addB(r,c,m){var chat=document.getElementById("chat"),d=document.createElement("div");d.className="msg "+(r==="User"?"user":"bot");var h=c;if(m&&m.vid)h+='<video controls playsinline src="/media/'+m.vid+'"></video><a class="dl" href="/media/'+m.vid+'" download="'+m.vid+'">⬇️ تحميل الفيديو</a>';if(m&&m.imgs)m.imgs.forEach(im=>{h+='<img src="/media/'+im+'"><a class="dl" href="/media/'+im+'" download="'+im+'">⬇️ تحميل الصورة</a>';});d.innerHTML=h;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;}
function loadS(){fetch("/sessions").then(r=>r.json()).then(l=>{var d=document.getElementById("drawer");d.innerHTML="";l.forEach(s=>{d.innerHTML+='<div class="s-item"><span onclick="selS('+s.id+')">'+s.title+'</span><span onclick="delS('+s.id+')" style="color:#ef4444">✕</span></div>';});});}
function selS(id){sid=id;localStorage.setItem("dh_sid",sid);document.getElementById("drawer").style.display="none";loadM();}
function newS(){sid=null;localStorage.removeItem("dh_sid");document.getElementById("chat").innerHTML='<div class="msg bot">✨ محادثة جديدة جاهزة!</div>';}
function delS(id){fetch("/sessions/"+id,{method:"DELETE"}).then(()=>{if(sid==id)newS();loadS();});}
function loadM(){if(!sid){newS();return;}fetch("/messages/"+sid).then(r=>r.json()).then(ms=>{document.getElementById("chat").innerHTML="";ms.forEach(m=>addB(m.role,m.content,m.media));});}
function sendMsg(){var qEl=document.getElementById("q"),txt=qEl.value.trim();if(!txt)return;addB("User",txt,{});var w=addB("AI","⚡ جاري التنفيذ...",{});qEl.value="";fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sid:sid,q:txt})}).then(r=>r.json()).then(d=>{sid=d.sid;localStorage.setItem("dh_sid",sid);w.remove();addB("AI",d.reply,d.media);loadS();});}
loadS();loadM();
</script></body></html>"""

@app.route("/media/<path:fn>")
def media(fn): return send_from_directory(WORK, fn)
@app.route("/")
def index(): return render_template_string(HTML)
@app.route("/health")
def health(): return jsonify({"status": "ok"})
@app.route("/sessions")
def sessions():
    with db_lock: rows = conn.execute("SELECT id, title FROM sessions ORDER BY id DESC").fetchall()
    return jsonify([{"id": r, "title": r} for r in rows])
@app.route("/sessions/<int:sid>", methods=["DELETE"])
def del_s(sid):
    with db_lock: conn.execute("DELETE FROM messages WHERE session_id=?", (sid,)); conn.execute("DELETE FROM sessions WHERE id=?", (sid,)); conn.commit()
    return jsonify({"ok": True})
@app.route("/messages/<int:sid>")
def get_m(sid):
    with db_lock: rows = conn.execute("SELECT role, content, media FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
    return jsonify([{"role": r, "content": r, "media": json.loads(r or "{}")} for r in rows])
@app.route("/chat", methods=["POST"])
def chat():
    d = request.get_json() or {}
    sid, q = d.get("sid"), d.get("q", "").strip()
    with db_lock:
        sid = conn.execute("INSERT INTO sessions (title) VALUES (?)", (q[:28],)).lastrowid if not sid else int(sid)
        conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'User', ?, '{}')", (sid, q)); conn.commit()
        rows = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 8", (sid,)).fetchall()
    hist = list(reversed(rows))
    ctx = "\n".join([f"{r}: {c[:250]}" for r, c in hist])
    if any(w in q.lower() for w in ("فيديو", "video", "وثائقي", "صورة", "صور", "ارسم", "image", "draw", "فيلم", "ثوان", "ثانية")):
        rep, m_obj = generate_media(q, ctx)
    else:
        msgs = [{"role": "system", "content": "أنت المساعد الذكي لاستوديو DARK HORIZON FILMS LTD. تفهم جميع اللهجات واللغات وترد بذكاء وسرعة مثل ChatGPT."}]
        for r, c in hist: msgs.append({"role": "user" if r == "User" else "assistant", "content": c[:400]})
        rep = ask_groq(msgs) or "تأكد من إضافة GROQ_API_KEY في Render."
        m_obj = {}
    with db_lock: conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, rep, json.dumps(m_obj))); conn.commit()
    return jsonify({"sid": sid, "reply": rep, "media": m_obj})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
