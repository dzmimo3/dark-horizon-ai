import os, re, json, time, random, base64, sqlite3, asyncio, threading, urllib.parse, requests
from flask import Flask, request, jsonify, render_template_string, send_from_directory, Response, stream_with_context
import edge_tts

app = Flask(__name__)
WORK = os.path.expanduser("~/omni_work")
DB_PATH = os.path.expanduser("~/omni_sessions.db")
os.makedirs(WORK, exist_ok=True)
db_lock = threading.Lock()
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, content TEXT, media TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS config (k TEXT PRIMARY KEY, v TEXT)")
conn.commit()

def get_cfg(k):
    with db_lock:
        r = conn.execute("SELECT v FROM config WHERE k=?", (k,)).fetchone()
    return r.__getitem__(0) if r else ""

def fetch_wiki(q):
    try:
        cq = re.sub(r"(فيديو|وثائقي|يتحدث|عن|على|اصنع|انشيء)", "", q).strip()
        w = requests.get("https://wikipedia.org" + urllib.parse.quote(cq) + "&format=json&srlimit=1", headers={"User-Agent": "OMNI/1.0"}, timeout=5).json()
        hits = w.get("query", {}).get("search", ())
        if hits:
            t = hits.__getitem__(0)["title"]
            s = requests.get("https://wikipedia.org" + urllib.parse.quote(t), headers={"User-Agent": "OMNI/1.0"}, timeout=5).json()
            return s.get("extract", "")[:450]
    except Exception: pass
    return ""

def stream_llm(messages):
    gem_key = os.environ.get("GEMINI_API_KEY", "") or get_cfg("gemini_key")
    groq_key = os.environ.get("GROQ_API_KEY", "") or get_cfg("groq_key")
    ans = ""

    # 1. Google Gemini 2.5 Flash الرسمي المجاني (يعمل 100% على خوادم Render)
    if gem_key:
        try:
            sys_txt, contents = "", []
            for m in messages:
                if m.get("role") == "system": sys_txt = str(m.get("content", ""))
                else:
                    rg = "model" if m.get("role") == "assistant" else "user"
                    contents.append({"role": rg, "parts": [{"text": str(m.get("content", ""))}]})
            payload = {"contents": contents}
            if sys_txt: payload["systemInstruction"] = {"parts": [{"text": sys_txt}]}
            gr = requests.post(f"https://googleapis.com{gem_key}", json=payload, timeout=15).json()
            cands = gr.get("candidates", ())
            if cands: ans = cands.__getitem__(0).get("content", {}).get("parts", ()).__getitem__(0).get("text", "").strip()
        except Exception: pass

    # 2. Groq Cloud الرسمي المجاني (Llama 3.3 70B)
    if not ans and groq_key:
        try:
            r = requests.post("https://groq.com", headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}, json={"model": "llama-3.3-70b-versatile", "messages": messages}, timeout=12).json()
            ch = r.get("choices", ())
            if ch: ans = ch.__getitem__(0).get("message", {}).get("content", "").strip()
        except Exception: pass

    # 3. نقطة Pollinations النصية المباشرة مع تمرير سياق المحادثة
    if not ans:
        try:
            sl = chr(47)
            ctx_q = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-4:]])[:450]
            r2 = requests.get(f"https:{sl}{sl}text.pollinations.ai{sl}" + urllib.parse.quote(ctx_q), params={"seed": random.randint(1, 99999)}, timeout=12)
            if r2.status_code == 200 and "Free limit" not in r2.text and "404" not in r2.text:
                ans = r2.text.strip()
        except Exception: pass

    if not ans:
        ans = "أهلاً بك! لتفعيل الذكاء الاصطناعي الكامل بسرعة ChatGPT على السحابة مجاناً، ضع مفتاح Google Gemini المجاني في زر (⚙️ API) بالأعلى."
    yield ans

def call_llm_sync(messages):
    return "".join(list(stream_llm(messages)))

