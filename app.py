import os, re, json, time, random, shutil, base64, sqlite3, asyncio, threading, subprocess, urllib.parse, requests
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, render_template_string, send_from_directory, Response
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
conn.execute("CREATE TABLE IF NOT EXISTS jobs (jid TEXT PRIMARY KEY, done INTEGER, reply TEXT, media TEXT)")
conn.commit()

def get_keys(prefix):
    out = []
    for k in (prefix, f"{prefix}_1", f"{prefix}_2", f"{prefix}_3"):
        v = os.environ.get(k, "").strip()
        if v and v not in out: out.append(v)
    return out


def web_search_engine(query):
    sl = chr(47)
    clean_q = re.sub(r"^(ابحث عن|بحث عن|معلومات عن|من هو|من هي|search for|who is)\s+", "", query.strip(), flags=re.I)
    results = []
    # أ. البحث الفوري عبر DuckDuckGo Instant Answer API
    try:
        ddg_url = f"https:{sl}{sl}://duckduckgo.com{sl}"
        r = requests.get(ddg_url, params={"q": clean_q, "format": "json", "no_html": 1}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("AbstractText"):
                results.append(data["AbstractText"])
            for t in data.get("RelatedTopics", [])[:3]:
                if isinstance(t, dict) and t.get("Text"):
                    results.append(t["Text"])
    except Exception:
        pass

    # ب. البحث في موسوعة ويكيبيديا العربية ثم الإنجليزية
    for lang in ("ar", "en"):
        try:
            w_url = f"https:{sl}{sl}{lang}.wikipedia.org{sl}w{sl}api.php"
            wr = requests.get(w_url, params={"action": "query", "list": "search", "srsearch": clean_q, "format": "json", "srlimit": 2}, headers={"User-Agent": "DarkHorizonBot/1.0"}, timeout=10).json()
            hits = wr.get("query", {}).get("search", [])
            if hits:
                title = hits[0]["title"]
                sr = requests.get(f"https:{sl}{sl}{lang}.wikipedia.org{sl}api{sl}rest_v1{sl}page{sl}summary{sl}" + urllib.parse.quote(title), headers={"User-Agent": "DarkHorizonBot/1.0"}, timeout=10).json()
                ext = sr.get("extract", "")
                if ext:
                    results.append(f"[{title}]: {ext}")
                    break
        except Exception:
            continue

    return "\n".join(results)[:1500]

def smart_ai(messages):
    sl = chr(47)
    cf_acc = os.environ.get("CF_ACCOUNT_ID", "").strip()
    cf_tok = os.environ.get("CF_API_TOKEN", "").strip()
    if cf_acc and cf_tok:
        try:
            u = f"https:{sl}{sl}://cloudflare.com{sl}client{sl}v4{sl}accounts{sl}{cf_acc}{sl}ai{sl}run{sl}@cf/meta/llama-3.1-8b-instruct"
            r = requests.post(u, headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"}, json={"messages": messages}, timeout=12)
            if r.status_code == 200:
                res = r.json().get("result", {}).get("response", "").strip()
                if res: return res
        except Exception: pass
    try:
        conv = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-6:]])[:600]
        r2 = requests.get(f"https:{sl}{sl}text.pollinations.ai{sl}" + urllib.parse.quote(conv), params={"seed": random.randint(1, 99999)}, timeout=15)
        if r2.status_code == 200 and "Free limit" not in r2.text and "404" not in r2.text and len(r2.text.strip()) > 2:
            return r2.text.strip()
    except Exception: pass
    return "أهلاً بك في DARK HORIZON AI! كيف يمكنني مساعدتك الآن؟"

def apply_brand_logo(fpath):
    logo_p = "brand_logo.png" if os.path.exists("brand_logo.png") else os.path.join(WORK, "brand_logo.png")
    if os.path.exists(logo_p) and os.path.exists(fpath):
        try:
            from PIL import Image
            base = Image.open(fpath).convert("RGBA")
            w, h = base.size
            base = base.crop((0, 0, w, int(h * 0.94)))
            lg = Image.open(logo_p).convert("RGBA")
            lw = max(80, int(base.width * 0.24))
            lh = int(lg.height * (lw / lg.width))
            lg = lg.resize((lw, lh))
            base.paste(lg, (base.width - lw - 14, base.height - lh - 14), lg)
            base.convert("RGB").save(fpath, quality=90)
        except Exception: pass

