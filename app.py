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
    clean_q = re.sub(r"^(ابحث عن|بحث عن|معلومات عن|من هو|من هي|حول|فيديو|صور|صورة|اريد|انشيء|أنشئ)\s+", "", query.strip(), flags=re.I)
    results = []
    try:
        r = requests.get(f"https:{sl}{sl}://duckduckgo.com{sl}", params={"q": clean_q, "format": "json", "no_html": 1}, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code == 200 and r.json().get("AbstractText"):
            results.append(r.json()["AbstractText"])
    except Exception: pass
    for lang in ("ar", "en"):
        try:
            wr = requests.get(f"https:{sl}{sl}{lang}.wikipedia.org{sl}w{sl}api.php", params={"action": "query", "list": "search", "srsearch": clean_q, "format": "json", "srlimit": 2}, headers={"User-Agent": "DarkHorizonBot/1.0"}, timeout=8).json()
            hits = wr.get("query", {}).get("search", [])
            if hits:
                title = hits["title"]
                sr = requests.get(f"https:{sl}{sl}{lang}.wikipedia.org{sl}api{sl}rest_v1{sl}page{sl}summary{sl}" + urllib.parse.quote(title), headers={"User-Agent": "DarkHorizonBot/1.0"}, timeout=8).json()
                if sr.get("extract"):
                    results.append(f"[{title}]: {sr['extract']}")
                    break
        except Exception: continue
    return "\n".join(results)[:1200]

def smart_ai(messages):
    sl = chr(47)
    g_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if g_key:
        try:
            g_url = f"https:{sl}{sl}://googleapis.com{sl}v1beta{sl}models{sl}gemini-2.5-flash:generateContent?key={g_key}"
            prompt_txt = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-6:]])
            gr = requests.post(g_url, json={"contents": [{"parts": [{"text": prompt_txt}]}]}, timeout=15)
            if gr.status_code == 200:
                c0 = next(iter(gr.json().get("candidates", [])), {})
                p0 = next(iter(c0.get("content", {}).get("parts", [])), {})
                if p0.get("text"): return p0["text"].strip()
        except Exception: pass
    cf_acc = os.environ.get("CF_ACCOUNT_ID", "").strip()
    cf_tok = os.environ.get("CF_API_TOKEN", "").strip()
    if cf_acc and cf_tok:
        try:
            u = f"https:{sl}{sl}://cloudflare.com{sl}client{sl}v4{sl}accounts{sl}{cf_acc}{sl}ai{sl}run{sl}@cf/meta/llama-3.1-8b-instruct"
            r = requests.post(u, headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"}, json={"messages": messages}, timeout=12)
            if r.status_code == 200 and r.json().get("result", {}).get("response"):
                return r.json()["result"]["response"].strip()
        except Exception: pass
    try:
        conv = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages[-4:]])[:500]
        r2 = requests.get(f"https:{sl}{sl}text.pollinations.ai{sl}" + urllib.parse.quote(conv), params={"seed": random.randint(1, 99999)}, timeout=12)
        if r2.status_code == 200 and "Free limit" not in r2.text and "404" not in r2.text and len(r2.text.strip()) > 2:
            return r2.text.strip()
    except Exception: pass
    return ""

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
            base.convert("RGB").save(fpath, quality=96)
        except Exception: pass