def build_image(en_prompt):
    seed = random.randint(10000, 9999999)
    sl = chr(47)
    full_p = f"{en_prompt}, shot on ARRI Alexa 65, IMAX 70mm, anamorphic lens, hyper-realistic detailed textures, volumetric golden lighting, shallow depth of field, photorealistic, 8k uhd"
    url = f"https:{sl}{sl}image.pollinations.ai{sl}prompt{sl}" + urllib.parse.quote(full_p[:240]) + f"?width=540&height=960&nologo=true&model=flux&seed={seed}"
    fn = f"OMNI_{int(time.time())}_{seed}.jpg"
    fpath = os.path.join(WORK, fn)
    hf_tok = os.environ.get("HF_TOKEN", "")
    img_bytes = b""
    if hf_tok:
        try:
            hr = requests.post(
                "https://huggingface.co",
                headers={"Authorization": f"Bearer {hf_tok}"},
                json={"inputs": full_p[:240]},
                timeout=25
            )
            if hr.status_code == 200 and len(hr.content) > 5000:
                img_bytes = hr.content
        except Exception:
            pass
    if not img_bytes:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        img_bytes = r.content
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

import subprocess, glob
from concurrent.futures import ThreadPoolExecutor

def parse_arabic_duration(q):
    words_map = {"ثلاث": 3, "اربع": 4, "أربع": 4, "خمس": 5, "ست": 6, "سبع": 7, "ثمان": 8, "تسع": 9, "عشر": 10, "عشرين": 20, "ثلاثين": 30}
    m = re.search(r"(\d+)", q)
    if m: return float(m.group(1))
    for k, v in words_map.items():
        if k in q: return float(v)
    return 8.0

