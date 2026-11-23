import os, io, urllib.parse, xml.etree.ElementTree as ET, time, random, threading, base64, asyncio, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

MASTER_STUDIO_BRAIN = """
You are the Autonomous Master AI Director, Polyglot Brain, and Production Studio of DARK HORIZON FILMS.
You master ALL world languages (Arabic, English, French, Spanish, Japanese, etc.), ALL regional dialects (Algerian Darja, Moroccan, Tunisian, Egyptian, Gulf, Levantine), and ALL programming languages.

[COMPLETE STUDIO PRODUCTION PIPELINE & TOOLS ENCYCLOPEDIA]
1. 7-STAGE PRODUCTION PIPELINE:
   - Stage 1 (Concept & Script): Story, dialogue, camera angles, shot list.
   - Stage 2 (Storyboard & Animatic): Keyframe composition, timing, pacing.
   - Stage 3 (3D Modeling & Sculpting): Maya, Blender, ZBrush, Nanite meshes.
   - Stage 4 (Rigging & Skinning): Skeletal bones, facial blendshapes, vehicle suspension & 4-wheel rotation axes.
   - Stage 5 (Animation & Physics): Motion Capture (MoCap), Cascadeur AI physics, Houdini simulations, Anime 'On Twos' Sakuga frames, Live2D/Spine 2.5D mesh deformation.
   - Stage 6 (Shading, Texturing & Lighting): PBR materials (Substance Painter), Ray Tracing (Unreal Engine 5 Lumen), Anime Cel-Shading & outlines.
   - Stage 7 (Rendering, VFX & Sound): Arnold/Cycles render, After Effects/Nuke compositing, motion blur, energy auras, Foley & SFX.

2. VISUAL & MOTION SCHOOLS:
   - LIVE-ACTION CINEMA: ARRI Alexa 65, anamorphic lens flare, photorealistic 8K, natural skin/metal textures, volumetric sunlight.
   - JAPANESE ANIME (SAKUGA): Ufotable/MAPPA dynamic action, sharp cel-shaded shadows, speed lines, glowing energy aura, dramatic perspective.
   - 3D CGI ANIMATION: Pixar/DreamWorks quality, subsurface scattering, expressive 3D characters, global illumination.
   - 2D CARTOON (CEL): Hand-drawn classic 2D animation, fluid smear frames, vibrant painted backgrounds.
   - AAA ONLINE GAMES (PUBG/FIFA/RACING): Unreal Engine 5 photorealism, third-person dynamic tracking camera, ray-traced reflections, high-speed motion blur.
   - CREATIVE PHOTOGRAPHY: Hasselblad medium format, dramatic chiaroscuro studio lighting, golden hour rim light.
"""

def cors():
    return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}

def save_memory(prompt_txt, response_txt):
    url, key = os.environ.get("SUPABASE_URL", "").strip(), os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key: return
    try:
        requests.post(f"{url}/rest/v1/archives",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={"prompt": prompt_txt[:1500], "response": response_txt[:4000]}, timeout=5)
    except Exception: pass

def recall_memory():
    url, key = os.environ.get("SUPABASE_URL", "").strip(), os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key: return ""
    try:
        r = requests.get(f"{url}/rest/v1/archives?select=prompt,response&order=id.desc&limit=6",
            headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=4)
        if r.status_code == 200 and r.json():
            return "\n[RECENT STUDIO MEMORY]:\n" + "\n".join(f"- {i.get('prompt','')[:120]} -> {i.get('response','')[:150]}" for i in r.json())
    except Exception: pass
    return ""