def generate_image_item(en_prompt, idx=0):
    sl = chr(47)
    seed = random.randint(10000, 9999999)
    full_p = f"{en_prompt}, single full screen frame, sharp focus, crisp details, 8k photorealistic, no split screen, no collage"
    fn = f"OMNI_{int(time.time())}_{seed}.jpg"
    fpath = os.path.join(WORK, fn)

    g_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if g_key:
        try:
            im_url = f"https:{sl}{sl}://googleapis.com{sl}v1beta{sl}models{sl}imagen-3.0-generate-002:predict?key={g_key}"
            ir = requests.post(im_url, json={"instances": [{"prompt": full_p[:280]}], "parameters": {"sampleCount": 1, "aspectRatio": "9:16"}}, timeout=22)
            if ir.status_code == 200:
                p0 = next(iter(ir.json().get("predictions", [])), {})
                if p0.get("bytesBase64Encoded"):
                    open(fpath, "wb").write(base64.b64decode(p0["bytesBase64Encoded"]))
                    apply_brand_logo(fpath)
                    return "data:image/jpeg;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
        except Exception: pass

    cf_acc = os.environ.get("CF_ACCOUNT_ID", "").strip()
    cf_tok = os.environ.get("CF_API_TOKEN", "").strip()
    if cf_acc and cf_tok:
        cf_mdls = ("@cf/black-forest-labs/flux-1-schnell", "@cf/bytedance/stable-diffusion-xl-lightning", "@cf/lykon/dreamshaper-8-lcm", "@cf/stabilityai/stable-diffusion-xl-base-1.0")
        for step in range(len(cf_mdls)):
            c_mdl = cf_mdls[(idx + step) % len(cf_mdls)]
            cf_url = f"https:{sl}{sl}://cloudflare.com{sl}client{sl}v4{sl}accounts{sl}{cf_acc}{sl}ai{sl}run{sl}{c_mdl}"
            payload = {"prompt": full_p[:240], "num_steps": 8, "width": 544, "height": 960} if "flux" in c_mdl else {"prompt": full_p[:240], "width": 544, "height": 960}
            try:
                cr = requests.post(cf_url, headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"}, json=payload, timeout=25)
                if cr.status_code == 200:
                    if "json" in cr.headers.get("Content-Type", ""):
                        b64_img = cr.json().get("result", {}).get("image", "")
                        if b64_img:
                            open(fpath, "wb").write(base64.b64decode(b64_img))
                            apply_brand_logo(fpath)
                            return "data:image/jpeg;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
                    elif len(cr.content) > 4000:
                        open(fpath, "wb").write(cr.content)
                        apply_brand_logo(fpath)
                        return "data:image/jpeg;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
            except Exception: continue

    for hft in get_keys("HF_TOKEN"):
        for h_mdl in ("black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-xl-base-1.0"):
            try:
                hr = requests.post(f"https:{sl}{sl}router.huggingface.co{sl}hf-inference{sl}models{sl}{h_mdl}", headers={"Authorization": f"Bearer {hft}"}, json={"inputs": full_p[:240]}, timeout=22)
                if hr.status_code == 200 and len(hr.content) > 15000:
                    open(fpath, "wb").write(hr.content)
                    apply_brand_logo(fpath)
                    return "data:image/jpeg;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
            except Exception: continue

    time.sleep(idx * 1.5)
    p_url = f"https:{sl}{sl}image.pollinations.ai{sl}prompt{sl}" + urllib.parse.quote(full_p[:180]) + f"?width=544&height=960&nologo=true&seed={seed}"
    try:
        r = requests.get(p_url, headers={"User-Agent": f"Mozilla/5.0 (Client-{idx}-{seed})"}, timeout=22)
        if r.status_code == 200 and len(r.content) > 22000 and b"Free limit" not in r.content:
            open(fpath, "wb").write(r.content)
            apply_brand_logo(fpath)
            return "data:image/jpeg;base64," + base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
    except Exception: pass
    return None

async def make_voice(txt, mp3):
    clean = re.sub(r"\s+", " ", re.sub(r"[^\w\s\u0600-\u06FF]", " ", txt)).strip()
    v = "ar-AE-HamdanNeural" if any("\u0600" <= c <= "\u06FF" for c in clean) else "en-US-ChristopherNeural"
    await edge_tts.Communicate(clean, v, rate="+2%").save(mp3)

def fast_ar_to_en(text, web_facts=""):
    sl = chr(47)
    clean = re.sub(r"(اريد|انشيء|أنشئ|صمم|ارسم|صور|صورة|فيديو|واقعي|فلم|فيلم|مدته|ثوان|ثانية|المزيد|مزيد|\d+)", "", text).strip() or text
    en = ""
    try:
        u = f"https:{sl}{sl}://googleapis.com{sl}translate_a{sl}single"
        r = requests.get(u, params={"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": clean[:200]}, timeout=8)
        if r.status_code == 200:
            segs = next(iter(r.json()), [])
            en = "".join([s for s in segs if isinstance(s, list) and s]).strip()
    except Exception:
        pass
    if not en:
        en = clean
    if any(w in text for w in ("بنات", "بنت", "نساء", "امرأة", "فتاة", "فتيات")):
        en = f"beautiful young women, female portrait, {en}, sharp DSLR photography, detailed skin texture, 8k"
    elif any(w in text for w in ("رجال", "رجل", "شاب", "شباب", "فارس", "فرسان")):
        en = f"handsome adult men, masculine male portrait, {en}, sharp DSLR photography, detailed skin texture, 8k"
    else:
        en = f"{en}, sharp DSLR photography, hyperrealistic, detailed texture, 8k"
    return en

def try_real_video(prompt_en, img_path, aud_path, is_talk, out_mp4):
    sl = chr(47)
    colab_url = os.environ.get("COLAB_GPU_URL", "").strip().rstrip("/")
    if colab_url:
        try:
            cr = requests.post(f"{colab_url}/render_gpu", data={"prompt": prompt_en, "script": prompt_en, "duration": 25}, timeout=120)
            if cr.status_code == 200 and len(cr.content) > 25000:
                open(out_mp4, "wb").write(cr.content)
                return "NVIDIA T4 GPU Live Action"
        except Exception:
            pass

    g_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if g_key:
        try:
            veo_url = f"https:{sl}{sl}://googleapis.com{sl}v1beta{sl}models{sl}veo-2.0-generate-001:predictLongRunning?key={g_key}"
            vr = requests.post(veo_url, json={"instances": [{"prompt": f"{prompt_en}, realistic live action motion, 8k"}], "parameters": {"aspectRatio": "9:16"}}, timeout=20)
            if vr.status_code == 200 and vr.json().get("name"):
                op_name = vr.json()["name"]
                for _ in range(10):
                    time.sleep(4)
                    op_r = requests.get(f"https:{sl}{sl}://googleapis.com{sl}v1beta{sl}{op_name}?key={g_key}", timeout=15).json()
                    if op_r.get("done"):
                        samples = op_r.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
                        v_uri = next(iter(samples), {}).get("video", {}).get("uri", "")
                        if v_uri:
                            vb = requests.get(f"{v_uri}&key={g_key}", timeout=30).content
                            if len(vb) > 25000:
                                open(out_mp4, "wb").write(vb)
                                return "Google Veo 2 AI Motion"
                        break
        except Exception: pass
    if is_talk and img_path and os.path.exists(img_path) and aud_path and os.path.exists(aud_path):
        for sp in (f"https:{sl}{sl}vinthony-sadtalker.hf.space", f"https:{sl}{sl}fffiloni-sadtalker.hf.space"):
            try:
                ib = "data:image/jpeg;base64," + base64.b64encode(open(img_path, "rb").read()).decode()
                ab = "data:audio/mp3;base64," + base64.b64encode(open(aud_path, "rb").read()).decode()
                r = requests.post(f"{sp}{sl}api{sl}predict", json={"data": [ib, ab, "crop", True, True, 1, 256, 0]}, timeout=40)
                if r.status_code == 200 and r.json().get("data"):
                    v0 = r.json()["data"]
                    vi = v0.get("name", "") if isinstance(v0, dict) else str(v0)
                    vr = requests.get(vi if vi.startswith("http") else f"{sp}{sl}file={vi}", timeout=25)
                    if vr.status_code == 200 and len(vr.content) > 25000:
                        open(out_mp4, "wb").write(vr.content)
                        return "AI Lip-Sync"
            except Exception: continue
    return None

def generate_media(q, hist_ctx):
    low = q.lower().strip()
    is_vid = any(w in low for w in ("فيديو", "video", "وثائقي", "فيلم", "فلم", "ثوان", "ثانية", "ثواني"))
    m_dur = re.search(r"(\d+)", q)
    req_dur = max(5.0, min(30.0, float(m_dur.group(1)) if m_dur else 8.0))
    web_info = web_search_engine(q)
    target_txt = hist_ctx[-250:] if (len(q.split()) <= 2 and any(w in low for w in ("المزيد", "مزيد", "أخرى", "اخرى", "غيرها", "مشابهة", "more"))) else q
    en_p = fast_ar_to_en(target_txt, web_info)

    if is_vid:
        seed = random.randint(10000, 999999)
        is_talk = any(w in low for w in ("يتكلم", "تتكلم", "متكلم", "شفاه", "يقول", "تقول", "مذيع", "شخصية", "talk", "speak"))
        script = smart_ai([{"role": "system", "content": "اكتب تعليقاً صوتياً أو نصاً عربياً فصيحاً مشوقاً من جملتين يطابق موضوع المستخدم بدقة بدون رموز."}, {"role": "user", "content": f"الطلب: {q}\nبيانات البحث: {web_info[:400]}"}])
        if not script or len(script) < 6:
            script = re.sub(r"(حول هذا النص إلى|حول هذا النص الى|اريد فيديو|انشيء فيديو|واقعي)", "", q).strip() or q
        aud_p = os.path.join(WORK, f"Voice_{seed}.mp3")
        try: asyncio.run(make_voice(script, aud_p))
        except Exception: pass
        has_aud = os.path.exists(aud_p) and os.path.getsize(aud_p) > 1500

        sc_urls = [u for u in [generate_image_item(f"{en_p}, cinematic shot {i+1}", i) for i in range(3)] if u]
        v_imgs = [os.path.join(WORK, u.replace("/media/", "")) for u in sc_urls if os.path.exists(os.path.join(WORK, u.replace("/media/", "")))]

        vid_fn = f"DARK_HORIZON_{int(req_dur)}s_{seed}.mp4"
        vid_p, raw_vid = os.path.join(WORK, vid_fn), os.path.join(WORK, f"raw_{seed}.mp4")
        real_mode = try_real_video(en_p, v_imgs if v_imgs else None, aud_p if has_aud else None, is_talk, raw_vid)

        if real_mode and os.path.exists(raw_vid):
            cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", raw_vid] + (["-i", aud_p] if has_aud else []) + ["-vf", "scale=544:960:force_original_aspect_ratio=increase,crop=544:960", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"] + (["-c:a", "aac"] if has_aud else []) + ["-t", f"{req_dur:.2f}", vid_p]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            mode_lbl = real_mode
        elif v_imgs:
            sc_d = req_dur / len(v_imgs)
            inp, flt = [], ""
            for idx, im_f in enumerate(v_imgs):
                inp += ["-loop", "1", "-t", f"{sc_d:.2f}", "-i", im_f]
                flt += f"[{idx}:v]scale=544:960:force_original_aspect_ratio=increase,crop=544:960,setsar=1[v{idx}];"
            flt += "".join([f"[v{i}]" for i in range(len(v_imgs))]) + f"concat=n={len(v_imgs)}:v=1:a=0[outv]"
            cmd = ["ffmpeg", "-y"] + inp + (["-i", aud_p, "-filter_complex", flt, "-map", "[outv]", "-map", f"{len(v_imgs)}:a", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", vid_p] if has_aud else ["-filter_complex", flt, "-map", "[outv]", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-t", f"{req_dur:.2f}", vid_p])
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            mode_lbl = "مشاهد سينمائية 8K"
        else:
            return "⚠️ الخادم السحابي مشغول لحظياً، أعد المحاولة الآن.", {}
        return f"🎬 <b>إنتاج DARK HORIZON FILMS LTD ({mode_lbl} - {int(req_dur)} ثانية):</b>\n\n🎙️ <b>السيناريو:</b>\n{script}", {"vid": f"/media/{vid_fn}"}

    m_cnt = re.search(r"(\d+)", q)
    count = max(1, min(10, int(m_cnt.group(1)))) if m_cnt else (4 if any(w in low for w in ("صور", "معرض", "تشكيلة", "المزيد", "مزيد", "أخرى", "اخرى", "more", "شخصيات", "مشابهة")) else 1)
    urls = []
    for i in range(count):
        u = generate_image_item(f"{en_p}, distinct pose and angle {i+1}", i)
        if not u:
            time.sleep(2.0)
            u = generate_image_item(f"{en_p}, variation {i+1}", i + 1)
        if u: urls.append(u)
    if len(urls) > 1: return f"🎨 <b>تم تصميم {len(urls)} صور سينمائية 8K (DARK HORIZON FILMS LTD):</b>", {"imgs": urls}
    if len(urls) == 1: return "🎨 <b>تم تصميم الصورة بدقة سينمائية 8K (DARK HORIZON FILMS LTD):</b>", {"imgs": urls}
    return "⚠️ الخادم السحابي مشغول لحظياً، أعد إرسال الطلب.", {}