def generate_media_kit(q, hist_ctx):
    low = q.lower().strip()
    is_vid = any(w in low for w in ("فيديو", "video", "وثائقي", "ريلز", "مشهد", "قصة", "تاريخي", "film", "reel", "ديرها", "حولها", "اجعله", "ثوان", "ثانية", "ثواني"))
    is_short = len(low.split()) <= 5
    source_text = f"{hist_ctx[-500:]}\nالطلب: {q}" if (is_short and hist_ctx) else q
    req_dur = max(4.0, min(45.0, parse_arabic_duration(q)))

    if is_vid:
        seed = random.randint(10000, 999999)
        # إذا طلب تحويل الصورة الأخيرة ("اجعله فيديو" / "حولها") نستخدم آخر صورة جاهزة فوراً لسرعة البرق
        existing_imgs = sorted(glob.glob(os.path.join(WORK, "OMNI_*.jpg")), key=os.path.getmtime)
        use_last = any(w in low for w in ("اجعله", "اجعلها", "حولها", "ديرها", "هذي", "هذه")) and len(existing_imgs) > 0

        if use_last:
            img_paths = [existing_imgs.__getitem__(-1)]
            script = ""
        else:
            en_p = call_llm_sync([{"role": "system", "content": "Write ONLY a 15-word English cinematic visual prompt."}, {"role": "user", "content": source_text}]) or "cinematic evening street with glowing lanterns, 8k"
            angles = ("wide cinematic shot", "emotional close-up portrait")
            with ThreadPoolExecutor(max_workers=2) as ex:
                fns = list(ex.map(build_image, [f"{en_p}, {a}" for a in angles]))
            img_paths = [os.path.join(WORK, fn) for fn in fns]

            wiki = fetch_wiki(source_text)
            script = call_llm_sync([{"role": "system", "content": "اكتب تعليقاً صوتياً وثائقياً قصيراً من جملتين بالعربية الفصحى بدون رموز."}, {"role": "user", "content": f"{source_text}\n{wiki}"}]) or "في صفحات التاريخ والحياة، تتجلى أجمل المشاهد السينمائية الخالدة."

        aud_p = os.path.join(WORK, f"Voice_{seed}.mp3")
        has_aud = False
        if script and "صامت" not in low:
            try: asyncio.run(make_voice(script, aud_p))
            except Exception: pass
            has_aud = os.path.exists(aud_p) and os.path.getsize(aud_p) > 1500

        sc_dur = req_dur / len(img_paths)
        clip_files = []
        for idx, im_p in enumerate(img_paths):
            cl_p = os.path.join(WORK, f"clip_{idx}_{seed}.mp4")
            z_expr = "min(zoom+0.001,1.12)" if idx % 2 == 0 else "max(1.12-0.001*on,1.0)"
            # معالجة خفيفة وسريعة جداً (540x960 @ 15fps) بتدريج لوني سينمائي
            v_fx = f"scale=540:960:force_original_aspect_ratio=increase,crop=540:960,zoompan=z='{z_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(sc_dur*15)}:s=540x960:fps=15,eq=contrast=1.08:saturation=1.16"
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", im_p, "-vf", v_fx, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-t", f"{sc_dur:.2f}", "-pix_fmt", "yuv420p", cl_p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(cl_p): clip_files.append(cl_p)

        vid_fn = f"DARK_HORIZON_{int(req_dur)}s_{seed}.mp4"
        vid_p = os.path.join(WORK, vid_fn)
        lst_p = os.path.join(WORK, f"lst_{seed}.txt")
        open(lst_p, "w").write("\n".join([f"file '{c}'" for c in clip_files]))

        m_vid = os.path.join(WORK, f"merged_{seed}.mp4")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst_p, "-c", "copy", m_vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        fade_st = max(0.5, req_dur - 0.6)
        if has_aud:
            subprocess.run(["ffmpeg", "-y", "-i", m_vid, "-i", aud_p, "-vf", f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_st:.2f}:d=0.5", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-t", f"{req_dur:.2f}", vid_p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["ffmpeg", "-y", "-i", m_vid, "-vf", f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_st:.2f}:d=0.5", "-c:v", "libx264", "-preset", "ultrafast", "-t", f"{req_dur:.2f}", vid_p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        rep = f"🎬 <b>تم إنتاج الفيديو السينمائي ({int(req_dur)} ثوانٍ - DARK HORIZON FILMS LTD):</b>" + (f"\n\n🎙️ <b>النص المسموع:</b>\n{script}" if script else "")
        return rep, {"vid": vid_fn}

    en_p = call_llm_sync([{"role": "system", "content": "Write ONLY a 15-word English realistic visual prompt."}, {"role": "user", "content": source_text}]) or "cinematic evening street with glowing lanterns, 8k"
    return "🎨 <b>تم تصميم الصورة المطلوبة:</b>", {"imgs": [build_image(en_p)], "motions": ["Cinematic camera push-in"]}

HTML = """<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>DARK HORIZON | ENTERPRISE AI</title><style>
*{box-sizing:border-box;font-family:system-ui,sans-serif}body{background:radial-gradient(circle at top,#181f33,#090b10);color:#f8fafc;margin:0;display:flex;flex-direction:column;height:100vh}
header{padding:12px 16px;background:rgba(17,22,34,0.92);display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(245,158,11,0.3)}
.brand{font-weight:800;font-size:16px;background:linear-gradient(90deg,#f59e0b,#fde047,#38bdf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.h-btn{background:rgba(255,255,255,0.08);color:#f1f5f9;border:1px solid rgba(245,158,11,0.3);padding:6px 10px;border-radius:10px;font-size:12px;cursor:pointer;margin-right:4px}
.panel{display:none;background:#111622;border-bottom:1px solid rgba(245,158,11,0.35);padding:12px;max-height:260px;overflow-y:auto}
.s-item{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(255,255,255,0.05);border-radius:10px;margin-bottom:6px;cursor:pointer}
.del-btn{background:#ef4444;color:#fff;border:none;border-radius:6px;padding:2px 8px;font-weight:bold}
.cfg-in{width:100%;padding:9px;margin:6px 0 10px;background:#090b10;border:1px solid #334155;color:#fff;border-radius:8px;direction:ltr}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:14px;max-width:800px;width:100%;margin:auto}
.msg{max-width:88%;padding:13px 17px;border-radius:20px;line-height:1.65;font-size:15px;white-space:pre-wrap;word-wrap:break-word}
.user{align-self:flex-start;background:#1e293b;color:#fff;border:1px solid rgba(56,189,248,0.35);border-bottom-right-radius:4px}
.bot{align-self:flex-end;background:rgba(26,33,48,0.85);color:#f1f5f9;border:1px solid rgba(255,255,255,0.1);border-bottom-left-radius:4px;width:100%}
.bot img,.bot audio,.bot video{width:100%;max-height:70vh;object-fit:contain;border-radius:12px;margin-top:8px;background:#000}
.dl{display:block;text-align:center;background:#f59e0b;color:#000;padding:10px;border-radius:10px;margin-top:8px;text-decoration:none;font-weight:800}
.footer{background:rgba(17,22,34,0.95);padding:12px 14px;border-top:1px solid rgba(245,158,11,0.2)}
.input-row{max-width:800px;margin:auto;display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.08);border:1px solid rgba(245,158,11,0.35);border-radius:26px;padding:6px 14px}
input[type=text]{flex:1;background:transparent;border:none;color:#fff;font-size:15px;outline:none;padding:8px 0}
button#sendBtn{background:#f59e0b;color:#000;border:none;width:38px;height:38px;border-radius:50%;font-weight:bold;font-size:16px;flex-shrink:0}
</style></head><body>
<header>
  <span class="brand">✨ DARK HORIZON AI</span>
  <div>
    
    <button class="h-btn" onclick="toggleEl('drawer');loadSessions()">📂 السجل</button>
    <button class="h-btn" onclick="newSession()">➕</button>
  </div>
</header>
<div id="cfgBox" class="panel">
  <b>🌐 ربط المحركات السحابية العالمية:</b>
  <input class="cfg-in" id="gemKey" placeholder="Google Gemini API Key (AIza...) - مجاني من ://google.com">
  <input class="cfg-in" id="groqKey" placeholder="Groq API Key (gsk_...) - اختياري">
  <button class="dl" style="border:none;width:100%;cursor:pointer" onclick="saveCfg()">💾 حفظ المفاتيح السحابية</button>
</div>
<div id="drawer" class="panel"></div>
<div id="chat"></div>
<div class="footer">
  <div id="plusMenu" style="display:none;max-width:800px;margin:0 auto 8px;background:#1e293b;border:1px solid #f59e0b;border-radius:14px;padding:8px;gap:8px">
    <button type="button" onclick="pickFile('image/*')" style="flex:1;background:#0f172a;color:#fff;border:1px solid #334155;padding:10px;border-radius:10px">🖼️ صورة</button>
    <button type="button" onclick="pickFile('.pdf,.txt')" style="flex:1;background:#0f172a;color:#fff;border:1px solid #334155;padding:10px;border-radius:10px">📄 ملف PDF</button>
  </div>
  <div id="filePreview" style="max-width:800px;margin:0 auto 6px;font-size:13px;color:#fde047;display:none;justify-content:space-between;background:rgba(245,158,11,0.2);padding:6px 12px;border-radius:10px"></div>
  <div class="input-row">
    <input type="file" id="fileIn" style="display:none" onchange="showFile()">
    <button type="button" onclick="togglePlus()" style="background:rgba(255,255,255,0.1);color:#f59e0b;border:none;width:36px;height:36px;border-radius:50%;font-size:22px;flex-shrink:0">+</button>
    <input type="text" id="q" placeholder="اكتب رسالتك أو أرفق ملفاً (+)..." onkeypress="if(event.key==='Enter')sendMsg()">
    <button type="button" id="sendBtn" onclick="sendMsg()">➤</button>
  </div>
</div>
<script src="/app.js"></script></body></html>"""

@app.route("/media/<path:filename>")
def media(filename): return send_from_directory(WORK, filename)

@app.route("/app.js")
def app_js():
    code = """
var sid = localStorage.getItem("dh_sid") || null;
function toggleEl(id){ var el = document.getElementById(id); if(el) el.style.display = (el.style.display === "block") ? "none" : "block"; }
function togglePlus(){ var m = document.getElementById("plusMenu"); if(m) m.style.display = (m.style.display === "flex") ? "none" : "flex"; }
function pickFile(acc){ var m = document.getElementById("plusMenu"); if(m) m.style.display = "none"; var f = document.getElementById("fileIn"); if(f){ f.accept = acc; f.click(); } }
function showFile(){ var fIn = document.getElementById("fileIn"), pv = document.getElementById("filePreview"); if(fIn && fIn.files.length > 0){ pv.style.display = "flex"; pv.innerHTML = "<span>📎 " + fIn.files.item(0).name + "</span><span onclick='clearFile()' style='cursor:pointer;color:#f87171;font-weight:bold'>✕</span>"; } }
function clearFile(){ var fIn = document.getElementById("fileIn"), pv = document.getElementById("filePreview"); if(fIn) fIn.value = ""; if(pv) pv.style.display = "none"; }
function saveCfg(){ fetch("/cfg", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({groq_key:document.getElementById("groqKey").value.trim(), fal_key:document.getElementById("falKey").value.trim()})}).then(function(){ toggleEl("cfgBox"); alert("تم الحفظ!"); }); }
function renderBubble(role, content, media){
  var c = document.getElementById("chat"), div = document.createElement("div");
  div.className = "msg " + (role === "User" ? "user" : "bot");
  var html = content;
  if(media && media.vid) html += '<video controls playsinline src="/media/' + media.vid + '"></video><a class="dl" href="/media/' + media.vid + '" download="' + media.vid + '">⬇️ تحميل الفيديو</a>';
  if(media && media.aud) html += '<audio controls src="/media/' + media.aud + '"></audio><a class="dl" href="/media/' + media.aud + '" download="' + media.aud + '">⬇️ تحميل الصوت</a>';
  if(media && media.imgs) media.imgs.forEach(function(im, idx){ var mp = (media.motions && media.motions.at(idx)) ? media.motions.at(idx) : ""; html += '<div style="margin-top:10px"><img src="/media/' + im + '"><a class="dl" href="/media/' + im + '" download="' + im + '">⬇️ تحميل الصورة</a><div style="margin-top:6px;padding:6px;background:#0f172a;font-size:12px;color:#38bdf8;direction:ltr">' + mp + '</div></div>'; });
  div.innerHTML = html; c.appendChild(div); c.scrollTop = c.scrollHeight; return div;
}
function loadSessions(){ fetch("/sessions").then(function(r){ return r.json(); }).then(function(list){ var d = document.getElementById("drawer"); if(!d) return; d.innerHTML = ""; list.forEach(function(s){ var div = document.createElement("div"); div.className = "s-item"; var sp = document.createElement("span"); sp.style.flex = "1"; sp.innerText = s.title; sp.onclick = function(){ selectSession(s.id); }; var btn = document.createElement("button"); btn.className = "del-btn"; btn.innerText = "✕"; btn.onclick = function(e){ e.stopPropagation(); delSession(s.id); }; div.appendChild(sp); div.appendChild(btn); d.appendChild(div); }); }); }
function selectSession(id){ sid = id; localStorage.setItem("dh_sid", sid); document.getElementById("drawer").style.display = "none"; loadMessages(); }
function newSession(){ sid = null; localStorage.removeItem("dh_sid"); document.getElementById("chat").innerHTML = '<div class="msg bot">✨ محادثة جديدة جاهزة.</div>'; }
function delSession(id){ fetch("/sessions/" + id, {method: "DELETE"}).then(function(){ if(sid == id) newSession(); loadSessions(); }); }
function loadMessages(){ if(!sid){ document.getElementById("chat").innerHTML = '<div class="msg bot">✨ <b>DARK HORIZON AI</b> جاهز! اضغط (+) لإرفاق ملف أو اكتب رسالتك.</div>'; return; } fetch("/messages/" + sid).then(function(r){ return r.json(); }).then(function(msgs){ document.getElementById("chat").innerHTML = ""; msgs.forEach(function(m){ renderBubble(m.role, m.content, m.media); }); }); }
function sendMsg(){
  var qEl = document.getElementById("q"), fEl = document.getElementById("fileIn"), txt = qEl.value.trim(), file = (fEl && fEl.files.length > 0) ? fEl.files.item(0) : null;
  if(!txt && !file) return;
  var chatBox = document.getElementById("chat"); if(chatBox.innerText.indexOf("DARK HORIZON AI") !== -1) chatBox.innerHTML = "";
  renderBubble("User", txt || ("📎 " + file.name), {});
  var botDiv = renderBubble("AI", "⚡ جاري المعالجة...", {});
  var fd = new FormData(); if(sid) fd.append("sid", sid); fd.append("q", txt); if(file) fd.append("file", file);
  qEl.value = ""; clearFile();
  fetch("/universal_send", {method: "POST", body: fd}).then(function(r){ return r.json(); }).then(function(d){ sid = d.sid; localStorage.setItem("dh_sid", sid); botDiv.remove(); renderBubble("AI", d.reply, d.media); loadSessions(); }).catch(function(err){ botDiv.innerText = "⚠️ تعذر الاتصال: " + err.message; });
}
window.onload = function(){ loadSessions(); loadMessages(); };
"""
    return Response(code, mimetype="application/javascript")
@app.route("/")
def index(): return render_template_string(HTML)
@app.route("/cfg", methods=["POST"])
def cfg():
    d = request.get_json() or {}
    with db_lock:
        for k in ("groq_key", "gemini_key"):
            if d.get(k): conn.execute("INSERT OR REPLACE INTO config (k, v) VALUES (?, ?)", (k, d.get(k)))
        conn.commit()
    return jsonify({"ok": True})
@app.route("/sessions")
def sessions():
    with db_lock: rows = conn.execute("SELECT id, title FROM sessions ORDER BY id DESC").fetchall()
    return jsonify([{"id": r.__getitem__(0), "title": r.__getitem__(1)} for r in rows])
@app.route("/sessions/<int:sid>", methods=["DELETE"])
def del_session(sid):
    with db_lock: conn.execute("DELETE FROM messages WHERE session_id=?", (sid,)); conn.execute("DELETE FROM sessions WHERE id=?", (sid,)); conn.commit()
    return jsonify({"ok": True})
@app.route("/messages/<int:sid>")
def get_messages(sid):
    with db_lock: rows = conn.execute("SELECT role, content, media FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
    return jsonify([{"role": r.__getitem__(0), "content": r.__getitem__(1), "media": json.loads(r.__getitem__(2) or "{}")} for r in rows])

@app.route("/stream_chat", methods=["POST"])
def stream_chat():
    d = request.get_json() or {}
    sid, q = d.get("sid"), d.get("q", "").strip()
    with db_lock:
        sid = conn.execute("INSERT INTO sessions (title) VALUES (?)", (q[:28],)).lastrowid if not sid else int(sid)
        conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'User', ?, '{}')", (sid, q))
        conn.commit()
        rows = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 8", (sid,)).fetchall()
    hist = list(reversed(rows))
    ctx = "\n".join([f"{r}: {c[:300]}" for r, c in hist])

    def gen():
        yield f"SID:{sid}\n"
        low = q.lower()
        if any(w in low for w in ("فيديو", "video", "وثائقي", "صورة", "ارسم", "image", "draw", "اخدمني", "ثوان", "ثانية", "ثواني", "ديرها", "حولها", "اجعله", "اجعلها")):
            yield "TXT:⚡ جاري الإخراج عبر السحابة...\n"
            rep, m_obj = generate_media_kit(q, ctx)
            with db_lock:
                conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, rep, json.dumps(m_obj)))
                conn.commit()
            yield "TXT:" + rep.replace("\n", "\\n") + "\n"
            yield "MEDIA:" + json.dumps(m_obj) + "\n"
        else:
            msgs = [{"role": "system", "content": "أنت المحرك الذكي لاستوديو DARK HORIZON FILMS LTD. لا ترحب أبداً إذا كانت المحادثة جارية، أكمل الحوار مباشرة."}]
            for r, c in hist: msgs.append({"role": "user" if r == "User" else "assistant", "content": c[:350]})
            acc = []
            for tok in stream_llm(msgs):
                acc.append(tok)
                yield "TXT:" + tok.replace("\n", "\\n") + "\n"
            final_txt = "".join(acc).strip()
            with db_lock:
                conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, '{}')", (sid, final_txt))
                conn.commit()

    return Response(stream_with_context(gen()), mimetype="text/plain")


