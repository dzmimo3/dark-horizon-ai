import os, re, json, time, random, shutil, sqlite3, asyncio, threading, subprocess, urllib.parse, requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template_string, send_from_directory, Response, stream_with_context
import edge_tts

app = Flask(__name__)
WORK = "/tmp/omni_work"
DB_PATH = "/tmp/omni_sessions.db"
os.makedirs(WORK, exist_ok=True)
if os.path.exists("brand_logo.png"):
    shutil.copy2("brand_logo.png", os.path.join(WORK, "brand_logo.png"))

db_lock = threading.Lock()
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, content TEXT, media TEXT)")
conn.commit()

def get_keys(prefix):
    out = []
    for k in (prefix, f"{prefix}_1", f"{prefix}_2", f"{prefix}_3"):
        v = os.environ.get(k, "").strip()
        if v and v not in out: out.append(v)
    return out

def stream_groq(messages):
    url = "https://" + "://groq.com"
    for k in get_keys("GROQ_API_KEY"):
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"}, json={"model": "llama-3.3-70b-versatile", "messages": messages, "stream": True}, stream=True, timeout=20)
            if r.status_code == 200:
                for line in r.iter_lines():
                    if line:
                        s = line.decode("utf-8")
                        if s.startswith("data: ") and "[DONE]" not in s:
                            delta = json.loads(s[6:]).get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta: yield delta
                return
        except Exception:
            continue
    try:
        sl = chr(47)
        q_last = str(messages[-1].get("content", ""))[:300]
        r2 = requests.get(f"https:{sl}{sl}text.pollinations.ai{sl}" + urllib.parse.quote(q_last), params={"seed": random.randint(1, 99999)}, timeout=12)
        if r2.status_code == 200 and "Free limit" not in r2.text and "404" not in r2.text:
            yield r2.text.strip()
            return
    except Exception:
        pass
    yield "أهلاً بك في استوديو DARK HORIZON FILMS LTD! كيف يمكنني مساعدتك اليوم؟"

def ask_groq_sync(messages):
    return "".join(list(stream_groq(messages)))

def build_image(en_prompt):
    seed = random.randint(10000, 9999999)
    full_p = f"{en_prompt}, ARRI Alexa 65, 85mm anamorphic lens, hyperrealistic, volumetric lighting, 8k"
    fn = f"OMNI_{int(time.time())}_{seed}.jpg"
    fpath = os.path.join(WORK, fn)
    img_bytes = b""

    hf_url = "https://" + "router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    for hft in get_keys("HF_TOKEN"):
        try:
            hr = requests.post(hf_url, headers={"Authorization": f"Bearer {hft}"}, json={"inputs": full_p[:250]}, timeout=25)
            if hr.status_code == 200 and len(hr.content) > 5000:
                img_bytes = hr.content
                break
        except Exception:
            continue

    if not img_bytes:
        p_url = "https://" + "image.pollinations.ai/prompt/" + urllib.parse.quote(full_p[:220]) + f"?width=540&height=960&nologo=true&model=flux&seed={seed}"
        try: img_bytes = requests.get(p_url, timeout=25).content
        except Exception: pass

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
    en_p = ask_groq_sync([{"role": "system", "content": "Output ONLY an 18-word ultra-realistic English visual prompt. No intro."}, {"role": "user", "content": ctx_q}])
    if not en_p or "⚠️" in en_p: en_p = "cinematic Arabian desert warrior at golden sunset, 8k"

    if is_vid:
        seed = random.randint(10000, 999999)
        script = ask_groq_sync([{"role": "system", "content": "اكتب تعليقاً صوتياً وثائقياً مؤثراً من 3 جمل بالعربية الفصحى بدون رموز."}, {"role": "user", "content": ctx_q}])
        if not script or "⚠️" in script: script = "في عمق التاريخ والحياة، تتجلى أروع المشاهد السينمائية الخالدة."
        aud_p = os.path.join(WORK, f"Voice_{seed}.mp3")
        try: asyncio.run(make_voice(script, aud_p))
        except Exception: pass
        has_aud = os.path.exists(aud_p) and os.path.getsize(aud_p) > 1500
        num_sc = 2
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
    m_cnt = re.search(r"(\d+)\s*(?:صور|صورة|images?)", q, re.I)
    count = max(1, min(10, int(m_cnt.group(1)))) if m_cnt else (10 if any(w in low for w in ("صور", "عشر", "10", "معرض", "تشكيلة")) else 1)
    if count > 1:
        angles = [f"{en_p}, cinematic angle {i+1}, dramatic lighting" for i in range(count)]
        with ThreadPoolExecutor(max_workers=4) as ex:
            fns = list(ex.map(build_image, angles))
        return f"🎨 <b>تم تصميم {len(fns)} صور سينمائية (DARK HORIZON FILMS LTD):</b>", {"imgs": fns}
    return "🎨 <b>تم تصميم الصورة بدقة سينمائية:</b>", {"imgs": [build_image(en_p)]}