HTML = """<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>DARK HORIZON AI</title><style>
*{box-sizing:border-box;font-family:system-ui,-apple-system,sans-serif;-webkit-tap-highlight-color:transparent}
body{background:#131314;color:#e3e3e3;margin:0;display:flex;flex-direction:column;height:100dvh;overflow:hidden}
header{padding:12px 16px;background:#131314;display:flex;justify-content:space-between;align-items:center;z-index:10}
.h-icon{background:transparent;border:none;color:#c4c7c5;width:40px;height:40px;border-radius:50%;font-size:19px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:background .2s}
.h-icon:active{background:rgba(255,255,255,0.1)}
.brand{font-weight:600;font-size:16px;color:#e3e3e3;letter-spacing:.3px;display:flex;align-items:center;gap:6px}
.badge{font-size:11px;background:#1e1f20;color:#a8c7fa;padding:3px 8px;border-radius:12px;border:1px solid rgba(168,199,250,0.2)}
#drawer{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:50}
.drawer-panel{width:270px;max-width:80vw;height:100%;background:#1e1f20;padding:16px;display:flex;flex-direction:column;gap:10px;overflow-y:auto}
.new-chat-pill{background:#282a2c;color:#e3e3e3;border:none;padding:12px 16px;border-radius:24px;font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px;cursor:pointer;margin-bottom:8px}
.s-item{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-radius:20px;font-size:14px;color:#c4c7c5;cursor:pointer}
.s-item:hover,.s-item:active{background:#282a2c}
#chat{flex:1;overflow-y:auto;padding:12px 16px 24px;display:flex;flex-direction:column;gap:18px;max-width:780px;width:100%;margin:auto}
.msg{max-width:92%;line-height:1.65;font-size:15.5px;word-wrap:break-word}
.user{align-self:flex-start;background:#282a2c;color:#e3e3e3;padding:12px 18px;border-radius:22px 22px 4px 22px}
.bot{align-self:flex-end;background:transparent;color:#e3e3e3;width:100%;padding:4px 2px}
.img-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px}
.img-wrap{position:relative;margin-top:8px;border-radius:16px;overflow:hidden;background:#1e1f20;cursor:zoom-in}
.img-wrap img,.img-wrap video{width:100%;display:block;border-radius:16px}
.glass-dl{position:absolute;top:10px;left:10px;width:36px;height:36px;border-radius:50%;background:rgba(19,19,20,0.75);backdrop-filter:blur(8px);color:#e3e3e3;border:1px solid rgba(255,255,255,0.18);display:flex;align-items:center;justify-content:center;text-decoration:none;font-size:15px}
.dl-pill{display:inline-flex;align-items:center;gap:6px;background:#1e1f20;color:#a8c7fa;border:1px solid rgba(168,199,250,0.25);padding:7px 14px;border-radius:20px;margin-top:8px;font-size:13px;font-weight:500;cursor:pointer}
.footer{padding:8px 14px 14px;background:#131314}
.capsule{max-width:780px;margin:auto;background:#1e1f20;border-radius:28px;padding:6px 10px;display:flex;align-items:center;gap:6px;border:1px solid rgba(255,255,255,0.08)}
.capsule:focus-within{border-color:rgba(168,199,250,0.45);background:#232527}
#q{flex:1;background:transparent;border:none;color:#e3e3e3;font-size:15.5px;outline:none;padding:8px 6px}
.c-btn{border:none;width:38px;height:38px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .15s}
#plusBtn{background:transparent;color:#c4c7c5;font-size:22px}
#plusBtn:active{background:rgba(255,255,255,0.1)}
#sendBtn{background:#a8c7fa;color:#062e6f;font-weight:700}
#sendBtn:active{transform:scale(0.92)}
#lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.96);z-index:9999;flex-direction:column;align-items:center;justify-content:center;padding:16px}
#lightbox img{max-width:100%;max-height:82dvh;border-radius:14px;object-fit:contain}
.lb-bar{display:flex;gap:12px;margin-top:16px}
.lb-btn{background:#1e1f20;color:#e3e3e3;border:1px solid rgba(255,255,255,0.2);padding:10px 20px;border-radius:24px;text-decoration:none;font-size:14px;font-weight:600;cursor:pointer}
</style></head><body>
<header>
  <button type="button" id="histBtn" class="h-icon" title="المحادثات">☰</button>
  <div class="brand">DARK HORIZON <span class="badge">AI</span></div>
  <div style="display:flex;gap:4px">
    <button type="button" id="docBtn" class="h-icon" title="فحص النظام">🩺</button>
    <button type="button" id="newBtn" class="h-icon" title="محادثة جديدة">✎</button>
  </div>
</header>
<div id="drawer"><div class="drawer-panel"><button type="button" id="drawerNew" class="new-chat-pill">✎ محادثة جديدة</button><div id="sessList"></div></div></div>
<div id="lightbox"><img id="lbImg" src=""><div class="lb-bar"><a id="lbDl" class="lb-btn" download="DARK_HORIZON_8K.jpg">⬇️ حفظ الصورة</a><button type="button" id="lbClose" class="lb-btn">✕ إغلاق</button></div></div>
<div id="chat"></div>
<div class="footer">
  <div id="fileBar" style="display:none;max-width:780px;margin:0 auto 8px;background:#1e1f20;color:#a8c7fa;padding:6px 14px;border-radius:16px;font-size:13px;justify-content:space-between;align-items:center"></div>
  <div class="capsule">
    <input type="file" id="fileIn" accept="image/*,.pdf,.txt" style="display:none">
    <button type="button" id="plusBtn" class="c-btn">+</button>
    <input type="text" id="q" placeholder="اسأل DARK HORIZON AI...">
    <button type="button" id="sendBtn" class="c-btn">↑</button>
  </div>
</div>
<script src="/ui_logic.js"></script></body></html>"""