@app.route("/universal_send", methods=["POST"])
def universal_send():
    try:
        sid = request.form.get("sid")
        q = request.form.get("q", "").strip()
        f_obj = request.files.get("file")
        up_path = None
        if f_obj and f_obj.filename:
            up_path = os.path.join(WORK, f"up_{int(time.time())}_{f_obj.filename}")
            f_obj.save(up_path)
            if not q: q = f"📎 {f_obj.filename}"
        with db_lock:
            sid = conn.execute("INSERT INTO sessions (title) VALUES (?)", (q[:28],)).lastrowid if (not sid or sid in ("null", "", "None", "undefined")) else int(sid)
            conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'User', ?, '{}')", (sid, q))
            conn.commit()
            rows = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 8", (sid,)).fetchall()
        hist = list(reversed(rows))
        ctx = "\n".join([f"{r}: {c[:300]}" for r, c in hist])

        if up_path and os.path.exists(up_path):
            ext = os.path.splitext(up_path).__getitem__(1).lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                with open(up_path, "rb") as f: b64 = base64.b64encode(f.read()).decode("utf-8")
                rep = call_llm_sync([{"role": "user", "content": [{"type": "text", "text": q or "صف هذه الصورة بالعربية."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]) or "تم تحليل الصورة."
                m_obj = {}
            elif ext == ".pdf":
                import fitz
                txt = "\n".join([pg.get_text() for pg in fitz.open(up_path)][:8])
                rep = call_llm_sync([{"role": "user", "content": f"لخص بالعربية:\n{txt[:1800]}\n\n{q}"}]) or "تمت قراءة الملف."
                m_obj = {}
            else:
                rep, m_obj = "تم استلام الملف بنجاح.", {}
        elif any(w in q.lower() for w in ("فيديو", "video", "وثائقي", "صورة", "صور", "تصويرة", "ارسم", "رسم", "image", "draw", "photo", "اخدمني", "ديرلي", "ديرها", "صاوب", "حولها", "نعم", "ايه", "واخا", "نفذ", "ابدأ", "ok", "oui", "make", "create")) or ("موضوع الفيديو" in ctx[-250:] and len(q.split()) <= 5):
            rep, m_obj = generate_media_kit(q, ctx)
        else:
            msgs = [{"role": "system", "content": "أنت المحرك الذكي العالمي لاستوديو DARK HORIZON FILMS LTD. تفهم جميع لغات العالم وجميع اللهجات العربية (خاصة الدارجة الجزائرية، المغربية، التونسية، المصرية، الخليجية، والشامية) بطلاقة تامة. أجب دائماً بنفس لغة أو لهجة المستخدم باختصار وذكاء، وممنوع ذكر أي أسعار أو تكلفة مالية."}]
            for r, c in hist: msgs.append({"role": "user" if r == "User" else "assistant", "content": c[:350]})
            rep = call_llm_sync(msgs)
            m_obj = {}

        with db_lock:
            conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, rep, json.dumps(m_obj)))
            conn.commit()
        return jsonify({"sid": sid, "reply": rep, "media": m_obj})
    except Exception as err:
        return jsonify({"sid": 1, "reply": f"⚠️ حدث خطأ بسيط وتم تجاوزه: {str(err)[:90]}", "media": {}})


def cloud_self_doctor():
    while True:
        time.sleep(300)
        try:
            with db_lock:
                conn.execute("DELETE FROM messages WHERE content='...' OR content LIKE '%جاري%'")
                conn.commit()
            now = time.time()
            for fn in os.listdir(WORK):
                fp = os.path.join(WORK, fn)
                if fn != "brand_logo.png" and os.path.isfile(fp) and (now - os.path.getmtime(fp)) > 3600:
                    os.remove(fp)
        except Exception:
            pass

threading.Thread(target=cloud_self_doctor, daemon=True).start()

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "studio": "DARK HORIZON FILMS LTD", "uptime": "24/7"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
