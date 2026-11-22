from concurrent.futures import ThreadPoolExecutor, as_completed
import os, io, json, time, base64, random, urllib.parse, sqlite3, threading, subprocess, requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
db_lock = threading.Lock()
DB_PATH = "/tmp/dh_v6.db"
MEDIA_DIR = "/tmp/dh_media"
os.makedirs(MEDIA_DIR, exist_ok=True)

def first(seq, default=None):
    return next(iter(seq), default) if isinstance(seq, (list, tuple)) else default

def init_db():
    with db_lock:
        c = sqlite3.connect(DB_PATH)
        c.execute("CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT, content TEXT, media TEXT)")
        c.commit(); c.close()
init_db()

def get_key(name):
    val = os.environ.get(name, "").strip()
    return first([x.strip() for x in val.split(",") if x.strip()], "")

def search_web(q):
    tv = get_key("TAVILY_API_KEY")
    if not tv: return ""
    try:
        r = requests.post("https://tavily.com", json={"api_key": tv, "query": q, "include_answer": True, "max_results": 3}, timeout=4)
        if r.status_code == 200:
            d = r.json()
            res = [d["answer"]] if d.get("answer") else []
            for it in d.get("results", [])[:2]:
                res.append(f"- {it.get('title','')}: {it.get('content','')[:160]}")
            return "\n".join(res)
    except Exception: pass
    return ""

def ai_brain(messages, img_b64=None):
    sys_msg = (
        "أنت مساعد ذكاء اصطناعي خبير تتحدث بأسلوب طبيعي، ذكي، ومباشر تماماً مثل ChatGPT و Gemini. "
        "أجب بوضوح وعمق وتفاعل مع كلام المستخدم وسياق المحادثة بدون أي عبارات ترحيبية مكررة."
    )
    clean = [{"role": ("assistant" if m.get("role") == "AI" else "user"), "content": str(m.get("content", ""))} for m in messages if m.get("content")]
    if not clean: clean = [{"role": "user", "content": "مرحباً"}]
    errors = []

    # 1. Google Gemini 2.5 Flash
    gk = get_key("GEMINI_API_KEY")
    if gk:
        try:
            g_contents = []
            for idx, m in enumerate(clean[-6:]):
                parts = [{"text": m["content"]}]
                if img_b64 and idx == len(clean[-6:]) - 1 and m["role"] == "user":
                    raw_b64 = img_b64.split(",", 1).pop() if "," in img_b64 else img_b64
                    parts.append({"inlineData": {"mimeType": "image/jpeg", "data": raw_b64}})
                g_contents.append({"role": ("model" if m["role"] == "assistant" else "user"), "parts": parts})
            r = requests.post(f"https://googleapis.com{gk}",
                              json={"systemInstruction": {"parts": [{"text": sys_msg}]}, "contents": g_contents}, timeout=12)
            if r.status_code == 200:
                c0 = first(r.json().get("candidates", []), {})
                txt = first(c0.get("content", {}).get("parts", []), {}).get("text", "").strip()
                if txt: return txt
            else:
                errors.append(f"Gemini:{r.status_code}")
        except Exception as e:
            errors.append("Gemini:Err")

    # 2. Groq Llama 3.3 70B
    gq = get_key("GROQ_API_KEY")
    if gq:
        try:
            r = requests.post("https://groq.com",
                              headers={"Authorization": f"Bearer {gq}", "Content-Type": "application/json"},
                              json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_msg}] + clean[-6:]}, timeout=10)
            if r.status_code == 200:
                txt = first(r.json().get("choices", []), {}).get("message", {}).get("content", "").strip()
                if txt: return txt
            else:
                errors.append(f"Groq:{r.status_code}")
        except Exception:
            errors.append("Groq:Err")

    # 3. OpenRouter Free
    ork = get_key("OPENROUTER_API_KEY")
    if ork:
        try:
            r = requests.post("https://openrouter.ai",
                              headers={"Authorization": f"Bearer {ork}", "Content-Type": "application/json"},
                              json={"model": "openrouter/free", "messages": [{"role": "system", "content": sys_msg}] + clean[-6:]}, timeout=12)
            if r.status_code == 200:
                txt = first(r.json().get("choices", []), {}).get("message", {}).get("content", "").strip()
                if txt: return txt
            else:
                errors.append(f"OpenRouter:{r.status_code}")
        except Exception:
            errors.append("OpenRouter:Err")

    # 4. Pollinations AI
    pk = get_key("POLLINATIONS_API_KEY")
    if pk:
        try:
            r = requests.post("https://pollinations.ai",
                              headers={"Authorization": f"Bearer {pk}", "Content-Type": "application/json"},
                              json={"model": "openai", "messages": [{"role": "system", "content": sys_msg}] + clean[-6:]}, timeout=12)
            if r.status_code == 200:
                txt = first(r.json().get("choices", []), {}).get("message", {}).get("content", "").strip()
                if txt: return txt
            else:
                errors.append(f"Poll:{r.status_code}")
        except Exception:
            errors.append("Poll:Err")

    # 5. Cloudflare Workers AI
    cf_id, cf_tok = get_key("CF_ACCOUNT_ID"), get_key("CF_API_TOKEN")
    if cf_id and cf_tok:
        try:
            r = requests.post(f"https://cloudflare.com{cf_id}/ai/run/@cf/meta/llama-3.1-8b-instruct",
                              headers={"Authorization": f"Bearer {cf_tok}"},
                              json={"messages": [{"role": "system", "content": sys_msg}] + clean[-4:]}, timeout=12)
            if r.status_code == 200:
                txt = r.json().get("result", {}).get("response", "").strip()
                if txt: return txt
            else:
                errors.append(f"CF:{r.status_code}")
        except Exception:
            errors.append("CF:Err")

    err_info = " | ".join(errors) if errors else "لا توجد مفاتيح مفعّلة في Render"
    return f"⚠️ تعذر الاتصال بالخوادم حالياً ({err_info})."