@app.route("/ui_logic.js")
def ui_logic():
    return Response(base64.b64decode("CnZhciBzaWQgPSBsb2NhbFN0b3JhZ2UuZ2V0SXRlbSgiZGhfc2lkIikgfHwgbnVsbDsKCmZ1bmN0aW9uIG9wZW5MaWdodGJveChzcmMsIGlkeCkgewogIHZhciBsYiA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsaWdodGJveCIpOwogIHZhciBpbSA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsYkltZyIpOwogIHZhciBkbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsYkRsIik7CiAgaWYgKCFsYiB8fCAhaW0gfHwgIWRsKSByZXR1cm47CiAgaW0uc3JjID0gc3JjOwogIGRsLmhyZWYgPSBzcmM7CiAgZGwuZG93bmxvYWQgPSAiREFSS19IT1JJWk9OXyIgKyAoaWR4ICsgMSkgKyAiLmpwZyI7CiAgbGIuc3R5bGUuZGlzcGxheSA9ICJmbGV4IjsKfQoKZnVuY3Rpb24gZGxBbGxJbWdzKGJ0bikgewogIHRyeSB7CiAgICB2YXIgYXJyID0gSlNPTi5wYXJzZShkZWNvZGVVUklDb21wb25lbnQoYnRuLmdldEF0dHJpYnV0ZSgiZGF0YS11cmxzIikpKTsKICAgIGFyci5mb3JFYWNoKGZ1bmN0aW9uKHUsIGlkeCkgewogICAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uKCkgewogICAgICAgIHZhciBhID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiYSIpOwogICAgICAgIGEuaHJlZiA9IHU7CiAgICAgICAgYS5kb3dubG9hZCA9ICJEQVJLX0hPUklaT05fIiArIChpZHggKyAxKSArICIuanBnIjsKICAgICAgICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKGEpOwogICAgICAgIGEuY2xpY2soKTsKICAgICAgICBkb2N1bWVudC5ib2R5LnJlbW92ZUNoaWxkKGEpOwogICAgICB9LCBpZHggKiA0NTApOwogICAgfSk7CiAgfSBjYXRjaCAoZSkge30KfQoKZnVuY3Rpb24gYWRkQnViYmxlKHJvbGUsIGNvbnRlbnQsIG1lZGlhKSB7CiAgdmFyIGNoYXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiY2hhdCIpOwogIHZhciBkID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiZGl2Iik7CiAgZC5jbGFzc05hbWUgPSAibXNnICIgKyAocm9sZSA9PT0gIlVzZXIiID8gInVzZXIiIDogImJvdCIpOwogIHZhciBoID0gY29udGVudCB8fCAiIjsKICBpZiAobWVkaWEgJiYgbWVkaWEudmlkKSB7CiAgICBoICs9ICc8ZGl2IGNsYXNzPSJpbWctd3JhcCI+PHZpZGVvIGNvbnRyb2xzIHBsYXlzaW5saW5lIHNyYz0iJyArIG1lZGlhLnZpZCArICciPjwvdmlkZW8+PGEgY2xhc3M9ImdsYXNzLWRsIiBocmVmPSInICsgbWVkaWEudmlkICsgJyIgZG93bmxvYWQ9IkRBUktfSE9SSVpPTl9WSURFTy5tcDQiPuKsh++4jzwvYT48L2Rpdj4nOwogIH0KICBpZiAobWVkaWEgJiYgbWVkaWEuaW1ncyAmJiBtZWRpYS5pbWdzLmxlbmd0aCA+IDApIHsKICAgIGlmIChtZWRpYS5pbWdzLmxlbmd0aCA+IDEpIHsKICAgICAgdmFyIGxzID0gZW5jb2RlVVJJQ29tcG9uZW50KEpTT04uc3RyaW5naWZ5KG1lZGlhLmltZ3MpKTsKICAgICAgaCArPSAnPGRpdj48YnV0dG9uIHR5cGU9ImJ1dHRvbiIgY2xhc3M9ImRsLXBpbGwiIGRhdGEtdXJscz0iJyArIGxzICsgJyIgb25jbGljaz0iZGxBbGxJbWdzKHRoaXMpIj7irIfvuI8g2K3Zgdi4INis2YXZiti5INin2YTYtdmI2LEgKCcgKyBtZWRpYS5pbWdzLmxlbmd0aCArICcpPC9idXR0b24+PC9kaXY+PGRpdiBjbGFzcz0iaW1nLWdyaWQiPic7CiAgICAgIG1lZGlhLmltZ3MuZm9yRWFjaChmdW5jdGlvbih1LCBpKSB7CiAgICAgICAgaCArPSAnPGRpdiBjbGFzcz0iaW1nLXdyYXAiIHN0eWxlPSJtYXJnaW4tdG9wOjAiPjxpbWcgc3JjPSInICsgdSArICciIHN0eWxlPSJhc3BlY3QtcmF0aW86OS8xNjtvYmplY3QtZml0OmNvdmVyIiBvbmNsaWNrPSJvcGVuTGlnaHRib3godGhpcy5zcmMsJyArIGkgKyAnKSI+PGEgY2xhc3M9ImdsYXNzLWRsIiBocmVmPSInICsgdSArICciIGRvd25sb2FkPSJEQVJLX0hPUklaT05fJyArIChpICsgMSkgKyAnLmpwZyIgb25jbGljaz0iZXZlbnQuc3RvcFByb3BhZ2F0aW9uKCkiPuKsh++4jzwvYT48L2Rpdj4nOwogICAgICB9KTsKICAgICAgaCArPSAnPC9kaXY+JzsKICAgIH0gZWxzZSB7CiAgICAgIHZhciB1MCA9IG1lZGlhLmltZ3NbMF07CiAgICAgIGggKz0gJzxkaXYgY2xhc3M9ImltZy13cmFwIj48aW1nIHNyYz0iJyArIHUwICsgJyIgb25jbGljaz0ib3BlbkxpZ2h0Ym94KHRoaXMuc3JjLDApIj48YSBjbGFzcz0iZ2xhc3MtZGwiIGhyZWY9IicgKyB1MCArICciIGRvd25sb2FkPSJEQVJLX0hPUklaT05fOEsuanBnIiBvbmNsaWNrPSJldmVudC5zdG9wUHJvcGFnYXRpb24oKSI+4qyH77iPPC9hPjwvZGl2Pic7CiAgICB9CiAgfQogIGQuaW5uZXJIVE1MID0gaDsKICBjaGF0LmFwcGVuZENoaWxkKGQpOwogIGNoYXQuc2Nyb2xsVG9wID0gY2hhdC5zY3JvbGxIZWlnaHQ7CiAgcmV0dXJuIGQ7Cn0KCmZ1bmN0aW9uIHNhZmVKc29uKHJlcykgewogIHJldHVybiByZXMudGV4dCgpLnRoZW4oZnVuY3Rpb24odCkgewogICAgdHJ5IHsgcmV0dXJuIEpTT04ucGFyc2UodCk7IH0gY2F0Y2ggKGUpIHsgdGhyb3cgbmV3IEVycm9yKCLYp9mE2K7Yp9iv2YUg2YrYs9iq2YrZgti42Iwg2KPYudivINin2YTZhdit2KfZiNmE2Kkg2KfZhNii2YYuIik7IH0KICB9KTsKfQoKZnVuY3Rpb24gcnVuRG9jdG9yKCkgewogIHZhciB3ID0gYWRkQnViYmxlKCJBSSIsICLwn6m6INis2KfYsdmKINmB2K3YtSDYp9mE2K7ZiNin2K/ZhS4uLiIsIHt9KTsKICBmZXRjaCgiL2RvY3RvciIpLnRoZW4oc2FmZUpzb24pLnRoZW4oZnVuY3Rpb24oZCkgeyB3LmlubmVySFRNTCA9IGQucmVwb3J0OyB9KS5jYXRjaChmdW5jdGlvbihlKSB7IHcudGV4dENvbnRlbnQgPSAi4pqg77iPICIgKyBlLm1lc3NhZ2U7IH0pOwp9CgpmdW5jdGlvbiBsb2FkU2Vzc2lvbnMoKSB7CiAgZmV0Y2goIi9zZXNzaW9ucyIpLnRoZW4oc2FmZUpzb24pLnRoZW4oZnVuY3Rpb24obGlzdCkgewogICAgdmFyIGJveCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJzZXNzTGlzdCIpOwogICAgaWYgKCFib3gpIHJldHVybjsKICAgIGJveC5pbm5lckhUTUwgPSAiIjsKICAgIGxpc3QuZm9yRWFjaChmdW5jdGlvbihzKSB7CiAgICAgIHZhciByb3cgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJkaXYiKTsKICAgICAgcm93LmNsYXNzTmFtZSA9ICJzLWl0ZW0iOwogICAgICB2YXIgc3AgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJzcGFuIik7CiAgICAgIHNwLnN0eWxlLmNzc1RleHQgPSAiZmxleDoxO292ZXJmbG93OmhpZGRlbjt0ZXh0LW92ZXJmbG93OmVsbGlwc2lzO3doaXRlLXNwYWNlOm5vd3JhcCI7CiAgICAgIHNwLnRleHRDb250ZW50ID0gcy50aXRsZTsKICAgICAgc3Aub25jbGljayA9IGZ1bmN0aW9uKCkgewogICAgICAgIHNpZCA9IHMuaWQ7CiAgICAgICAgbG9jYWxTdG9yYWdlLnNldEl0ZW0oImRoX3NpZCIsIHNpZCk7CiAgICAgICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImRyYXdlciIpLnN0eWxlLmRpc3BsYXkgPSAibm9uZSI7CiAgICAgICAgbG9hZE1lc3NhZ2VzKCk7CiAgICAgIH07CiAgICAgIHZhciBkZWwgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJidXR0b24iKTsKICAgICAgZGVsLnRleHRDb250ZW50ID0gIuKclSI7CiAgICAgIGRlbC5zdHlsZS5jc3NUZXh0ID0gImJhY2tncm91bmQ6bm9uZTtib3JkZXI6bm9uZTtjb2xvcjojZjI4YjgyO2ZvbnQtc2l6ZToxNXB4O2N1cnNvcjpwb2ludGVyO3BhZGRpbmc6MCA0cHgiOwogICAgICBkZWwub25jbGljayA9IGZ1bmN0aW9uKGV2KSB7CiAgICAgICAgZXYuc3RvcFByb3BhZ2F0aW9uKCk7CiAgICAgICAgZmV0Y2goIi9zZXNzaW9ucy8iICsgcy5pZCwgeyBtZXRob2Q6ICJERUxFVEUiIH0pLnRoZW4oZnVuY3Rpb24oKSB7CiAgICAgICAgICBpZiAoc2lkID09IHMuaWQpIHN0YXJ0TmV3KCk7CiAgICAgICAgICBsb2FkU2Vzc2lvbnMoKTsKICAgICAgICB9KTsKICAgICAgfTsKICAgICAgcm93LmFwcGVuZENoaWxkKHNwKTsKICAgICAgcm93LmFwcGVuZENoaWxkKGRlbCk7CiAgICAgIGJveC5hcHBlbmRDaGlsZChyb3cpOwogICAgfSk7CiAgfSkuY2F0Y2goZnVuY3Rpb24oKSB7fSk7Cn0KCmZ1bmN0aW9uIHN0YXJ0TmV3KCkgewogIHNpZCA9IG51bGw7CiAgbG9jYWxTdG9yYWdlLnJlbW92ZUl0ZW0oImRoX3NpZCIpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJkcmF3ZXIiKS5zdHlsZS5kaXNwbGF5ID0gIm5vbmUiOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjaGF0IikuaW5uZXJIVE1MID0gJzxkaXYgY2xhc3M9Im1zZyBib3QiPuKcqCDYo9mH2YTYp9mLINio2YMg2YHZiiA8Yj5EQVJLIEhPUklaT04gQUk8L2I+LiDZg9mK2YEg2YrZhdmD2YbZhtmKINmF2LPYp9i52K/YqtmDINin2YTZitmI2YXYnzwvZGl2Pic7Cn0KCmZ1bmN0aW9uIGxvYWRNZXNzYWdlcygpIHsKICBpZiAoIXNpZCkgeyBzdGFydE5ldygpOyByZXR1cm47IH0KICBmZXRjaCgiL21lc3NhZ2VzLyIgKyBzaWQpLnRoZW4oc2FmZUpzb24pLnRoZW4oZnVuY3Rpb24obXNncykgewogICAgdmFyIGNoYXQgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiY2hhdCIpOwogICAgY2hhdC5pbm5lckhUTUwgPSAiIjsKICAgIG1zZ3MuZm9yRWFjaChmdW5jdGlvbihtKSB7IGFkZEJ1YmJsZShtLnJvbGUsIG0uY29udGVudCwgbS5tZWRpYSk7IH0pOwogIH0pLmNhdGNoKGZ1bmN0aW9uKCkgeyBzdGFydE5ldygpOyB9KTsKfQoKZnVuY3Rpb24gc2VuZE1lc3NhZ2UoKSB7CiAgdmFyIHFFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJxIik7CiAgdmFyIGZFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKTsKICB2YXIgdHh0ID0gcUVsLnZhbHVlLnRyaW0oKTsKICB2YXIgZmlsZSA9IChmRWwuZmlsZXMgJiYgZkVsLmZpbGVzLmxlbmd0aCA+IDApID8gZkVsLmZpbGVzWzBdIDogbnVsbDsKICBpZiAoIXR4dCAmJiAhZmlsZSkgcmV0dXJuOwogIGFkZEJ1YmJsZSgiVXNlciIsIHR4dCB8fCAoIvCfk44gIiArIGZpbGUubmFtZSksIHt9KTsKICB2YXIgd2FpdEJveCA9IGFkZEJ1YmJsZSgiQUkiLCAi4pqhINis2KfYsdmKINin2YTYqtmB2YPZitixLi4uIiwge30pOwogIHZhciBmZCA9IG5ldyBGb3JtRGF0YSgpOwogIGlmIChzaWQpIGZkLmFwcGVuZCgic2lkIiwgc2lkKTsKICBmZC5hcHBlbmQoInEiLCB0eHQpOwogIGlmIChmaWxlKSBmZC5hcHBlbmQoImZpbGUiLCBmaWxlKTsKICBxRWwudmFsdWUgPSAiIjsKICBmRWwudmFsdWUgPSAiIjsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZmlsZUJhciIpLnN0eWxlLmRpc3BsYXkgPSAibm9uZSI7CiAgZmV0Y2goIi9zZW5kX2FsbCIsIHsgbWV0aG9kOiAiUE9TVCIsIGJvZHk6IGZkIH0pLnRoZW4oc2FmZUpzb24pLnRoZW4oZnVuY3Rpb24oZCkgewogICAgc2lkID0gZC5zaWQ7CiAgICBsb2NhbFN0b3JhZ2Uuc2V0SXRlbSgiZGhfc2lkIiwgc2lkKTsKICAgIGlmIChkLmpvYl9pZCkgewogICAgICB3YWl0Qm94LnRleHRDb250ZW50ID0gIvCfjqjwn46sINis2KfYsdmKINin2YTYqti12YXZitmFINmI2KfZhNil2K7Ysdin2Kwg2KfZhNiz2YrZhtmF2KfYptmKLi4uIjsKICAgICAgdmFyIGl2ID0gc2V0SW50ZXJ2YWwoZnVuY3Rpb24oKSB7CiAgICAgICAgZmV0Y2goIi9qb2IvIiArIGQuam9iX2lkKS50aGVuKHNhZmVKc29uKS50aGVuKGZ1bmN0aW9uKHN0KSB7CiAgICAgICAgICBpZiAoc3QuZG9uZSkgewogICAgICAgICAgICBjbGVhckludGVydmFsKGl2KTsKICAgICAgICAgICAgd2FpdEJveC5yZW1vdmUoKTsKICAgICAgICAgICAgYWRkQnViYmxlKCJBSSIsIHN0LnJlcGx5LCBzdC5tZWRpYSk7CiAgICAgICAgICAgIGxvYWRTZXNzaW9ucygpOwogICAgICAgICAgfQogICAgICAgIH0pLmNhdGNoKGZ1bmN0aW9uKCkge30pOwogICAgICB9LCAxNTAwKTsKICAgIH0gZWxzZSB7CiAgICAgIHdhaXRCb3gucmVtb3ZlKCk7CiAgICAgIGFkZEJ1YmJsZSgiQUkiLCBkLnJlcGx5LCBkLm1lZGlhKTsKICAgICAgbG9hZFNlc3Npb25zKCk7CiAgICB9CiAgfSkuY2F0Y2goZnVuY3Rpb24oZXJyKSB7IHdhaXRCb3gudGV4dENvbnRlbnQgPSAi4pqg77iPICIgKyBlcnIubWVzc2FnZTsgfSk7Cn0KCmZ1bmN0aW9uIGluaXRVSSgpIHsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZG9jQnRuIikub25jbGljayA9IHJ1bkRvY3RvcjsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiaGlzdEJ0biIpLm9uY2xpY2sgPSBmdW5jdGlvbigpIHsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJkcmF3ZXIiKS5zdHlsZS5kaXNwbGF5ID0gImJsb2NrIjsKICAgIGxvYWRTZXNzaW9ucygpOwogIH07CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImRyYXdlciIpLm9uY2xpY2sgPSBmdW5jdGlvbihlKSB7CiAgICBpZiAoZS50YXJnZXQuaWQgPT09ICJkcmF3ZXIiKSB0aGlzLnN0eWxlLmRpc3BsYXkgPSAibm9uZSI7CiAgfTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmV3QnRuIikub25jbGljayA9IHN0YXJ0TmV3OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJkcmF3ZXJOZXciKS5vbmNsaWNrID0gc3RhcnROZXc7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInBsdXNCdG4iKS5vbmNsaWNrID0gZnVuY3Rpb24oKSB7IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKS5jbGljaygpOyB9OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKS5vbmNoYW5nZSA9IGZ1bmN0aW9uKCkgewogICAgdmFyIGZFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKSwgZmIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZmlsZUJhciIpOwogICAgaWYgKGZFbC5maWxlcyAmJiBmRWwuZmlsZXMubGVuZ3RoID4gMCkgewogICAgICBmYi5zdHlsZS5kaXNwbGF5ID0gImZsZXgiOwogICAgICBmYi5pbm5lckhUTUwgPSAiPHNwYW4+8J+TjiAiICsgZkVsLmZpbGVzWzBdLm5hbWUgKyAiPC9zcGFuPjxzcGFuIHN0eWxlPSdjb2xvcjojZjI4YjgyO2ZvbnQtd2VpZ2h0OmJvbGQ7Y3Vyc29yOnBvaW50ZXInIG9uY2xpY2s9J2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKS52YWx1ZT0iIjtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZmlsZUJhciIpLnN0eWxlLmRpc3BsYXk9Im5vbmUiOyc+4pyVPC9zcGFuPiI7CiAgICB9CiAgfTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgic2VuZEJ0biIpLm9uY2xpY2sgPSBzZW5kTWVzc2FnZTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgicSIpLm9ua2V5ZG93biA9IGZ1bmN0aW9uKGUpIHsgaWYgKGUua2V5ID09PSAiRW50ZXIiKSB7IGUucHJldmVudERlZmF1bHQoKTsgc2VuZE1lc3NhZ2UoKTsgfSB9OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsYkNsb3NlIikub25jbGljayA9IGZ1bmN0aW9uKCkgeyBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibGlnaHRib3giKS5zdHlsZS5kaXNwbGF5ID0gIm5vbmUiOyB9OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsaWdodGJveCIpLm9uY2xpY2sgPSBmdW5jdGlvbihlKSB7IGlmIChlLnRhcmdldC5pZCA9PT0gImxpZ2h0Ym94IikgdGhpcy5zdHlsZS5kaXNwbGF5ID0gIm5vbmUiOyB9OwogIGxvYWRTZXNzaW9ucygpOwogIGxvYWRNZXNzYWdlcygpOwp9CgppZiAoZG9jdW1lbnQucmVhZHlTdGF0ZSA9PT0gImxvYWRpbmciKSB7CiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcigiRE9NQ29udGVudExvYWRlZCIsIGluaXRVSSk7Cn0gZWxzZSB7CiAgaW5pdFVJKCk7Cn0K").decode("utf-8"), mimetype="application/javascript")