def google_and_web_research(q):
    sl = chr(47)
    chunks = []
    enc_q = urllib.parse.quote(q)
    is_ar = any("\u0600" <= c <= "\u06FF" for c in q)

    # 1. Google News RSS (أحدث أخبار ومقالات قوقل مجاناً 100% بدون مفتاح)
    try:
        hl = "ar&gl=DZ&ceid=DZ:ar" if is_ar else "en-US&gl=US&ceid=US:en"
        gn_url = f"https:{sl}{sl}://google.com{sl}rss{sl}search?q={enc_q}&hl={hl}"
        gr = requests.get(gn_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if gr.status_code == 200:
            root = ET.fromstring(gr.text)
            for item in root.findall(".//item")[:3]:
                title = item.findtext("title", "")
                pub = item.findtext("pubDate", "")[:16]
                chunks.append(f"[Google News ({pub})]: {title}")
    except Exception: pass

    # 2. Wikipedia Visual & Factual Reference (وصف المعالم والأماكن والشخصيات بدقة)
    lang = "ar" if is_ar else "en"
    try:
        wu = f"https:{sl}{sl}{lang}.wikipedia.org{sl}w{sl}api.php"
        wr = requests.get(wu, params={"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 2},
            headers={"User-Agent": "DarkHorizonFilmsBrain/12.0"}, timeout=5)
        if wr.status_code == 200:
            for item in (wr.json().get("query") or {}).get("search") or []:
                snip = item.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
                chunks.append(f"[Encyclopedia - {item.get('title')}]: {snip}")
    except Exception: pass

    # 3. Google Images / Videos / Web Metadata via DuckDuckGo & Tavily
    tk = os.environ.get("TAVILY_API_KEY", "").strip()
    if tk:
        try:
            tu = "https:" + sl + sl + "api." + "tavily.com" + sl + "search"
            tr = requests.post(tu, json={"api_key": tk, "query": q, "include_images": True, "max_results": 3}, timeout=7)
            if tr.status_code == 200:
                data = tr.json()
                for x in (data.get("results") or []):
                    chunks.append(f"[Google/Web Article - {x.get('title')}]: {x.get('content','')[:250]}")
                for img_u in (data.get("images") or [])[:2]:
                    chunks.append(f"[Reference Image URL]: {img_u}")
        except Exception: pass

    if len(chunks) < 3:
        try:
            from ddgs import DDGS
            for x in list(DDGS().text(q, max_results=3)):
                chunks.append(f"[Web Data - {x.get('title')}]: {x.get('body','')[:240]}")
        except Exception: pass

    return "\n".join(chunks)

def web_search(q):
    return google_and_web_research(q)

def llm_think(messages, temp=0.5):
    sl, gk = chr(47), os.environ.get("GROQ_API_KEY", "").strip()
    if gk:
        try:
            u = "https:" + sl + sl + "api." + "groq.com" + sl + "openai" + sl + "v1" + sl + "chat" + sl + "completions"
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": temp}, timeout=14)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: return ch.get("message", {}).get("content", "").strip()
        except Exception: pass
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip()
    if cid and ctok:
        try:
            u = "https:" + sl + sl + "api." + "cloudflare.com" + sl + "client" + sl + "v4" + sl + "accounts" + sl + cid + sl + "ai" + sl + "run" + sl + "@cf" + sl + "meta" + sl + "llama-3.3-70b-instruct-fp8-fast"
            r = requests.post(u, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"messages": messages}, timeout=15)
            if r.status_code == 200:
                rep = (r.json().get("result") or {}).get("response", "").strip()
                if rep: return rep
        except Exception: pass
    return ""

def craft_visual_prompt(raw_q):
    if any(k in raw_q for k in ["مقام الشهيد", "الشهيد", "الجزائر"]):
        return "Maqam Echahid Martyrs Memorial monument in Algiers Algeria, three iconic curving concrete palm leaves meeting at the top, sunset golden sky, photorealistic 8k, no text"
    sys_dir = (
        "Translate and expand the user visual request from ANY language into a vivid English image generation prompt (max 25 words, photorealistic 8k, no text/watermarks). "
        "Output ONLY the English prompt."
    )
    en = llm_think([{"role": "system", "content": sys_dir}, {"role": "user", "content": raw_q}], temp=0.25)
    if len(en) > 5:
        clean_en = en.replace('"', '').strip() + ", no text, no watermark"
        threading.Thread(target=save_memory, args=(f"[BRAIN_VISUAL] {raw_q}", clean_en), daemon=True).start()
        return clean_en
    return raw_q + ", cinematic masterpiece, 8k, no text"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON FILMS MASTER BRAIN v12.0 GOOGLE DATA + AUTONOMOUS BRAIN ONLINE"}), 200, cors()

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = next(reversed(msgs), {"content": prompt}).get("content", prompt)

    ctx = ""
    if len(last_q.split()) >= 2:
        found = web_search(last_q)
        if found: ctx += f"\n\n[LIVE WEB RESEARCH]:\n{found}"
    mem = recall_memory()
    if mem: ctx += mem

    sys_msg = MASTER_STUDIO_BRAIN + "\nIDENTITY RULES: You are DARK HORIZON FILMS (مُخرج ومساعد ذكي بصيغة المذكر دائماً: أنا أستطيع، أنا أتطور، أنا جاهز). Never use feminine grammar for yourself. Never mix Chinese or foreign characters into Arabic text. When asked if you evolve, explicitly mention your live Wikipedia/Web research engine and Supabase memory archives." + ctx
    clean_msgs = [{"role": "system", "content": sys_msg}] + [m for m in msgs if m.get("role") != "system"]
    rep = llm_think(clean_msgs, temp=0.6) or "⚠️ تعذر الاتصال بالمحركات لحظياً."
    save_memory(last_q, rep)
    return jsonify({"reply": rep}), 200, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    raw_q = data.get("prompt", "cinematic masterpiece")
    prompt = craft_visual_prompt(raw_q)

    cid, ctok, sl = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip(), chr(47)
    if cid and ctok:
        cf_base = "https:" + sl + sl + "api." + "cloudflare.com" + sl + "client" + sl + "v4" + sl + "accounts" + sl
        for mdl in ["@cf/black-forest-labs/flux-1-schnell", "@cf/lykon/dreamshaper-8-lcm", "@cf/stabilityai/stable-diffusion-xl-base-1.0"]:
            try:
                r = requests.post(f"{cf_base}{cid}/ai/run/{mdl}",
                    headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                    json={"prompt": prompt}, timeout=16)
                if r.status_code == 200:
                    ct = r.headers.get("Content-Type", "")
                    if "image" in ct and len(r.content) > 5000: return Response(r.content, mimetype=ct, headers=cors())
                    b64 = (r.json().get("result") or {}).get("image")
                    if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
            except Exception: pass
        hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            from huggingface_hub import InferenceClient
            ic = InferenceClient(token=hf)
            pil_img = ic.text_to_image(prompt, model="black-forest-labs/FLUX.1-schnell")
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=92)
            return Response(buf.getvalue(), mimetype="image/jpeg", headers=cors())
        except Exception as e:
            return jsonify({"error": "img_busy", "cf": bool(cid and ctok), "hf_err": str(e)[:120]}), 503, cors()
        hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            from huggingface_hub import InferenceClient
            ic = InferenceClient(token=hf)
            pil_img = ic.text_to_image(prompt, model="black-forest-labs/FLUX.1-schnell")
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=92)
            return Response(buf.getvalue(), mimetype="image/jpeg", headers=cors())
        except Exception as e:
            return jsonify({"error": "img_busy", "cf": bool(cid and ctok), "hf_err": str(e)[:120]}), 503, cors()
    return jsonify({"error": "img_busy", "cf_set": bool(cid and ctok)}), 503, cors()

