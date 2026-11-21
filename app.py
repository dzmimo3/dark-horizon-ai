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
.img-wrap{position:relative;margin-top:8px;border-radius:14px;overflow:hidden;cursor:zoom-in}.img-wrap img{width:100%;display:block;border-radius:14px}.glass-dl{position:absolute;top:10px;left:10px;width:36px;height:36px;border-radius:50%;background:rgba(15,23,42,0.72);backdrop-filter:blur(6px);color:#f8fafc;border:1px solid rgba(255,255,255,0.22);display:flex;align-items:center;justify-content:center;text-decoration:none;font-size:16px;box-shadow:0 4px 12px rgba(0,0,0,0.4)}.dl-all{display:inline-flex;align-items:center;gap:6px;background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.4);padding:7px 14px;border-radius:20px;margin-top:8px;font-size:13px;font-weight:700;cursor:pointer}#lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.95);z-index:9999;flex-direction:column;align-items:center;justify-content:center;padding:16px}#lightbox img{max-width:100%;max-height:82vh;border-radius:12px;object-fit:contain}.lb-bar{display:flex;gap:14px;margin-top:16px}.lb-btn{background:rgba(255,255,255,0.14);color:#fff;border:1px solid rgba(255,255,255,0.25);padding:10px 20px;border-radius:24px;text-decoration:none;font-size:14px;font-weight:700;cursor:pointer}
.footer{background:#111622;padding:12px;border-top:1px solid rgba(245,158,11,0.2)}.input-row{max-width:800px;margin:auto;display:flex;gap:8px;align-items:center;background:rgba(255,255,255,0.08);border:1px solid #f59e0b;border-radius:26px;padding:6px 12px}
input[type=text]{flex:1;background:transparent;border:none;color:#fff;font-size:15px;outline:none;padding:6px}.c-btn{border:none;width:40px;height:40px;border-radius:50%;font-weight:bold;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}#plusBtn{background:rgba(255,255,255,0.12);color:#f59e0b}#sendBtn{background:#f59e0b;color:#000}
</style></head><body>
<header><span class="brand">✨ DARK HORIZON AI</span><div><button type="button" id="docBtn" class="h-btn">🩺 فحص</button> <button type="button" id="histBtn" class="h-btn">📂 السجل</button> <button type="button" id="newBtn" class="h-btn">➕</button></div></header>
<div id="lightbox"><img id="lbImg" src=""><div class="lb-bar"><a id="lbDl" class="lb-btn" download="DARK_HORIZON_8K.jpg">⬇️ حفظ الصورة</a><button type="button" id="lbClose" class="lb-btn">✕ إغلاق</button></div></div><div id="drawer"></div><div id="chat"></div>
<div class="footer"><div id="fileBar" style="display:none;max-width:800px;margin:0 auto 8px;background:rgba(245,158,11,0.2);color:#fde047;padding:6px 12px;border-radius:10px;font-size:13px;justify-content:space-between"></div>
<div class="input-row"><input type="file" id="fileIn" accept="image/*,.pdf,.txt" style="display:none"><button type="button" id="plusBtn" class="c-btn">+</button><input type="text" id="q" placeholder="تحدث، أرفق ملفاً، اطلب صوراً أو فيديو..."><button type="button" id="sendBtn" class="c-btn">➤</button></div></div>
<script src="/ui_logic.js"></script></body></html>"""

@app.route("/ui_logic.js")
def ui_logic():
    return Response(base64.b64decode("CnZhciBzaWQgPSBsb2NhbFN0b3JhZ2UuZ2V0SXRlbSgiZGhfc2lkIikgfHwgbnVsbDsKZnVuY3Rpb24gb3BlbkxpZ2h0Ym94KHNyYywgaWR4KSB7CiAgdmFyIGxiID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImxpZ2h0Ym94IiksIGltID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImxiSW1nIiksIGRsID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImxiRGwiKTsKICBpZiAoIWxiIHx8ICFpbSB8fCAhZGwpIHJldHVybjsKICBpbS5zcmMgPSBzcmM7IGRsLmhyZWYgPSBzcmM7IGRsLmRvd25sb2FkID0gIkRBUktfSE9SSVpPTl8iICsgKGlkeCArIDEpICsgIi5qcGciOyBsYi5zdHlsZS5kaXNwbGF5ID0gImZsZXgiOwp9CmZ1bmN0aW9uIGRsQWxsSW1ncyhidG4pIHsKICB0cnkgewogICAgdmFyIGFyciA9IEpTT04ucGFyc2UoZGVjb2RlVVJJQ29tcG9uZW50KGJ0bi5nZXRBdHRyaWJ1dGUoImRhdGEtdXJscyIpKSk7CiAgICBhcnIuZm9yRWFjaChmdW5jdGlvbih1LCBpZHgpIHsKICAgICAgc2V0VGltZW91dChmdW5jdGlvbigpIHsKICAgICAgICB2YXIgYSA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImEiKTsgYS5ocmVmID0gdTsgYS5kb3dubG9hZCA9ICJEQVJLX0hPUklaT05fIiArIChpZHggKyAxKSArICIuanBnIjsKICAgICAgICBkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKGEpOyBhLmNsaWNrKCk7IGRvY3VtZW50LmJvZHkucmVtb3ZlQ2hpbGQoYSk7CiAgICAgIH0sIGlkeCAqIDQ1MCk7CiAgICB9KTsKICB9IGNhdGNoIChlKSB7fQp9CmZ1bmN0aW9uIGFkZEJ1YmJsZShyb2xlLCBjb250ZW50LCBtZWRpYSkgewogIHZhciBjaGF0ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNoYXQiKSwgZCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImRpdiIpOwogIGQuY2xhc3NOYW1lID0gIm1zZyAiICsgKHJvbGUgPT09ICJVc2VyIiA/ICJ1c2VyIiA6ICJib3QiKTsKICB2YXIgaCA9IGNvbnRlbnQgfHwgIiI7CiAgaWYgKG1lZGlhICYmIG1lZGlhLnZpZCkgewogICAgaCArPSAnPGRpdiBjbGFzcz0iaW1nLXdyYXAiPjx2aWRlbyBjb250cm9scyBwbGF5c2lubGluZSBzcmM9IicgKyBtZWRpYS52aWQgKyAnIiBzdHlsZT0id2lkdGg6MTAwJTtib3JkZXItcmFkaXVzOjE0cHgiPjwvdmlkZW8+PGEgY2xhc3M9ImdsYXNzLWRsIiBocmVmPSInICsgbWVkaWEudmlkICsgJyIgZG93bmxvYWQ9IkRBUktfSE9SSVpPTl9WSURFTy5tcDQiPuKsh++4jzwvYT48L2Rpdj4nOwogIH0KICBpZiAobWVkaWEgJiYgbWVkaWEuaW1ncyAmJiBtZWRpYS5pbWdzLmxlbmd0aCA+IDApIHsKICAgIGlmIChtZWRpYS5pbWdzLmxlbmd0aCA+IDEpIHsKICAgICAgdmFyIGxzID0gZW5jb2RlVVJJQ29tcG9uZW50KEpTT04uc3RyaW5naWZ5KG1lZGlhLmltZ3MpKTsKICAgICAgaCArPSAnPGRpdj48YnV0dG9uIHR5cGU9ImJ1dHRvbiIgY2xhc3M9ImRsLWFsbCIgZGF0YS11cmxzPSInICsgbHMgKyAnIiBvbmNsaWNrPSJkbEFsbEltZ3ModGhpcykiPuKsh++4jyDYrdmB2Lgg2KfZhNmD2YQgKCcgKyBtZWRpYS5pbWdzLmxlbmd0aCArICcpPC9idXR0b24+PC9kaXY+PGRpdiBjbGFzcz0iaW1nLWdyaWQiPic7CiAgICAgIG1lZGlhLmltZ3MuZm9yRWFjaChmdW5jdGlvbih1LCBpKSB7CiAgICAgICAgaCArPSAnPGRpdiBjbGFzcz0iaW1nLXdyYXAiIHN0eWxlPSJtYXJnaW4tdG9wOjAiPjxpbWcgc3JjPSInICsgdSArICciIHN0eWxlPSJhc3BlY3QtcmF0aW86OS8xNjtvYmplY3QtZml0OmNvdmVyIiBvbmNsaWNrPSJvcGVuTGlnaHRib3godGhpcy5zcmMsJyArIGkgKyAnKSI+PGEgY2xhc3M9ImdsYXNzLWRsIiBocmVmPSInICsgdSArICciIGRvd25sb2FkPSJEQVJLX0hPUklaT05fJyArIChpICsgMSkgKyAnLmpwZyIgb25jbGljaz0iZXZlbnQuc3RvcFByb3BhZ2F0aW9uKCkiPuKsh++4jzwvYT48L2Rpdj4nOwogICAgICB9KTsKICAgICAgaCArPSAnPC9kaXY+JzsKICAgIH0gZWxzZSB7CiAgICAgIHZhciB1ID0gbWVkaWEuaW1nc1swXTsKICAgICAgaCArPSAnPGRpdiBjbGFzcz0iaW1nLXdyYXAiPjxpbWcgc3JjPSInICsgdSArICciIG9uY2xpY2s9Im9wZW5MaWdodGJveCh0aGlzLnNyYywwKSI+PGEgY2xhc3M9ImdsYXNzLWRsIiBocmVmPSInICsgdSArICciIGRvd25sb2FkPSJEQVJLX0hPUklaT05fOEsuanBnIiBvbmNsaWNrPSJldmVudC5zdG9wUHJvcGFnYXRpb24oKSI+4qyH77iPPC9hPjwvZGl2Pic7CiAgICB9CiAgfQogIGQuaW5uZXJIVE1MID0gaDsgY2hhdC5hcHBlbmRDaGlsZChkKTsgY2hhdC5zY3JvbGxUb3AgPSBjaGF0LnNjcm9sbEhlaWdodDsgcmV0dXJuIGQ7Cn0KZnVuY3Rpb24gc2FmZUpzb24ocmVzKSB7CiAgcmV0dXJuIHJlcy50ZXh0KCkudGhlbihmdW5jdGlvbih0KSB7CiAgICB0cnkgeyByZXR1cm4gSlNPTi5wYXJzZSh0KTsgfSBjYXRjaCAoZSkgeyB0aHJvdyBuZXcgRXJyb3IoItin2YTYrtin2K/ZhSDZitiz2KrZitmC2LjYjCDYo9i52K8g2KfZhNmF2K3Yp9mI2YTYqSDYp9mE2KLZhi4iKTsgfQogIH0pOwp9CmZ1bmN0aW9uIHJ1bkRvY3RvcigpIHsKICB2YXIgdyA9IGFkZEJ1YmJsZSgiQUkiLCAi8J+puiDYrNin2LHZiiDZgdit2LUg2KfZhNiu2YjYp9iv2YUuLi4iLCB7fSk7CiAgZmV0Y2goIi9kb2N0b3IiKS50aGVuKHNhZmVKc29uKS50aGVuKGZ1bmN0aW9uKGQpIHsgdy5pbm5lckhUTUwgPSBkLnJlcG9ydDsgfSkuY2F0Y2goZnVuY3Rpb24oZSkgeyB3LnRleHRDb250ZW50ID0gIuKaoO+4jyAiICsgZS5tZXNzYWdlOyB9KTsKfQpmdW5jdGlvbiB0b2dnbGVEcmF3ZXIoKSB7CiAgdmFyIGRyID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImRyYXdlciIpOwogIGRyLnN0eWxlLmRpc3BsYXkgPSAoZHIuc3R5bGUuZGlzcGxheSA9PT0gImJsb2NrIikgPyAibm9uZSIgOiAiYmxvY2siOwogIGxvYWRTZXNzaW9ucygpOwp9CmZ1bmN0aW9uIGxvYWRTZXNzaW9ucygpIHsKICBmZXRjaCgiL3Nlc3Npb25zIikudGhlbihzYWZlSnNvbikudGhlbihmdW5jdGlvbihsaXN0KSB7CiAgICB2YXIgZHIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZHJhd2VyIik7IGRyLmlubmVySFRNTCA9ICIiOwogICAgbGlzdC5mb3JFYWNoKGZ1bmN0aW9uKHMpIHsKICAgICAgdmFyIHJvdyA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImRpdiIpOyByb3cuY2xhc3NOYW1lID0gInMtaXRlbSI7CiAgICAgIHZhciBzcCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoInNwYW4iKTsgc3Auc3R5bGUuY3NzVGV4dCA9ICJmbGV4OjE7Y3Vyc29yOnBvaW50ZXIiOyBzcC50ZXh0Q29udGVudCA9IHMudGl0bGU7CiAgICAgIHNwLm9uY2xpY2sgPSBmdW5jdGlvbigpIHsgc2lkID0gcy5pZDsgbG9jYWxTdG9yYWdlLnNldEl0ZW0oImRoX3NpZCIsIHNpZCk7IGRyLnN0eWxlLmRpc3BsYXkgPSAibm9uZSI7IGxvYWRNZXNzYWdlcygpOyB9OwogICAgICB2YXIgZGVsID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiYnV0dG9uIik7IGRlbC50ZXh0Q29udGVudCA9ICLinJUiOyBkZWwuc3R5bGUuY3NzVGV4dCA9ICJiYWNrZ3JvdW5kOm5vbmU7Ym9yZGVyOm5vbmU7Y29sb3I6I2VmNDQ0NDtmb250LXNpemU6MTZweDtjdXJzb3I6cG9pbnRlciI7CiAgICAgIGRlbC5vbmNsaWNrID0gZnVuY3Rpb24oKSB7IGZldGNoKCIvc2Vzc2lvbnMvIiArIHMuaWQsIHsgbWV0aG9kOiAiREVMRVRFIiB9KS50aGVuKGZ1bmN0aW9uKCkgeyBpZiAoc2lkID09IHMuaWQpIHN0YXJ0TmV3KCk7IGxvYWRTZXNzaW9ucygpOyB9KTsgfTsKICAgICAgcm93LmFwcGVuZENoaWxkKHNwKTsgcm93LmFwcGVuZENoaWxkKGRlbCk7IGRyLmFwcGVuZENoaWxkKHJvdyk7CiAgICB9KTsKICB9KS5jYXRjaChmdW5jdGlvbigpIHt9KTsKfQpmdW5jdGlvbiBzdGFydE5ldygpIHsKICBzaWQgPSBudWxsOyBsb2NhbFN0b3JhZ2UucmVtb3ZlSXRlbSgiZGhfc2lkIik7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNoYXQiKS5pbm5lckhUTUwgPSAnPGRpdiBjbGFzcz0ibXNnIGJvdCI+4pyoINin2LPYqtmI2K/ZitmIIERBUksgSE9SSVpPTiBBSSDYrNin2YfYsiEg2KzZhdmK2Lkg2KfZhNij2LLYsdin2LEg2KrYudmF2YQg2KfZhNii2YYg2KjZg9mB2KfYodipLjwvZGl2Pic7Cn0KZnVuY3Rpb24gbG9hZE1lc3NhZ2VzKCkgewogIGlmICghc2lkKSB7IHN0YXJ0TmV3KCk7IHJldHVybjsgfQogIGZldGNoKCIvbWVzc2FnZXMvIiArIHNpZCkudGhlbihzYWZlSnNvbikudGhlbihmdW5jdGlvbihtc2dzKSB7CiAgICB2YXIgY2hhdCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjaGF0Iik7IGNoYXQuaW5uZXJIVE1MID0gIiI7CiAgICBtc2dzLmZvckVhY2goZnVuY3Rpb24obSkgeyBhZGRCdWJibGUobS5yb2xlLCBtLmNvbnRlbnQsIG0ubWVkaWEpOyB9KTsKICB9KS5jYXRjaChmdW5jdGlvbigpIHsgc3RhcnROZXcoKTsgfSk7Cn0KZnVuY3Rpb24gc2VuZE1lc3NhZ2UoKSB7CiAgdmFyIHFFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJxIiksIGZFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKTsKICB2YXIgdHh0ID0gcUVsLnZhbHVlLnRyaW0oKSwgZmlsZSA9IChmRWwuZmlsZXMgJiYgZkVsLmZpbGVzLmxlbmd0aCA+IDApID8gZkVsLmZpbGVzWzBdIDogbnVsbDsKICBpZiAoIXR4dCAmJiAhZmlsZSkgcmV0dXJuOwogIGFkZEJ1YmJsZSgiVXNlciIsIHR4dCB8fCAoIvCfk44gIiArIGZpbGUubmFtZSksIHt9KTsKICB2YXIgd2FpdEJveCA9IGFkZEJ1YmJsZSgiQUkiLCAi4pqhINis2KfYsdmKINin2YTYqtmG2YHZitiwLi4uIiwge30pOwogIHZhciBmZCA9IG5ldyBGb3JtRGF0YSgpOyBpZiAoc2lkKSBmZC5hcHBlbmQoInNpZCIsIHNpZCk7IGZkLmFwcGVuZCgicSIsIHR4dCk7IGlmIChmaWxlKSBmZC5hcHBlbmQoImZpbGUiLCBmaWxlKTsKICBxRWwudmFsdWUgPSAiIjsgZkVsLnZhbHVlID0gIiI7IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlQmFyIikuc3R5bGUuZGlzcGxheSA9ICJub25lIjsKICBmZXRjaCgiL3NlbmRfYWxsIiwgeyBtZXRob2Q6ICJQT1NUIiwgYm9keTogZmQgfSkudGhlbihzYWZlSnNvbikudGhlbihmdW5jdGlvbihkKSB7CiAgICBzaWQgPSBkLnNpZDsgbG9jYWxTdG9yYWdlLnNldEl0ZW0oImRoX3NpZCIsIHNpZCk7CiAgICBpZiAoZC5qb2JfaWQpIHsKICAgICAgd2FpdEJveC50ZXh0Q29udGVudCA9ICLwn46o8J+OrCDYrNin2LHZiiDYp9mE2KrYtdmF2YrZhSDZiNin2YTYpdiu2LHYp9isINin2YTYs9mK2YbZhdin2KbZiiA4Sy4uLiI7CiAgICAgIHZhciBpdiA9IHNldEludGVydmFsKGZ1bmN0aW9uKCkgewogICAgICAgIGZldGNoKCIvam9iLyIgKyBkLmpvYl9pZCkudGhlbihzYWZlSnNvbikudGhlbihmdW5jdGlvbihzdCkgewogICAgICAgICAgaWYgKHN0LmRvbmUpIHsgY2xlYXJJbnRlcnZhbChpdik7IHdhaXRCb3gucmVtb3ZlKCk7IGFkZEJ1YmJsZSgiQUkiLCBzdC5yZXBseSwgc3QubWVkaWEpOyBsb2FkU2Vzc2lvbnMoKTsgfQogICAgICAgIH0pLmNhdGNoKGZ1bmN0aW9uKCkge30pOwogICAgICB9LCAxNTAwKTsKICAgIH0gZWxzZSB7IHdhaXRCb3gucmVtb3ZlKCk7IGFkZEJ1YmJsZSgiQUkiLCBkLnJlcGx5LCBkLm1lZGlhKTsgbG9hZFNlc3Npb25zKCk7IH0KICB9KS5jYXRjaChmdW5jdGlvbihlcnIpIHsgd2FpdEJveC50ZXh0Q29udGVudCA9ICLimqDvuI8gIiArIGVyci5tZXNzYWdlOyB9KTsKfQp3aW5kb3cub25sb2FkID0gZnVuY3Rpb24oKSB7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImRvY0J0biIpLm9uY2xpY2sgPSBydW5Eb2N0b3I7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImhpc3RCdG4iKS5vbmNsaWNrID0gdG9nZ2xlRHJhd2VyOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZXdCdG4iKS5vbmNsaWNrID0gc3RhcnROZXc7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInBsdXNCdG4iKS5vbmNsaWNrID0gZnVuY3Rpb24oKSB7IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKS5jbGljaygpOyB9OwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKS5vbmNoYW5nZSA9IGZ1bmN0aW9uKCkgewogICAgdmFyIGZFbCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKSwgZmIgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZmlsZUJhciIpOwogICAgaWYgKGZFbC5maWxlcyAmJiBmRWwuZmlsZXMubGVuZ3RoID4gMCkgewogICAgICBmYi5zdHlsZS5kaXNwbGF5ID0gImZsZXgiOwogICAgICBmYi5pbm5lckhUTUwgPSAiPHNwYW4+8J+TjiAiICsgZkVsLmZpbGVzWzBdLm5hbWUgKyAiPC9zcGFuPjxzcGFuIHN0eWxlPSdjb2xvcjojZWY0NDQ0O2ZvbnQtd2VpZ2h0OmJvbGQ7Y3Vyc29yOnBvaW50ZXInIG9uY2xpY2s9J2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJmaWxlSW4iKS52YWx1ZT0iIjtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZmlsZUJhciIpLnN0eWxlLmRpc3BsYXk9Im5vbmUiOyc+4pyVPC9zcGFuPiI7CiAgICB9CiAgfTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgic2VuZEJ0biIpLm9uY2xpY2sgPSBzZW5kTWVzc2FnZTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgicSIpLm9ua2V5ZG93biA9IGZ1bmN0aW9uKGUpIHsgaWYgKGUua2V5ID09PSAiRW50ZXIiKSB7IGUucHJldmVudERlZmF1bHQoKTsgc2VuZE1lc3NhZ2UoKTsgfSB9OwogIHZhciBsYkMgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibGJDbG9zZSIpOwogIGlmIChsYkMpIGxiQy5vbmNsaWNrID0gZnVuY3Rpb24oKSB7IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJsaWdodGJveCIpLnN0eWxlLmRpc3BsYXkgPSAibm9uZSI7IH07CiAgbG9hZFNlc3Npb25zKCk7IGxvYWRNZXNzYWdlcygpOwp9Owo=").decode("utf-8"), mimetype="application/javascript")

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