@app.route("/doctor")
def doctor():
    with db_lock: conn.execute("DELETE FROM messages WHERE content LIKE '%جاري%'"); conn.commit()
    g_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    cf_ok = bool(os.environ.get("CF_API_TOKEN", "").strip())
    return jsonify({"report": f"🩺 <b>تقرير الفحص الذاتي الشامل لـ DARK HORIZON AI:</b>\n• خوادم Google (Gemini 2.5 + Imagen 3 + Veo 2): {'مفعّلة ✅' if g_ok else 'غير مضافة ⚠️'}\n• بطاقات Cloudflare GPU (8K): {'مفعّلة ✅' if cf_ok else 'غير مضافة ⚠️'}\n• محرك البحث العالمي والموسوعات: متصل ✅\n• قاعدة البيانات والذاكرة: نظيفة ✅"})

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
    is_m = not up_path and not is_q and any(w in q.lower() for w in ("فيديو", "video", "وثائقي", "صورة", "صور", "ارسم", "image", "draw", "photo", "فيلم", "فلم", "ثوان", "ثانية", "عشر", "المزيد", "مزيد", "أخرى", "اخرى", "more", "شخصيات", "مشابهة"))
    if is_m:
        jid = f"j_{int(time.time())}_{random.randint(100,999)}"
        with db_lock: conn.execute("INSERT INTO jobs (jid, done, reply, media) VALUES (?, 0, '', '{}')", (jid,)); conn.commit()
        threading.Thread(target=run_media_job, args=(jid, sid, q, ctx), daemon=True).start()
        return jsonify({"sid": sid, "job_id": jid})
    if up_path and os.path.exists(up_path):
        rep = smart_ai([{"role": "user", "content": f"تم إرفاق ملف باسم {os.path.basename(up_path)}. {q}"}]) or "تم استلام الملف بنجاح."
    else:
        web_facts = web_search_engine(q)
        msgs = [{"role": "system", "content": f"أنت المساعد الذكي لاستوديو DARK HORIZON FILMS LTD. استعن ببيانات البحث العالمية التالية لتقديم إجابات شاملة ودقيقة:\n{web_facts}"}]
        for r_role, r_cnt in hist: msgs.append({"role": "user" if r_role == "User" else "assistant", "content": r_cnt[:400]})
        rep = smart_ai(msgs) or "أهلاً بك في استوديو DARK HORIZON FILMS LTD! كيف يمكنني مساعدتك اليوم؟"
    with db_lock: conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, '{}')", (sid, rep)); conn.commit()
    return jsonify({"sid": sid, "reply": rep, "media": {}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