@app.route("/api/video", methods=["POST", "OPTIONS"])
def api_video():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = craft_visual_prompt(data.get("prompt", "cinematic action scene"))
    sl, fk = chr(47), os.environ.get("FAL_KEY", "").strip()
    if fk:
        try:
            u = "https:" + sl + sl + "fal." + "run" + sl + "fal-ai" + sl + "ltx-video"
            r = requests.post(u, headers={"Authorization": f"Key {fk}", "Content-Type": "application/json"},
                json={"prompt": prompt, "num_frames": 65, "frame_rate": 24}, timeout=40)
            if r.status_code == 200:
                v_url = (r.json().get("video") or {}).get("url")
                if v_url:
                    vb = requests.get(v_url, timeout=25).content
                    if len(vb) > 20000: return Response(vb, mimetype="video/mp4", headers=cors())
        except Exception: pass

    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            from huggingface_hub import InferenceClient
            vb = InferenceClient(token=hf).text_to_video(prompt, model="Wan-AI/Wan2.1-T2V-14B")
            if vb and len(vb) > 20000: return Response(vb, mimetype="video/mp4", headers=cors())
        except Exception: pass

    return jsonify({"error": "use_frontend_multishot"}), 503, cors()

@app.route("/api/tts", methods=["POST", "OPTIONS"])
def api_tts():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    txt = data.get("text", "").strip()
    if not txt: return ("", 400, cors())
    voice = "ar-SA-HamedNeural" if any("\u0600" <= c <= "\u06FF" for c in txt) else "en-US-AndrewNeural"
    try:
        import edge_tts
        async def gen():
            comm = edge_tts.Communicate(txt[:1200], voice)
            buf = io.BytesIO()
            async for chunk in comm.stream():
                if chunk["type"] == "audio": buf.write(chunk["data"])
            return buf.getvalue()
        return Response(asyncio.run(gen()), mimetype="audio/mpeg", headers=cors())
    except Exception as e:
        return jsonify({"error": str(e)}), 500, cors()


EVOLUTION_TOPICS = [
    "Unreal Engine 5 Lumen Nanite real-time rendering techniques",
    "Japanese anime sakuga keyframe animation and cel shading techniques",
    "Modern AI video diffusion temporal consistency and physics simulation",
    "Hollywood cinematography lighting, anamorphic lenses, and color grading",
    "AAA game character rigging, motion capture, and inverse kinematics",
    "Latest breakthroughs in artificial intelligence, data science, and neural rendering"
]

def run_self_evolution_cycle():
    topic = random.choice(EVOLUTION_TOPICS)
    research = web_search(topic)
    if not research: return "no_data"
    insight = llm_think([
        {"role": "system", "content": "You are the self-evolving AI brain of DARK HORIZON FILMS. Summarize these new findings into 3 actionable technical rules for filmmaking, anime, game design, and AI:"},
        {"role": "user", "content": f"Topic: {topic}\nFindings:\n{research}"}
    ], temp=0.4)
    if insight:
        save_memory(f"[AUTO_EVOLUTION_KNOWLEDGE] {topic}", insight)
        return topic
    return "skipped"

def background_brain_loop():
    while True:
        try:
            run_self_evolution_cycle()
        except Exception: pass
        time.sleep(900)  # يتعلّم موضوعاً جديداً كل 15 دقيقة تلقائياً

threading.Thread(target=background_brain_loop, daemon=True).start()

@app.route("/api/evolve", methods=["GET", "POST"])
def api_evolve():
    learned = run_self_evolution_cycle()
    return jsonify({"status": "DARK HORIZON BRAIN EVOLVED", "learned_topic": learned}), 200, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