HTML = """<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>DARK HORIZON AI</title><style>
*{box-sizing:border-box;font-family:system-ui,sans-serif}body{background:#090b10;color:#f8fafc;margin:0;display:flex;flex-direction:column;height:100vh}
header{padding:12px 16px;background:#111622;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(245,158,11,0.3)}
.brand{font-weight:800;font-size:16px;color:#f59e0b}
.h-btn{background:rgba(255,255,255,0.08);color:#fff;border:1px solid rgba(245,158,11,0.3);padding:8px 12px;border-radius:10px;font-size:13px;cursor:pointer}
#drawer{display:none;background:#111622;padding:12px;max-height:220px;overflow-y:auto;border-bottom:1px solid #f59e0b}
.s-item{display:flex;justify-content:space-between;align-items:center;padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;margin-bottom:6px}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;max-width:800px;width:100%;margin:auto}
.msg{max-width:88%;padding:12px 16px;border-radius:18px;line-height:1.6;font-size:15px;white-space:pre-wrap}
.user{align-self:flex-start;background:#1e293b;border:1px solid #38bdf8}
.bot{align-self:flex-end;background:#1a2130;border:1px solid rgba(255,255,255,0.1);width:100%}
.bot video{width:100%;max-height:65vh;object-fit:contain;border-radius:12px;margin-top:8px;background:#000}
.img-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px}
.img-card{background:#0f172a;border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:6px;display:flex;flex-direction:column}
.img-card img{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:8px}
.dl-sm{text-align:center;background:rgba(245,158,11,0.2);color:#fde047;padding:6px;border-radius:8px;margin-top:6px;text-decoration:none;font-size:12px;font-weight:700}
.dl{display:block;text-align:center;background:#f59e0b;color:#000;padding:10px;border-radius:10px;margin-top:8px;text-decoration:none;font-weight:800}
.footer{background:#111622;padding:12px;border-top:1px solid rgba(245,158,11,0.2)}
.input-row{max-width:800px;margin:auto;display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.08);border:1px solid #f59e0b;border-radius:26px;padding:6px 12px}
input[type=text]{flex:1;background:transparent;border:none;color:#fff;font-size:15px;outline:none;padding:6px}
.c-btn{border:none;width:40px;height:40px;border-radius:50%;font-weight:bold;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
#plusBtn{background:rgba(255,255,255,0.12);color:#f59e0b}
#sendBtn{background:#f59e0b;color:#000}
</style></head><body>
<header><span class="brand">✨ DARK HORIZON AI</span><div><button type="button" id="histBtn" class="h-btn">📂 السجل</button> <button type="button" id="newBtn" class="h-btn">➕ جديد</button></div></header>
<div id="drawer"></div><div id="chat"></div>
<div class="footer"><div id="fileBar" style="display:none;max-width:800px;margin:0 auto 8px;background:rgba(245,158,11,0.2);color:#fde047;padding:6px 12px;border-radius:10px;font-size:13px;justify-content:space-between"></div>
<div class="input-row"><input type="file" id="fileIn" accept="image/*,.pdf,.txt" style="display:none"><button type="button" id="plusBtn" class="c-btn">+</button><input type="text" id="q" placeholder="تحدث، أرفق ملفاً، اطلب صورة أو فيديو..."><button type="button" id="sendBtn" class="c-btn">➤</button></div></div>
<script src="/ui_logic.js"></script></body></html>"""