def create_image(prompt):
    clean_q = prompt.strip()
    if len(clean_q) < 10 or clean_q in ("صور", "صورة", "ارسم"):
        en_p = "majestic Arabian horse galloping across golden desert dunes at sunset, ultra realistic 8k DSLR photography, natural lighting"
    else:
        en_p = ai_brain([{"role": "user", "content": f"Translate into a modest, ultra-realistic 8K English photography prompt (ONLY English words, no intro): {clean_q}"}])
        if not en_p or en_p.startswith("⚠️"):
            en_p = "cinematic ultra realistic 8k landscape photography, golden hour lighting, sharp focus"

    fn = f"dh_img_{int(time.time())}.jpg"
    fpath = os.path.join(MEDIA_DIR, fn)

    # 1. Cloudflare FLUX.1 (10,000 طلب/يوم)
    cf_id, cf_tok = get_key("CF_ACCOUNT_ID"), get_key("CF_API_TOKEN")
    if cf_id and cf_tok:
        try:
            r = requests.post(f"https://cloudflare.com{cf_id}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                              headers={"Authorization": f"Bearer {cf_tok}"}, json={"prompt": en_p[:240], "num_steps": 6}, timeout=25)
            if r.status_code == 200 and r.json().get("result", {}).get("image"):
                b64 = r.json()["result"]["image"]
                open(fpath, "wb").write(base64.b64decode(b64))
                return f"data:image/jpeg;base64,{b64}"
        except Exception: pass

    # 2. Pollinations Official Gateway
    pk = get_key("POLLINATIONS_API_KEY")
    if pk:
        try:
            r = requests.get(f"https://pollinations.ai{urllib.parse.quote(en_p[:220])}?width=1024&height=1024&model=flux&nologo=true&seed={random.randint(1,999999)}",
                             headers={"Authorization": f"Bearer {pk}"}, timeout=28)
            if r.status_code == 200 and len(r.content) > 3000:
                open(fpath, "wb").write(r.content)
                return "data:image/jpeg;base64," + base64.b64encode(r.content).decode("utf-8")
        except Exception: pass

    # 3. Google Imagen 3
    gk = get_key("GEMINI_API_KEY")
    if gk:
        try:
            r = requests.post(f"https://googleapis.com{gk}",
                              json={"instances": [{"prompt": en_p[:260]}], "parameters": {"sampleCount": 1}}, timeout=25)
            if r.status_code == 200:
                b64 = first(r.json().get("predictions", []), {}).get("bytesBase64Encoded")
                if b64:
                    open(fpath, "wb").write(base64.b64decode(b64))
                    return f"data:image/jpeg;base64,{b64}"
        except Exception: pass

    return None

def create_video(prompt, attached_img_b64=None):
    fn = f"dh_vid_{int(time.time())}.mp4"
    fpath = os.path.join(MEDIA_DIR, fn)
    img_path = None
    if attached_img_b64 and "," in attached_img_b64:
        img_path = os.path.join(MEDIA_DIR, f"up_{int(time.time())}.jpg")
        open(img_path, "wb").write(base64.b64decode(attached_img_b64.split(",", 1).pop()))
    else:
        create_image(prompt)
        imgs = sorted([f for f in os.listdir(MEDIA_DIR) if f.startswith("dh_img_")])
        if imgs: img_path = os.path.join(MEDIA_DIR, imgs.pop())
    if img_path and os.path.exists(img_path):
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-vf", "scale=1280:720,zoompan=z='min(zoom+0.0015,1.25)':d=125:s=1280x720", "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p", fpath]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 4000:
            return "data:video/mp4;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
    return None

HTML_UI = """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DARK HORIZON AI</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top,#181b22 0%,#0b0c0e 100%);color:#f1f3f4;font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;height:100vh}
header{padding:14px 18px;background:rgba(20,22,27,0.88);backdrop-filter:blur(12px);display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.08)}
.brand{font-weight:800;font-size:16px;background:linear-gradient(90deg,#a8c7fa,#d2e3fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.top-btn{background:rgba(255,255,255,0.06);color:#e3e3e3;border:1px solid rgba(255,255,255,0.12);border-radius:20px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer}
#chat{flex:1;overflow-y:auto;padding:18px 14px;display:flex;flex-direction:column;gap:14px}
.msg{max-width:86%;padding:13px 17px;border-radius:20px;line-height:1.65;font-size:15px;word-wrap:break-word;box-shadow:0 4px 16px rgba(0,0,0,0.25)}
.USER{align-self:flex-start;background:linear-gradient(135deg,#262932,#1e2028);border:1px solid rgba(255,255,255,0.08);border-bottom-right-radius:6px}
.AI{align-self:flex-end;background:rgba(24,26,32,0.92);border:1px solid rgba(168,199,250,0.14);border-bottom-left-radius:6px;width:92%}
.dock{position:relative;padding:10px 14px 16px;background:linear-gradient(to top,#0b0c0e 75%,transparent)}
.plus-menu{display:none;position:absolute;bottom:76px;right:16px;background:#1c1f26;border:1px solid rgba(168,199,250,0.22);border-radius:18px;padding:8px;width:245px;box-shadow:0 12px 32px rgba(0,0,0,0.6);z-index:50;flex-direction:column;gap:4px}
.plus-menu.show{display:flex}
.pm-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:12px;background:transparent;border:none;color:#f1f3f4;font-size:14px;cursor:pointer;text-align:right;width:100%}
.pm-item:hover,.pm-item:active{background:rgba(168,199,250,0.15)}
#preview-bar{display:none;align-items:center;gap:10px;background:#1c1f26;padding:8px 14px;border-radius:16px;margin-bottom:8px;border:1px solid rgba(168,199,250,0.25);font-size:13px}
.bar{display:flex;align-items:center;gap:8px;background:#181a20;border:1px solid rgba(255,255,255,0.14);border-radius:30px;padding:6px 10px 6px 6px;box-shadow:0 8px 28px rgba(0,0,0,0.45)}
.plus{width:38px;height:38px;border-radius:50%;border:none;background:rgba(168,199,250,0.14);color:#a8c7fa;font-size:22px;cursor:pointer;display:flex;align-items:center;justify-content:center;font-weight:bold}
input[type=text]{flex:1;background:transparent;border:none;color:#fff;font-size:15px;padding:8px 6px;outline:none}
.send{width:42px;height:42px;border-radius:50%;border:none;background:linear-gradient(135deg,#a8c7fa,#669df6);color:#041e49;font-size:17px;font-weight:bold;cursor:pointer;display:flex;align-items:center;justify-content:center}
img,video{max-width:100%;border-radius:14px;margin-top:12px;display:block}
.actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.act{background:rgba(168,199,250,0.12);color:#a8c7fa;border:1px solid rgba(168,199,250,0.25);padding:6px 13px;border-radius:14px;text-decoration:none;font-size:12px;font-weight:600;cursor:pointer}
</style></head>
<body>
<header><div class="brand">✦ DARK HORIZON AI</div><button class="top-btn" onclick="sid=null;document.getElementById('chat').innerHTML=''">+ محادثة جديدة</button></header>
<div id="chat"></div>
<div class="dock">
  <div id="plusMenu" class="plus-menu">
    <button class="pm-item" onclick="pickFile('image/*','img')">🖼️ إضافة صورة (تحليل أو تحويل لفيديو)</button>
    <button class="pm-item" onclick="pickFile('video/*','vid')">🎬 إضافة فيديو للمعالجة</button>
    <button class="pm-item" onclick="pickFile('.txt,.pdf,.py,.json,.csv,.md','doc')">📄 إضافة ملف ومستندات</button>
    <button class="pm-item" onclick="quickPrompt('صمم لي صورة سينمائية فائقة الواقعية بدقة 8K لـ ')">🎨 توليد صورة 8K فورية</button>
    <button class="pm-item" onclick="quickPrompt('اصنع لي فيديو سينمائي متحرك لـ ')">🎥 إنتاج فيديو بالذكاء الاصطناعي</button>
    <button class="pm-item" onclick="quickPrompt('ابحث في الويب عن أحدث المعلومات حول ')">🌐 بحث عميق في الإنترنت</button>
  </div>
  <div id="preview-bar"><span id="prev-name">📎 مرفق جاهز</span><button onclick="clearAttach()" style="margin-right:auto;background:none;border:none;color:#f28b82;cursor:pointer;font-weight:bold">✖ إلغاء</button></div>
  <input type="file" id="fileInp" style="display:none" onchange="handleFile(this)">
  <div class="bar">
    <button class="plus" onclick="toggleMenu()" title="إضافة وسائط وأدوات">+</button>
    <input type="text" id="q" placeholder="اسأل، أو اطلب تصميم صورة أو فيديو..." onkeydown="if(event.key==='Enter')send()">
    <button class="send" onclick="send()">➤</button>
  </div>
</div>
<script>
let sid=null, attData=null, attType=null, attName='';
function toggleMenu(){document.getElementById('plusMenu').classList.toggle('show');}
function pickFile(acc,tp){document.getElementById('plusMenu').classList.remove('show');const f=document.getElementById('fileInp');f.accept=acc;attType=tp;f.click();}
function quickPrompt(txt){document.getElementById('plusMenu').classList.remove('show');const q=document.getElementById('q');q.value=txt;q.focus();}
function clearAttach(){attData=null;attType=null;attName='';document.getElementById('preview-bar').style.display='none';}
function handleFile(inp){
  const file=inp.files;if(!file)return;attName=file.name;
  const reader=new FileReader();
  reader.onload=e=>{attData=e.target.result;document.getElementById('prev-name').textContent='📎 '+attName;document.getElementById('preview-bar').style.display='flex';};
  if(attType==='doc')reader.readAsText(file);else reader.readAsDataURL(file);
}
function copyTxt(btn){const t=btn.closest('.msg').innerText.replace(/📋 نسخ|⬇️ تحميل.*/g,'').trim();navigator.clipboard.writeText(t);btn.textContent='✅ تم النسخ';setTimeout(()=>btn.textContent='📋 نسخ',1500);}
function addMsg(r,t,m){
  const d=document.createElement('div');d.className='msg '+r;
  d.innerHTML=t.replace(/\\n/g,'<br>');
  if(m&&m.user_img)d.innerHTML+=`<img src="${m.user_img}" style="max-height:220px">`;
  if(m&&m.img)d.innerHTML+=`<img src="${m.img}"><div class="actions"><a class="act" href="${m.img}" download="DarkHorizon_8K.jpg" target="_blank">⬇️ تحميل الصورة</a></div>`;
  if(m&&m.vid)d.innerHTML+=`<video controls autoplay loop src="${m.vid}"></video><div class="actions"><a class="act" href="${m.vid}" download="DarkHorizon_Video.mp4" target="_blank">⬇️ تحميل الفيديو</a></div>`;
  if(r==='AI'&&(!m||(!m.img&&!m.vid)))d.innerHTML+=`<div class="actions"><button class="act" onclick="copyTxt(this)">📋 نسخ</button></div>`;
  const c=document.getElementById('chat');c.appendChild(d);c.scrollTop=c.scrollHeight;return d;
}
async function send(){
  const i=document.getElementById('q'),t=i.value.trim();if(!t&&!attData)return;i.value='';
  const curData=attData, curType=attType, curName=attName; clearAttach();
  addMsg('USER', t || ('📎 ملف مرفق: '+curName), curType==='img'?{user_img:curData}:null);
  const w=addMsg('AI','⏳ جاري التفكير والتنفيذ...');
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid,text:t,attData:curData,attType:curType,attName:curName})});
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
        text, sid, att_data, att_type, att_name = d.get("text", "").strip(), d.get("sid"), d.get("attData"), d.get("attType"), d.get("attName", "")
        full_user_text = text
        if att_type == "doc" and att_data: full_user_text = f"{text}\n\n[محتوى الملف ({att_name})]:\n{str(att_data)[:3500]}"
        elif att_type == "vid": full_user_text = f"{text or 'تم إرفاق مقطع فيديو'} (ملف فيديو: {att_name})."
        with db_lock:
            c = sqlite3.connect(DB_PATH)
            if not sid: sid = c.execute("INSERT INTO sessions (title) VALUES (?)", ((text or att_name)[:30],)).lastrowid
            c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, 'USER', ?)", (sid, full_user_text or "صورة مرفقة"))
            rows = c.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
            c.commit(); c.close()
        hist = [{"role": first(r), "content": list(r).pop()} for r in rows]
        low, media = text.lower(), {}
        if any(w in low for w in ("فيديو", "مقطع", "انميشن", "تحريك", "video", "cinema")):
            vid = create_video(text, att_data if att_type == "img" else None)
            reply, media = ("🎬 <b>تم إنتاج الفيديو بنجاح:</b>", {"vid": vid}) if vid else ("⚠️ تعذر إنتاج الفيديو حالياً، أعد المحاولة.", {})
        elif any(w in low for w in ("صورة", "صور", "ارسم", "صمم", "تصويرة", "image", "draw", "photo")) and att_type != "img":
            img = create_image(text)
            reply, media = ("🎨 <b>تم تصميم الصورة بدقة عالية:</b>", {"img": img}) if img else ("⚠️ تعذر تصميم الصورة حالياً، أعد المحاولة.", {})
        else:
            ctx = search_web(text) if any(w in low for w in ("ابحث", "أخبار", "طقس", "من هو", "ما هو", "اليوم", "2026")) else ""
            if ctx and hist: hist[-1]["content"] = f"معلومات محدثة:\n{ctx}\n\nسؤال المستخدم: {full_user_text}"
            reply = ai_brain(hist, att_data if att_type == "img" else None)
        with db_lock:
            c = sqlite3.connect(DB_PATH)
            c.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, reply, json.dumps(media)))
            c.commit(); c.close()
        return jsonify({"sid": sid, "reply": reply, "media": media})
    except Exception as e:
        return jsonify({"sid": 1, "reply": f"⚠️ تنبيه تقني: {str(e)}", "media": {}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