def generate_image_item(en_prompt, idx=0):
    sl = chr(47)
    seed = random.randint(10000, 9999999)
    full_p = f"{en_prompt}, cinematic angle {idx+1}, hyperrealistic, dramatic lighting, 8k"
    fn = f"OMNI_{int(time.time())}_{seed}.jpg"
    fpath = os.path.join(WORK, fn)

    cf_acc = os.environ.get("CF_ACCOUNT_ID", "").strip()
    cf_tok = os.environ.get("CF_API_TOKEN", "").strip()
    if cf_acc and cf_tok:
        
        cf_mdls = ("@cf/black-forest-labs/flux-1-schnell", "@cf/bytedance/stable-diffusion-xl-lightning", "@cf/stabilityai/stable-diffusion-xl-base-1.0")
        for step in range(len(cf_mdls)):
            c_mdl = cf_mdls[(idx + step) % len(cf_mdls)]
            cf_url = f"https:{sl}{sl}://cloudflare.com{sl}client{sl}v4{sl}accounts{sl}{cf_acc}{sl}ai{sl}run{sl}{c_mdl}"
            payload = {"prompt": full_p[:240], "num_steps": 2} if "flux" in c_mdl else {"prompt": full_p[:240]}
            try:
                cr = requests.post(cf_url, headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"}, json=payload, timeout=25)
                if cr.status_code == 200:
                    if "json" in cr.headers.get("Content-Type", ""):
                        b64_img = cr.json().get("result", {}).get("image", "")
                        if b64_img:
                            open(fpath, "wb").write(base64.b64decode(b64_img))
                            apply_brand_logo(fpath)
                            return f"/media/{fn}"
                    elif len(cr.content) > 4000:
                        open(fpath, "wb").write(cr.content)
                        apply_brand_logo(fpath)
                        return f"/media/{fn}"
            except Exception: continue

    for attempt in range(1):
        if idx > 0 or attempt > 0: time.sleep(0.5)
        p_url = f"https:{sl}{sl}image.pollinations.ai{sl}prompt{sl}" + urllib.parse.quote(full_p[:200]) + f"?width=540&height=960&nologo=true&seed={seed + attempt}"
        try:
            r = requests.get(p_url, headers={"User-Agent": f"Mozilla/5.0 (Studio-{idx}-{attempt})"}, timeout=25)
            if r.status_code == 200 and len(r.content) > 4500 and b"Free limit" not in r.content:
                open(fpath, "wb").write(r.content)
                apply_brand_logo(fpath)
                return f"/media/{fn}"
        except Exception: continue
    return None

async def make_voice(txt, mp3):
    clean = re.sub(r"\s+", " ", re.sub(r"[^\w\s\u0600-\u06FF]", " ", txt)).strip()
    v = "ar-AE-HamdanNeural" if any("\u0600" <= c <= "\u06FF" for c in clean) else "en-US-ChristopherNeural"
    await edge_tts.Communicate(clean, v, rate="+2%").save(mp3)


def fast_ar_to_en(text):
    sl = chr(47)
    clean = re.sub(r"(اريد|انشيء|أنشئ|صمم|ارسم|صور|صورة|فيديو|فلم|فيلم|مدته|ثوان|ثانية|\d+)", "", text).strip()
    if not clean: clean = text
    try:
        u = f"https:{sl}{sl}://googleapis.com{sl}translate_a{sl}single"
        r = requests.get(u, params={"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": clean[:250]}, timeout=8)
        if r.status_code == 200:
            en = "".join([seg for seg in r.json() if seg]).strip()
            if en and len(en) > 2:
                return f"{en}, cinematic lighting, ultra realistic, 8k"
    except Exception:
        pass
    return f"cinematic epic historical scene, {random.randint(1,999)}, 8k"

def generate_media(q, hist_ctx):
    low = q.lower().strip()
    is_vid = any(w in low for w in ("فيديو", "video", "وثائقي", "فيلم", "ثوان", "ثانية", "ثواني"))
    m_dur = re.search(r"(\d+)", q)
    req_dur = max(5.0, min(30.0, float(m_dur.group(1)) if m_dur else 8.0))
    ctx_q = f"سياق المحادثة:\n{hist_ctx[-300:]}\nالطلب الحالي: {q}"

    en_p = q if all(ord(c) < 128 for c in q) and len(q.split()) > 2 else smart_ai([{"role": "system", "content": "Translate to 10-word English image prompt ONLY."}, {"role": "user", "content": ctx_q}])
    if any("\u0600" <= c <= "\u06FF" for c in en_p) or len(en_p) < 5:
        en_p = "cinematic Arabian stallion running in golden desert dunes at sunset, 8k"

    if is_vid:
        sl = chr(47)
        seed = random.randint(10000, 999999)
        script = smart_ai([{"role": "system", "content": "اكتب تعليقاً صوتياً وثائقياً تاريخياً مشوقاً من جملتين بالعربية الفصحى بدون رموز."}, {"role": "user", "content": q}])
        if "أهلاً بك" in script or len(script) < 10:
            script = f"في صفحات التاريخ العريق، تتجلى أعظم الملاحم والبطولات التي خلدتها الذاكرة الإنسانية عبر العصور."
        aud_p = os.path.join(WORK, f"Voice_{seed}.mp3")
        try: asyncio.run(make_voice(script, aud_p))
        except Exception: pass
        has_aud = os.path.exists(aud_p) and os.path.getsize(aud_p) > 1500

        raw_vid = os.path.join(WORK, f"raw_{seed}.mp4")
        got_real_video = False

        # محاولة توليد فيديو حركي حقيقي (Text-to-Video AI) عبر Hugging Face GPU
        vid_models = ("Lightricks/LTX-Video", "Wan-AI/Wan2.1-T2V-14B", "ali-vilab/text-to-video-ms-1.7b")
        for hft in get_keys("HF_TOKEN"):
            for v_mdl in vid_models:
                v_url = f"https:{sl}{sl}router.huggingface.co{sl}hf-inference{sl}models{sl}{v_mdl}"
                try:
                    vr = requests.post(v_url, headers={"Authorization": f"Bearer {hft}"}, json={"inputs": f"{en_p}, smooth realistic motion, dynamic action, 24fps"}, timeout=45)
                    if vr.status_code == 200 and len(vr.content) > 25000:
                        open(raw_vid, "wb").write(vr.content)
                        got_real_video = True
                        break
                except Exception:
                    continue
            if got_real_video:
                break

        vid_fn = f"DARK_HORIZON_{int(req_dur)}s_{seed}.mp4"
        vid_p = os.path.join(WORK, vid_fn)

        if got_real_video and os.path.exists(raw_vid):
            # دمج الفيديو الحركي الحقيقي مع التعليق الصوتي العربي
            cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", raw_vid] + (["-i", aud_p] if has_aud else []) + ["-vf", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"] + (["-c:a", "aac"] if has_aud else []) + ["-t", f"{req_dur:.2f}", vid_p]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # مونتاج متعدد المشاهد المتتابعة (Storytelling Sequence) بدلاً من الصورة الواحدة الثابتة
            num_sc = 3
            sc_urls = [u for u in [generate_image_item(f"{en_p}, cinematic scene {i+1}", i) for i in range(num_sc)] if u]
            clips = []
            sc_dur = req_dur / max(1, len(sc_urls))
            for idx, u in enumerate(sc_urls):
                im_p = os.path.join(WORK, u.replace("/media/", ""))
                cl_p = os.path.join(WORK, f"cl_{idx}_{seed}.mp4")
                if os.path.exists(im_p):
                    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-framerate", "12", "-i", im_p, "-vf", "scale=540:960:force_original_aspect_ratio=increase,crop=540:960", "-c:v", "libx264", "-preset", "ultrafast", "-t", f"{sc_dur:.2f}", "-pix_fmt", "yuv420p", cl_p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(cl_p): clips.append(cl_p)
            valid_imgs = [os.path.join(WORK, u.replace("/media/", "")) for u in sc_urls if os.path.exists(os.path.join(WORK, u.replace("/media/", "")))]
            if not valid_imgs:
                from PIL import Image
                fb_im = os.path.join(WORK, f"fb_{seed}.jpg")
                Image.new("RGB", (540, 960), (20, 30, 50)).save(fb_im)
                valid_imgs = [fb_im]
            sc_d = req_dur / len(valid_imgs)
            inp_args = []
            flt = ""
            for idx, im_f in enumerate(valid_imgs):
                inp_args += ["-loop", "1", "-t", f"{sc_d:.2f}", "-i", im_f]
                flt += f"[{idx}:v]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,setsar=1[v{idx}];"
            flt += "".join([f"[v{i}]" for i in range(len(valid_imgs))]) + f"concat=n={len(valid_imgs)}:v=1:a=0[outv]"
            cmd = ["ffmpeg", "-y"] + inp_args
            if has_aud:
                cmd += ["-i", aud_p, "-filter_complex", flt, "-map", "[outv]", "-map", f"{len(valid_imgs)}:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", vid_p]
            else:
                cmd += ["-filter_complex", flt, "-map", "[outv]", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-t", f"{req_dur:.2f}", vid_p]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mode_lbl = "فيديو حركي بالذكاء الاصطناعي (AI Motion)" if got_real_video else "مونتاج مشاهد متتابعة"
        return f"🎬 <b>إنتاج DARK HORIZON FILMS LTD ({mode_lbl} - {int(req_dur)} ثانية):</b>\n\n🎙️ <b>السيناريو:</b>\n{script}", {"vid": f"/media/{vid_fn}"}

    m_cnt = re.search(r"(\d+)", q)
    count = max(1, min(10, int(m_cnt.group(1)))) if m_cnt else (4 if any(w in low for w in ("صور", "معرض", "تشكيلة", "المزيد", "مزيد", "أخرى", "اخرى", "more", "photos")) else 1)
    with ThreadPoolExecutor(max_workers=4) as ex:
        urls = [u for u in ex.map(lambda i: generate_image_item(en_p, i), range(count)) if u]
    if len(urls) > 1:
        return f"🎨 <b>تم تصميم {len(urls)} صور سينمائية (DARK HORIZON FILMS LTD):</b>", {"imgs": urls}
    if len(urls) == 1:
        return "🎨 <b>تم تصميم الصورة بدقة سينمائية (DARK HORIZON FILMS LTD):</b>", {"imgs": urls}
    return "⚠️ الخادم السحابي مشغول لحظياً، أعد إرسال الطلب وسيتم التصميم فوراً.", {}

HTML = """<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>DARK HORIZON AI</title><style>
*{box-sizing:border-box;font-family:system-ui,sans-serif}body{background:#090b10;color:#f8fafc;margin:0;display:flex;flex-direction:column;height:100vh}
header{padding:12px 16px;background:#111622;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(245,158,11,0.3)}
.brand{font-weight:800;font-size:15px;color:#f59e0b}.h-btn{background:rgba(255,255,255,0.08);color:#fff;border:1px solid rgba(245,158,11,0.3);padding:6px 10px;border-radius:10px;font-size:12px;cursor:pointer}
#drawer{display:none;background:#111622;padding:12px;max-height:220px;overflow-y:auto;border-bottom:1px solid #f59e0b}.s-item{display:flex;justify-content:space-between;align-items:center;padding:10px;background:rgba(255,255,255,0.05);border-radius:8px;margin-bottom:6px}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;max-width:800px;width:100%;margin:auto}
.msg{max-width:88%;padding:12px 16px;border-radius:18px;line-height:1.6;font-size:15px;white-space:pre-wrap}.user{align-self:flex-start;background:#1e293b;border:1px solid #38bdf8}.bot{align-self:flex-end;background:#1a2130;border:1px solid rgba(255,255,255,0.1);width:100%}
.bot video{width:100%;max-height:65vh;object-fit:contain;border-radius:12px;margin-top:8px;background:#000}.img-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px}
.img-card{background:#0f172a;border:1px solid rgba(245,158,11,0.3);border-radius:12px;padding:6px;display:flex;flex-direction:column}.img-card img{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:8px}
.dl{display:block;text-align:center;background:#f59e0b;color:#000;padding:10px;border-radius:10px;margin-top:8px;text-decoration:none;font-weight:800;width:100%;border:none;cursor:pointer}.dl-sm{text-align:center;background:rgba(245,158,11,0.2);color:#fde047;padding:6px;border-radius:8px;margin-top:6px;text-decoration:none;font-size:12px;font-weight:700}
.footer{background:#111622;padding:12px;border-top:1px solid rgba(245,158,11,0.2)}.input-row{max-width:800px;margin:auto;display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.08);border:1px solid #f59e0b;border-radius:26px;padding:6px 12px}
input[type=text]{flex:1;background:transparent;border:none;color:#fff;font-size:15px;outline:none;padding:6px}.c-btn{border:none;width:40px;height:40px;border-radius:50%;font-weight:bold;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}#plusBtn{background:rgba(255,255,255,0.12);color:#f59e0b}#sendBtn{background:#f59e0b;color:#000}
</style></head><body>
<header><span class="brand">✨ DARK HORIZON AI</span><div><button type="button" id="docBtn" class="h-btn">🩺 فحص</button> <button type="button" id="histBtn" class="h-btn">📂 السجل</button> <button type="button" id="newBtn" class="h-btn">➕</button></div></header>
<div id="drawer"></div><div id="chat"></div>
<div class="footer"><div id="fileBar" style="display:none;max-width:800px;margin:0 auto 8px;background:rgba(245,158,11,0.2);color:#fde047;padding:6px 12px;border-radius:10px;font-size:13px;justify-content:space-between"></div>
<div class="input-row"><input type="file" id="fileIn" accept="image/*,.pdf,.txt" style="display:none"><button type="button" id="plusBtn" class="c-btn">+</button><input type="text" id="q" placeholder="تحدث، أرفق ملفاً، اطلب صوراً أو فيديو..."><button type="button" id="sendBtn" class="c-btn">➤</button></div></div>
<script src="/ui_logic.js"></script></body></html>"""

@app.route("/ui_logic.js")
def ui_logic():
    code = """
var sid = localStorage.getItem("dh_sid") || null;
function dlAllImgs(enc){ JSON.parse(decodeURIComponent(enc)).forEach(function(u, idx){ setTimeout(function(){ var a=document.createElement("a"); a.href=u; a.download="DARK_HORIZON_"+(idx+1)+".jpg"; document.body.appendChild(a); a.click(); document.body.removeChild(a); }, idx*500); }); }
function addBubble(role, content, media){
  var chat=document.getElementById("chat"), d=document.createElement("div"); d.className="msg "+(role==="User"?"user":"bot"); var h=content;
  if(media && media.vid) h+='<video controls playsinline src="'+media.vid+'"></video><a class="dl" href="'+media.vid+'" download="DARK_HORIZON_VIDEO.mp4">⬇️ تحميل الفيديو إلى Download</a>';
  if(media && media.imgs && media.imgs.length>0){
    if(media.imgs.length>1){ var ls=encodeURIComponent(JSON.stringify(media.imgs)); h+='<button type="button" class="dl" onclick="dlAllImgs(\\''+ls+'\\')">⬇️ تحميل جميع الصور ('+media.imgs.length+') إلى Download</button><div class="img-grid">'; media.imgs.forEach(function(u,i){ h+='<div class="img-card"><img src="'+u+'"><a class="dl-sm" href="'+u+'" download="DARK_HORIZON_'+(i+1)+'.jpg">⬇️ صورة '+(i+1)+'</a></div>'; }); h+='</div>'; }
    else { var u=media.imgs.at(0); h+='<img style="width:100%;border-radius:12px;margin-top:8px" src="'+u+'"><a class="dl" href="'+u+'" download="DARK_HORIZON_IMG.jpg">⬇️ تحميل الصورة إلى Download</a>'; }
  }
  d.innerHTML=h; chat.appendChild(d); chat.scrollTop=chat.scrollHeight; return d;
}
function safeJson(res){ return res.text().then(function(t){ try{return JSON.parse(t);}catch(e){throw new Error("الخادم يستيقظ، أعد المحاولة الآن.");} }); }
function loadSessions(){ fetch("/sessions").then(safeJson).then(function(list){ var dr=document.getElementById("drawer"); dr.innerHTML=""; list.forEach(function(s){ var row=document.createElement("div"); row.className="s-item"; var sp=document.createElement("span"); sp.style.cssText="flex:1;cursor:pointer"; sp.textContent=s.title; sp.addEventListener("click",function(){sid=s.id;localStorage.setItem("dh_sid",sid);dr.style.display="none";loadMessages();}); var del=document.createElement("button"); del.textContent="✕"; del.style.cssText="background:none;border:none;color:#ef4444;font-size:16px"; del.addEventListener("click",function(){fetch("/sessions/"+s.id,{method:"DELETE"}).then(function(){if(sid==s.id)startNew();loadSessions();});}); row.appendChild(sp); row.appendChild(del); dr.appendChild(row); }); }).catch(function(){}); }
function startNew(){ sid=null; localStorage.removeItem("dh_sid"); document.getElementById("chat").innerHTML='<div class="msg bot">✨ استوديو DARK HORIZON AI جاهز! تحدث معي أو اطلب صوراً أو فيديو.</div>'; }
function loadMessages(){ if(!sid){startNew();return;} fetch("/messages/"+sid).then(safeJson).then(function(msgs){ var chat=document.getElementById("chat"); chat.innerHTML=""; msgs.forEach(function(m){addBubble(m.role,m.content,m.media);}); }).catch(function(){startNew();}); }
function sendMessage(){
  var qEl=document.getElementById("q"), fEl=document.getElementById("fileIn"), txt=qEl.value.trim(), file=(fEl.files&&fEl.files.length>0)?fEl.files.item(0):null;
  if(!txt && !file) return;
  addBubble("User", txt||("📎 "+file.name), {}); var waitBox=addBubble("AI", "⚡ جاري التنفيذ...", {});
  var fd=new FormData(); if(sid)fd.append("sid",sid); fd.append("q",txt); if(file)fd.append("file",file);
  qEl.value=""; fEl.value=""; document.getElementById("fileBar").style.display="none";
  fetch("/send_all", {method:"POST", body:fd}).then(safeJson).then(function(d){
    sid=d.sid; localStorage.setItem("dh_sid",sid);
    if(d.job_id){ waitBox.textContent="🎨🎬 جاري التصميم والإخراج السينمائي..."; var iv=setInterval(function(){ fetch("/job/"+d.job_id).then(safeJson).then(function(st){ if(st.done){clearInterval(iv);waitBox.remove();addBubble("AI",st.reply,st.media);loadSessions();} }).catch(function(){}); }, 1000); }
    else { waitBox.remove(); addBubble("AI",d.reply,d.media); loadSessions(); }
  }).catch(function(err){ waitBox.textContent="⚠️ "+err.message; });
}
document.addEventListener("DOMContentLoaded", function(){
  document.getElementById("docBtn").addEventListener("click",function(){ fetch("/doctor").then(safeJson).then(function(d){ addBubble("AI", d.report, {}); }); });
  document.getElementById("histBtn").addEventListener("click",function(){var dr=document.getElementById("drawer");dr.style.display=(dr.style.display==="block")?"none":"block";loadSessions();});
  document.getElementById("newBtn").addEventListener("click",startNew);
  document.getElementById("plusBtn").addEventListener("click",function(){document.getElementById("fileIn").click();});
  document.getElementById("fileIn").addEventListener("change",function(){var fEl=document.getElementById("fileIn"),fb=document.getElementById("fileBar");if(fEl.files&&fEl.files.length>0){fb.style.display="flex";fb.innerHTML="<span>📎 "+fEl.files.item(0).name+"</span><span id='clrF' style='color:#ef4444;font-weight:bold;cursor:pointer'>✕</span>";document.getElementById("clrF").addEventListener("click",function(){fEl.value="";fb.style.display="none";});}});
  document.getElementById("sendBtn").addEventListener("click",sendMessage);
  document.getElementById("q").addEventListener("keydown",function(e){if(e.key==="Enter"){e.preventDefault();sendMessage();}});
  loadSessions(); loadMessages();
});
"""
    return Response(code, mimetype="application/javascript")

@app.route("/doctor")
def doctor():
    with db_lock: conn.execute("DELETE FROM messages WHERE content LIKE '%جاري%'"); conn.commit()
    sl = chr(47)
    cf_acc = os.environ.get("CF_ACCOUNT_ID", "").strip()
    cf_tok = os.environ.get("CF_API_TOKEN", "").strip()
    cf_stat = "غير مضاف ⚠️"
    if cf_acc and cf_tok:
        try:
            t_url = f"https:{sl}{sl}://cloudflare.com{sl}client{sl}v4{sl}accounts{sl}{cf_acc}{sl}ai{sl}run{sl}@cf/black-forest-labs/flux-1-schnell"
            tr = requests.post(t_url, headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"}, json={"prompt": "test", "num_steps": 1}, timeout=12)
            cf_stat = "متصل ويعمل بقوة 100% ✅" if tr.status_code == 200 else f"تنبيه ({tr.status_code}) ⚠️"
        except Exception as e: cf_stat = f"خطأ اتصال: {str(e)[:40]} ⚠️"
    return jsonify({"report": f"🩺 <b>تقرير الفحص الذاتي لـ DARK HORIZON AI:</b>\n• حالة الخادم: متصل ✅\n• بطاقات Cloudflare GPU: {cf_stat}\n• قاعدة البيانات: نظيفة ✅"})

@app.route("/media/<path:fn>")
def media(fn): return send_from_directory(WORK, fn)
@app.route("/")
def index(): return render_template_string(HTML)
@app.route("/health")
def health(): return jsonify({"status": "ok"})
@app.route("/sessions")
def sessions():
    with db_lock: rows = conn.execute("SELECT id, title FROM sessions ORDER BY id DESC").fetchall()
    return jsonify([{"id": r_id, "title": r_title} for r_id, r_title in rows])
@app.route("/sessions/<int:sid>", methods=["DELETE"])
def del_s(sid):
    with db_lock: conn.execute("DELETE FROM messages WHERE session_id=?", (sid,)); conn.execute("DELETE FROM sessions WHERE id=?", (sid,)); conn.commit()
    return jsonify({"ok": True})
@app.route("/messages/<int:sid>")
def get_m(sid):
    with db_lock: rows = conn.execute("SELECT role, content, media FROM messages WHERE session_id=? ORDER BY id ASC", (sid,)).fetchall()
    return jsonify([{"role": r_role, "content": r_cnt, "media": json.loads(r_med or "{}")} for r_role, r_cnt, r_med in rows])

def run_media_job(jid, sid, q, ctx):
    try:
        rep, m_obj = generate_media(q, ctx)
        with db_lock:
            conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, ?)", (sid, rep, json.dumps(m_obj)))
            conn.execute("UPDATE jobs SET done=1, reply=?, media=? WHERE jid=?", (rep, json.dumps(m_obj), jid)); conn.commit()
    except Exception as e:
        with db_lock: conn.execute("UPDATE jobs SET done=1, reply=?, media='{}' WHERE jid=?", (f"⚠️ تعذر الإخراج: {str(e)[:60]}", jid)); conn.commit()

@app.route("/job/<jid>")
def check_job(jid):
    with db_lock: row = conn.execute("SELECT done, reply, media FROM jobs WHERE jid=?", (jid,)).fetchone()
    if not row: return jsonify({"done": True, "reply": "⚠️ أعد إرسال الطلب.", "media": {}})
    is_done, rep_txt, med_json = row
    return jsonify({"done": bool(is_done), "reply": rep_txt, "media": json.loads(med_json or "{}")})

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
    ctx = "\n".join([f"{r_role}: {r_cnt[:250]}" for r_role, r_cnt in hist])
    is_q = q.startswith(("هل", "لماذا", "كيف", "ما هو", "ما هي", "وش", "واش", "اين", "أين"))
    is_m = not up_path and not is_q and any(w in q.lower() for w in ("فيديو", "video", "وثائقي", "صورة", "صور", "ارسم", "image", "draw", "photo", "pic", "فيلم", "ثوان", "ثانية", "عشر", "المزيد", "مزيد", "أخرى", "اخرى", "غيرها", "more", "شخصيات", "شخصية", "مشابهة", "مشابه"))
    if is_m:
        jid = f"j_{int(time.time())}_{random.randint(100,999)}"
        with db_lock: conn.execute("INSERT INTO jobs (jid, done, reply, media) VALUES (?, 0, '', '{}')", (jid,)); conn.commit()
        threading.Thread(target=run_media_job, args=(jid, sid, q, ctx), daemon=True).start()
        return jsonify({"sid": sid, "job_id": jid})
    if up_path and os.path.exists(up_path):
        rep = smart_ai([{"role": "user", "content": f"تم إرفاق ملف باسم {os.path.basename(up_path)}. {q}"}])
    else:
        web_facts = web_search_engine(q)
        sys_txt = "أنت المساعد الذكي لاستوديو DARK HORIZON FILMS LTD. تفهم سياق المحادثة السابقة وتستعين بنتائج البحث الحية لتقديم إجابات دقيقة وشاملة بالعربية."
        if web_facts:
            sys_txt += f"\n\nنتائج البحث الحية من الويب:\n{web_facts}"
        msgs = [{"role": "system", "content": sys_txt}]
        for r_role, r_cnt in hist: msgs.append({"role": "user" if r_role == "User" else "assistant", "content": r_cnt[:400]})
        rep = smart_ai(msgs)
    with db_lock: conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, '{}')", (sid, rep)); conn.commit()
    return jsonify({"sid": sid, "reply": rep, "media": {}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