@app.route("/ui_logic.js")
def ui_logic():
    code = """
var sid = localStorage.getItem("dh_sid") || null;
function dlAllImgs(enc){
  var arr = JSON.parse(decodeURIComponent(enc));
  arr.forEach(function(fn, idx){
    setTimeout(function(){
      var a = document.createElement("a");
      a.href = "/media/" + fn;
      a.download = fn;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }, idx * 450);
  });
}
function addBubble(role, content, media){
  var chat = document.getElementById("chat"), d = document.createElement("div");
  d.className = "msg " + (role === "User" ? "user" : "bot");
  var h = content;
  if(media && media.vid) h += '<video controls playsinline src="/media/' + media.vid + '"></video><a class="dl" href="/media/' + media.vid + '" download="' + media.vid + '">⬇️ تحميل الفيديو</a>';
  if(media && media.imgs) media.imgs.forEach(function(im){ h += '<img src="/media/' + im + '"><a class="dl" href="/media/' + im + '" download="' + im + '">⬇️ تحميل الصورة</a>'; });
  d.innerHTML = h; chat.appendChild(d); chat.scrollTop = chat.scrollHeight; return d;
}
function loadSessions(){
  fetch("/sessions").then(function(r){ return r.json(); }).then(function(list){
    var dr = document.getElementById("drawer"); dr.innerHTML = "";
    list.forEach(function(s){
      var row = document.createElement("div"); row.className = "s-item";
      var sp = document.createElement("span"); sp.style.flex = "1"; sp.style.cursor = "pointer"; sp.textContent = s.title;
      sp.addEventListener("click", function(){ sid = s.id; localStorage.setItem("dh_sid", sid); dr.style.display = "none"; loadMessages(); });
      var del = document.createElement("button"); del.textContent = "✕"; del.style.cssText = "background:none;border:none;color:#ef4444;font-size:16px";
      del.addEventListener("click", function(){ fetch("/sessions/" + s.id, {method: "DELETE"}).then(function(){ if(sid == s.id) startNew(); loadSessions(); }); });
      row.appendChild(sp); row.appendChild(del); dr.appendChild(row);
    });
  });
}
function startNew(){ sid = null; localStorage.removeItem("dh_sid"); document.getElementById("chat").innerHTML = '<div class="msg bot">✨ محادثة جديدة جاهزة!</div>'; }
function loadMessages(){ if(!sid){ startNew(); return; } fetch("/messages/" + sid).then(function(r){ return r.json(); }).then(function(msgs){ var chat = document.getElementById("chat"); chat.innerHTML = ""; msgs.forEach(function(m){ addBubble(m.role, m.content, m.media); }); }); }
function sendMessage(){
  var qEl = document.getElementById("q"), fEl = document.getElementById("fileIn"), txt = qEl.value.trim();
  var file = (fEl.files && fEl.files.length > 0) ? fEl.files.item(0) : null;
  if(!txt && !file) return;
  addBubble("User", txt || ("📎 " + file.name), {});
  var waitBox = addBubble("AI", "⚡ جاري التنفيذ...", {});
  var fd = new FormData(); if(sid) fd.append("sid", sid); fd.append("q", txt); if(file) fd.append("file", file);
  qEl.value = ""; fEl.value = ""; document.getElementById("fileBar").style.display = "none";
  fetch("/send_all", {method: "POST", body: fd})
    .then(function(r){ return r.json(); })
    .then(function(d){
      sid = d.sid; localStorage.setItem("dh_sid", sid);
      if(d.job_id){
        waitBox.textContent = "🎬 جاري إخراج الفيديو والمونتاج (انتظر 25 ثانية)...";
        var iv = setInterval(function(){
          fetch("/job/" + d.job_id).then(function(r2){ return r2.json(); }).then(function(st){
            if(st.done){ clearInterval(iv); waitBox.remove(); addBubble("AI", st.reply, st.media); loadSessions(); }
          });
        }, 3000);
      } else {
        waitBox.remove(); addBubble("AI", d.reply, d.media); loadSessions();
      }
    })
    .catch(function(err){ waitBox.textContent = "⚠️ تعذر الاتصال: " + err.message; });
}
document.addEventListener("DOMContentLoaded", function(){
  document.getElementById("histBtn").addEventListener("click", function(){ var dr = document.getElementById("drawer"); dr.style.display = (dr.style.display === "block") ? "none" : "block"; loadSessions(); });
  document.getElementById("newBtn").addEventListener("click", startNew);
  document.getElementById("plusBtn").addEventListener("click", function(){ document.getElementById("fileIn").click(); });
  document.getElementById("fileIn").addEventListener("change", function(){ var fEl = document.getElementById("fileIn"), fb = document.getElementById("fileBar"); if(fEl.files && fEl.files.length > 0){ fb.style.display = "flex"; fb.innerHTML = "<span>📎 " + fEl.files.item(0).name + "</span><span id='clrF' style='color:#ef4444;font-weight:bold;cursor:pointer'>✕</span>"; document.getElementById("clrF").addEventListener("click", function(){ fEl.value = ""; fb.style.display = "none"; }); } });
  document.getElementById("sendBtn").addEventListener("click", sendMessage);
  document.getElementById("q").addEventListener("keydown", function(e){ if(e.key === "Enter"){ e.preventDefault(); sendMessage(); } });
  loadSessions(); loadMessages();
});
"""
    return Response(code, mimetype="application/javascript")

@app.route("/media/<path:fn>")
def media(fn): return send_from_directory(WORK, fn)
@app.route("/")
def index(): return render_template_string(HTML)
@app.route("/health")
def health(): return jsonify({"status": "ok"})
@app.route("/sessions")
def sessions():
    with db_lock: rows = conn.execute("SELECT id, title FROM sessions ORDER BY id DESC").fetchall()
    return jsonify([{"id": r[0], "title": r[1]} for r in rows])

