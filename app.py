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
    tv_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if tv_key:
        try:
            tr = requests.post(f"https:{sl}{sl}://tavily.com{sl}search", json={"api_key": tv_key, "query": clean_q, "search_depth": "advanced", "include_answer": True, "max_results": 4}, timeout=12)
            if tr.status_code == 200:
                td = tr.json()
                ans = td.get("answer", "")
                snippets = [f"- {r.get('title','')}: {r.get('content','')[:220]}" for r in td.get("results", [])]
                full_tv = f"{ans}\n" + "\n".join(snippets)
                if len(full_tv.strip()) > 15:
                    return full_tv[:1600]
        except Exception:
            pass
    return ""


def analyze_file_with_gemini(fpath, user_q):
    sl = chr(47)
    g_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not g_key or not os.path.exists(fpath):
        return ""
    ext = os.path.splitext(fpath).lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".pdf": "application/pdf", ".txt": "text/plain"}
    mime = mime_map.get(ext, "application/octet-stream")
    try:
        b64_data = base64.b64encode(open(fpath, "rb").read()).decode("utf-8")
        g_url = f"https:{sl}{sl}://googleapis.com{sl}v1beta{sl}models{sl}gemini-2.5-flash:generateContent?key={g_key}"
        payload = {"contents": [{"parts": [{"text": user_q or "حلل هذا الملف أو الصورة بالتفصيل باللغة العربية."}, {"inline_data": {"mime_type": mime, "data": b64_data}}]}]}
        gr = requests.post(g_url, json=payload, timeout=25)
        if gr.status_code == 200:
            c0 = next(iter(gr.json().get("candidates", [])), {})
            p0 = next(iter(c0.get("content", {}).get("parts", [])), {})
            if p0.get("text"):
                return p0["text"].strip()
    except Exception:
        pass
    return ""

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
<title>DARK HORIZON AI</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#131314"><style>
*{box-sizing:border-box;font-family:system-ui,-apple-system,sans-serif;-webkit-tap-highlight-color:transparent}
body{background:#131314;color:#e3e3e3;margin:0;display:flex;flex-direction:column;height:100dvh;overflow:hidden}
header{padding:12px 16px;background:#131314;display:flex;justify-content:space-between;align-items:center;z-index:10}
.h-icon{background:transparent;border:none;color:#c4c7c5;width:40px;height:40px;border-radius:50%;font-size:19px;display:flex;align-items:center;justify-content:center;cursor:pointer}
.h-icon:active{background:rgba(255,255,255,0.1)}
.brand{font-weight:600;font-size:16px;color:#e3e3e3;display:flex;align-items:center;gap:6px}
.badge{font-size:11px;background:#1e1f20;color:#a8c7fa;padding:3px 8px;border-radius:12px;border:1px solid rgba(168,199,250,0.2)}
#drawer{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:50}
.drawer-panel{width:270px;max-width:80vw;height:100%;background:#1e1f20;padding:16px;display:flex;flex-direction:column;gap:10px;overflow-y:auto}
.new-chat-pill{background:#282a2c;color:#e3e3e3;border:none;padding:12px 16px;border-radius:24px;font-size:14px;font-weight:600;display:flex;align-items:center;gap:10px;cursor:pointer}
.s-item{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-radius:20px;font-size:14px;color:#c4c7c5;cursor:pointer}
#chat{flex:1;overflow-y:auto;padding:12px 16px 24px;display:flex;flex-direction:column;gap:18px;max-width:780px;width:100%;margin:auto}
.msg{max-width:92%;line-height:1.65;font-size:15.5px;word-wrap:break-word;white-space:pre-wrap}
.user{align-self:flex-start;background:#282a2c;color:#e3e3e3;padding:12px 18px;border-radius:22px 22px 4px 22px}
.bot{align-self:flex-end;background:transparent;color:#e3e3e3;width:100%;padding:4px 2px}
.img-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px}
.img-wrap{position:relative;margin-top:8px;border-radius:16px;overflow:hidden;background:#1e1f20;cursor:zoom-in}
.img-wrap img,.img-wrap video{width:100%;display:block;border-radius:16px}
.glass-dl{position:absolute;top:10px;left:10px;width:36px;height:36px;border-radius:50%;background:rgba(19,19,20,0.78);color:#e3e3e3;border:1px solid rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;text-decoration:none;font-size:15px}
.dl-pill{display:inline-flex;align-items:center;gap:6px;background:#1e1f20;color:#a8c7fa;border:1px solid rgba(168,199,250,0.25);padding:7px 14px;border-radius:20px;margin-top:8px;font-size:13px;cursor:pointer}
.footer{padding:8px 14px 14px;background:#131314}
.capsule{max-width:780px;margin:auto;background:#1e1f20;border-radius:28px;padding:6px 10px;display:flex;align-items:center;gap:6px;border:1px solid rgba(255,255,255,0.1)}
#q{flex:1;background:transparent;border:none;color:#e3e3e3;font-size:15.5px;outline:none;padding:8px 6px}
.c-btn{border:none;width:38px;height:38px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
#plusBtn{background:transparent;color:#c4c7c5;font-size:22px}
#sendBtn{background:#a8c7fa;color:#062e6f;font-weight:700}
#lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.96);z-index:9999;flex-direction:column;align-items:center;justify-content:center;padding:16px}
#lightbox img{max-width:100%;max-height:82dvh;border-radius:14px;object-fit:contain}
.lb-bar{display:flex;gap:12px;margin-top:16px}
.lb-btn{background:#1e1f20;color:#e3e3e3;border:1px solid rgba(255,255,255,0.2);padding:10px 20px;border-radius:24px;text-decoration:none;font-size:14px;cursor:pointer}
</style></head><body>
<header>
  <button type="button" id="histBtn" class="h-icon" onclick="openDrawer()">☰</button>
  <div class="brand">DARK HORIZON <span class="badge">AI</span></div>
  <div style="display:flex;gap:4px">
    <button type="button" id="docBtn" class="h-icon" onclick="runDoctor()">🩺</button>
    <button type="button" id="newBtn" class="h-icon" onclick="startNew()">✎</button>
  </div>
</header>
<div id="drawer" onclick="if(event.target.id==='drawer')this.style.display='none'"><div class="drawer-panel"><button type="button" class="new-chat-pill" onclick="startNew()">✎ محادثة جديدة</button><div id="sessList"></div></div></div>
<div id="lightbox" onclick="if(event.target.id==='lightbox')closeLightbox()"><img id="lbImg" src=""><div class="lb-bar"><a id="lbDl" class="lb-btn" download="DARK_HORIZON_8K.jpg">⬇️ حفظ الصورة</a><button type="button" class="lb-btn" onclick="closeLightbox()">✕ إغلاق</button></div></div>
<div id="chat"><div class="msg bot">✨ أهلاً بك في <b>DARK HORIZON AI</b>. كيف يمكنني مساعدتك اليوم؟</div></div>
<div class="footer">
  <div id="fileBar" style="display:none;max-width:780px;margin:0 auto 8px;background:#1e1f20;color:#a8c7fa;padding:6px 14px;border-radius:16px;font-size:13px;justify-content:space-between;align-items:center"></div>
  <div class="capsule">
    <input type="file" id="fileIn" accept="image/*,.pdf,.txt" style="display:none" onchange="onFilePicked()">
    <button type="button" id="plusBtn" class="c-btn" onclick="document.getElementById('fileIn').click()">+</button>
    <input type="text" id="q" placeholder="اسأل DARK HORIZON AI..." onkeydown="if(event.key==='Enter'){event.preventDefault();sendMessage();}">
    <button type="button" id="sendBtn" class="c-btn" onclick="sendMessage()">↑</button>
  </div>
</div>
<script>
var sid = localStorage.getItem("dh_sid") || null;


function startVoiceInput() {
  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { alert("متصفحك لا يدعم الإدخال الصوتي المباشر."); return; }
  var rec = new SR();
  rec.lang = "ar-DZ";
  var mb = document.getElementById("micBtn");
  mb.style.color = "#f28b82";
  rec.onresult = function(e) {
    var txt = e.results.item(0).item(0).transcript;
    document.getElementById("q").value = txt;
    mb.style.color = "#c4c7c5";
    sendMessage();
  };
  rec.onerror = function() { mb.style.color = "#c4c7c5"; };
  rec.onend = function() { mb.style.color = "#c4c7c5"; };
  rec.start();
}

function saveLocalBackup(sId, title, role, content) {
  try {
    var db = JSON.parse(localStorage.getItem("dh_backup_db") || "{}");
    if (!db[sId]) db[sId] = { title: title || "محادثة", msgs: [] };
    db[sId].msgs.push({ role: role, content: content });
    localStorage.setItem("dh_backup_db", JSON.stringify(db));
  } catch (e) {}
}


function copyBubbleText(btn) {
  var box = btn.parentElement.parentElement;
  var txt = box.innerText.replace("📋 نسخ", "").replace("🔊 استماع", "").trim();
  navigator.clipboard.writeText(txt).then(function() {
    btn.textContent = "✅ تم النسخ";
    setTimeout(function() { btn.textContent = "📋 نسخ"; }, 1500);
  });
}

function speakBubbleText(btn) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  var box = btn.parentElement.parentElement;
  var txt = box.innerText.replace("📋 نسخ", "").replace("🔊 استماع", "").trim();
  var u = new SpeechSynthesisUtterance(txt);
  u.lang = "ar-SA";
  window.speechSynthesis.speak(u);
}
if ("serviceWorker" in navigator) { navigator.serviceWorker.register("/sw.js").catch(function(){}); }

function openLightbox(src, idx) {
  var lb = document.getElementById("lightbox"), im = document.getElementById("lbImg"), dl = document.getElementById("lbDl");
  if (!lb || !im || !dl) return;
  im.src = src; dl.href = src; dl.download = "DARK_HORIZON_" + (idx + 1) + ".jpg"; lb.style.display = "flex";
}

function closeLightbox() { document.getElementById("lightbox").style.display = "none"; }

function dlAllImgs(btn) {
  try {
    var arr = JSON.parse(decodeURIComponent(btn.getAttribute("data-urls")));
    arr.forEach(function(u, idx) {
      setTimeout(function() {
        var a = document.createElement("a"); a.href = u; a.download = "DARK_HORIZON_" + (idx + 1) + ".jpg";
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
      }, idx * 450);
    });
  } catch (e) {}
}

function addBubble(role, content, media) {
  var chat = document.getElementById("chat"), d = document.createElement("div");
  d.className = "msg " + (role === "User" ? "user" : "bot");
  var h = (content || "").replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
  if (role === "AI" && content && content.indexOf("جاري") === -1) {
    h += '<div style="display:flex;gap:8px;margin-top:10px"><button type="button" onclick="copyBubbleText(this)" style="background:#1e1f20;color:#c4c7c5;border:1px solid rgba(255,255,255,0.12);padding:4px 10px;border-radius:12px;font-size:12px;cursor:pointer">📋 نسخ</button><button type="button" onclick="speakBubbleText(this)" style="background:#1e1f20;color:#a8c7fa;border:1px solid rgba(168,199,250,0.2);padding:4px 10px;border-radius:12px;font-size:12px;cursor:pointer">🔊 استماع</button></div>';
  }
  if (media && media.vid) {
    h += '<div class="img-wrap"><video controls playsinline src="' + media.vid + '"></video><a class="glass-dl" href="' + media.vid + '" download="DARK_HORIZON_VIDEO.mp4">⬇️</a></div>';
  }
  if (media && media.imgs && media.imgs.length > 0) {
    if (media.imgs.length > 1) {
      var ls = encodeURIComponent(JSON.stringify(media.imgs));
      h += '<div><button type="button" class="dl-pill" data-urls="' + ls + '" onclick="dlAllImgs(this)">⬇️ حفظ جميع الصور (' + media.imgs.length + ')</button></div><div class="img-grid">';
      media.imgs.forEach(function(u, i) {
        h += '<div class="img-wrap" style="margin-top:0"><img src="' + u + '" style="aspect-ratio:9/16;object-fit:cover" onclick="openLightbox(this.src,' + i + ')"><a class="glass-dl" href="' + u + '" download="DARK_HORIZON_' + (i + 1) + '.jpg" onclick="event.stopPropagation()">⬇️</a></div>';
      });
      h += '</div>';
    } else {
      var u0 = media.imgs.item ? media.imgs.item(0) : media.imgs.slice(0, 1).pop();
      h += '<div class="img-wrap"><img src="' + u0 + '" onclick="openLightbox(this.src,0)"><a class="glass-dl" href="' + u0 + '" download="DARK_HORIZON_8K.jpg" onclick="event.stopPropagation()">⬇️</a></div>';
    }
  }
  d.innerHTML = h; chat.appendChild(d); chat.scrollTop = chat.scrollHeight; if(sid && content && content.indexOf("جاري")===-1) saveLocalBackup(sid, content.slice(0,25), role, content); return d;
}

function safeJson(res) {
  return res.text().then(function(t) {
    try { return JSON.parse(t); } catch (e) { throw new Error("الخادم يستيقظ، أعد المحاولة الآن."); }
  });
}

function runDoctor() {
  var w = addBubble("AI", "🩺 جاري فحص الخوادم...", {});
  fetch("/doctor").then(safeJson).then(function(d) { w.innerHTML = d.report; }).catch(function(e) { w.textContent = "⚠️ " + e.message; });
}

function openDrawer() { document.getElementById("drawer").style.display = "block"; loadSessions(); }

function loadSessions() {
  fetch("/sessions").then(safeJson).then(function(list) {
    var box = document.getElementById("sessList"); if (!box) return; box.innerHTML = "";
    list.forEach(function(s) {
      var row = document.createElement("div"); row.className = "s-item";
      var sp = document.createElement("span"); sp.style.cssText = "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"; sp.textContent = s.title;
      sp.onclick = function() { sid = s.id; localStorage.setItem("dh_sid", sid); document.getElementById("drawer").style.display = "none"; loadMessages(); };
      var del = document.createElement("button"); del.textContent = "✕"; del.style.cssText = "background:none;border:none;color:#f28b82;font-size:15px;cursor:pointer";
      del.onclick = function(ev) { ev.stopPropagation(); fetch("/sessions/" + s.id, { method: "DELETE" }).then(function() { if (sid == s.id) startNew(); loadSessions(); }); };
      row.appendChild(sp); row.appendChild(del); box.appendChild(row);
    });
  }).catch(function() {});
}

function startNew() {
  sid = null; localStorage.removeItem("dh_sid"); document.getElementById("drawer").style.display = "none";
  document.getElementById("chat").innerHTML = '<div class="msg bot">✨ أهلاً بك في <b>DARK HORIZON AI</b>. كيف يمكنني مساعدتك اليوم؟</div>';
}

function loadMessages() {
  if (!sid) return;
  fetch("/messages/" + sid).then(safeJson).then(function(msgs) {
    if (!msgs || msgs.length === 0) return;
    var chat = document.getElementById("chat"); chat.innerHTML = "";
    msgs.forEach(function(m) { addBubble(m.role, m.content, m.media); });
  }).catch(function() {});
}

function onFilePicked() {
  var fEl = document.getElementById("fileIn"), fb = document.getElementById("fileBar"), f = fEl.files ? fEl.files.item(0) : null;
  if (f) { fb.style.display = "flex"; fb.innerHTML = "<span>📎 " + f.name + "</span><span style='color:#f28b82;font-weight:bold;cursor:pointer' onclick='clearFile()'>✕</span>"; }
}

function clearFile() { document.getElementById("fileIn").value = ""; document.getElementById("fileBar").style.display = "none"; }

function sendMessage() {
  var qEl = document.getElementById("q"), fEl = document.getElementById("fileIn"), txt = qEl.value.trim(), file = fEl.files ? fEl.files.item(0) : null;
  if (!txt && !file) return;
  addBubble("User", txt || ("📎 " + file.name), {});
  var waitBox = addBubble("AI", "⚡ جاري التفكير...", {});
  var fd = new FormData(); if (sid) fd.append("sid", sid); fd.append("q", txt); if (file) fd.append("file", file);
  qEl.value = ""; clearFile();
  fetch("/send_all", { method: "POST", body: fd }).then(safeJson).then(function(d) {
    sid = d.sid; localStorage.setItem("dh_sid", sid);
    if (d.job_id) {
      waitBox.textContent = "🎨🎬 جاري التصميم والإخراج السينمائي...";
      var iv = setInterval(function() {
        fetch("/job/" + d.job_id).then(safeJson).then(function(st) {
          if (st.done) { clearInterval(iv); waitBox.remove(); addBubble("AI", st.reply, st.media); loadSessions(); }
        }).catch(function() {});
      }, 1500);
    } else { waitBox.remove(); addBubble("AI", d.reply, d.media); loadSessions(); }
  }).catch(function(err) { waitBox.textContent = "⚠️ " + err.message; });
}

loadSessions(); loadMessages();
</script></body></html>"""


@app.route("/doctor")
def doctor():
    with db_lock: conn.execute("DELETE FROM messages WHERE content LIKE '%جاري%'"); conn.commit()
    g_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    cf_ok = bool(os.environ.get("CF_API_TOKEN", "").strip())
    return jsonify({"report": f"🩺 <b>تقرير الفحص الذاتي الشامل لـ DARK HORIZON AI:</b>\n• خوادم Google (Gemini 2.5 + Imagen 3 + Veo 2): {'مفعّلة ✅' if g_ok else 'غير مضافة ⚠️'}\n• بطاقات Cloudflare GPU (8K): {'مفعّلة ✅' if cf_ok else 'غير مضافة ⚠️'}\n• محرك البحث العميق (Tavily AI): {'مفعّل ✅' if os.environ.get('TAVILY_API_KEY') else 'غير مضاف ⚠️'}\n• قاعدة البيانات والذاكرة: نظيفة ✅"})

@app.route("/media/<path:fn>")
def media(fn): return send_from_directory(WORK, fn)
@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/manifest.json")
def pwa_manifest():
    return jsonify({
        "name": "DARK HORIZON AI",
        "short_name": "DARK HORIZON",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#131314",
        "theme_color": "#131314",
        "icons": [{"src": "https://flaticon.com", "sizes": "512x512", "type": "image/png"}]
    })

@app.route("/sw.js")
def pwa_sw():
    return Response("self.addEventListener('fetch', function(e){});", mimetype="application/javascript")

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
        rep = analyze_file_with_gemini(up_path, q) or smart_ai([{"role": "user", "content": f"تم إرفاق ملف باسم {os.path.basename(up_path)}. {q}"}]) or "تم استلام الملف بنجاح."
    else:
        web_facts = web_search_engine(q)
        msgs = [{"role": "system", "content": f"أنت المساعد الذكي لاستوديو DARK HORIZON FILMS LTD. استعن ببيانات البحث العالمية التالية لتقديم إجابات شاملة ودقيقة:\n{web_facts}"}]
        for r_role, r_cnt in hist: msgs.append({"role": "user" if r_role == "User" else "assistant", "content": r_cnt[:400]})
        rep = smart_ai(msgs) or "أهلاً بك في استوديو DARK HORIZON FILMS LTD! كيف يمكنني مساعدتك اليوم؟"
    with db_lock: conn.execute("INSERT INTO messages (session_id, role, content, media) VALUES (?, 'AI', ?, '{}')", (sid, rep)); conn.commit()
    return jsonify({"sid": sid, "reply": rep, "media": {}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