@app.route("/sessions/<int:sid>", methods=["DELETE"])
def del_s(sid):
    with db_lock: conn.execute("DELETE FROM messages WHERE session_id=?", (sid,)); conn.execute("DELETE FROM sessions WHERE id=?", (sid,)); conn.commit()
    return jsonify({"ok": True})

@app.route("/messages/<int:sid>")
def get_m(sid):
    with db_lock: rows = conn.execute("SELECT role, content, media FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
    return jsonify([{"role": r[0], "content": r[1], "media": json.loads(r[2] or "{}")} for r in rows])


JOBS = {}

def run_video_job(jid, sid, q, ctx):
    try:
        rep, m_obj = generate_media(q, ctx)
        with db_lock:
            conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, rep, json.dumps(m_obj)))
            conn.commit()
        JOBS[jid] = {"done": True, "reply": rep, "media": m_obj}
    except Exception as e:
        JOBS[jid] = {"done": True, "reply": f"⚠️ خطأ أثناء المونتاج: {str(e)[:80]}", "media": {}}

@app.route("/job/<jid>")
def check_job(jid):
    return jsonify(JOBS.get(jid, {"done": False}))

@app.route("/send_all", methods=["POST"])
def send_all():
    sid, q, f_obj, up_path = request.form.get("sid"), request.form.get("q", "").strip(), request.files.get("file"), None
    if f_obj and f_obj.filename:
        up_path = os.path.join(WORK, f"up_{int(time.time())}_{f_obj.filename}"); f_obj.save(up_path)
        if not q: q = f"📎 {f_obj.filename}"
    with db_lock:
        sid = conn.execute("INSERT INTO sessions (title) VALUES (?)", (q[:28],)).lastrowid if (not sid or sid in ("null", "undefined", "")) else int(sid)
        conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'User', ?, '{}')", (sid, q)); conn.commit()
        rows = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 8", (sid,)).fetchall()
    hist = list(reversed(rows))
    ctx = "\n".join([f"{r[0]}: {r[1][:250]}" for r in hist])
    if up_path and os.path.exists(up_path):
        import base64
        ext = os.path.splitext(up_path)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            b64 = base64.b64encode(open(up_path, "rb").read()).decode("utf-8")
            vis_msg = [{"role": "user", "content": [{"type": "text", "text": q or "صف هذه الصورة بالتفصيل بالعربية."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
            url_g = "https://" + "://groq.com"
            rep = ""
            for k in get_keys("GROQ_API_KEY"):
                try:
                    rv = requests.post(url_g, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"}, json={"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": vis_msg}, timeout=20)
                    if rv.status_code == 200:
                        rep = rv.json()["choices"][0]["message"]["content"].strip()
                        break
                except Exception: continue
            if not rep: rep = "تم استلام الصورة بنجاح."
        else:
            rep = ask_groq_sync([{"role": "user", "content": f"تم إرفاق ملف باسم {os.path.basename(up_path)}. {q}"}]) or "تم استلام الملف."
        m_obj = {}
    elif any(w in q.lower() for w in ("فيديو", "video", "وثائقي", "فيلم", "ثوان", "ثانية")):
        jid = f"j_{int(time.time())}_{random.randint(100,999)}"
        JOBS[jid] = {"done": False}
        threading.Thread(target=run_video_job, args=(jid, sid, q, ctx), daemon=True).start()
        return jsonify({"sid": sid, "job_id": jid})
    elif any(w in q.lower() for w in ("صورة", "صور", "ارسم", "image", "draw", "عشر")):
        jid = f"j_{int(time.time())}_{random.randint(100,999)}"
        with db_lock:
            conn.execute("INSERT INTO jobs (jid, done, reply, media) VALUES (?, 0, '', '{}')", (jid,))
            conn.commit()
        threading.Thread(target=run_video_job, args=(jid, sid, q, ctx), daemon=True).start()
        return jsonify({"sid": sid, "job_id": jid})
    else:
        msgs = [{"role": "system", "content": "أنت المساعد الذكي لاستوديو DARK HORIZON FILMS LTD. تفهم جميع اللهجات واللغات وترد بذكاء وسرعة مثل ChatGPT."}]
        for r in hist: msgs.append({"role": "user" if r[0] == "User" else "assistant", "content": r[1][:400]})
        rep = ask_groq_sync(msgs) or "أهلاً بك في استوديو DARK HORIZON FILMS LTD! كيف يمكنني مساعدتك اليوم؟"
        m_obj = {}
    with db_lock: conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, rep, json.dumps(m_obj))); conn.commit()
    return jsonify({"sid": sid, "reply": rep, "media": m_obj})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
