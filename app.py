import os, io, time, random, threading, base64, asyncio, requests
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

def web_search(q):
    sl = chr(47)
    chunks = []
    # 1. Wikipedia Encyclopedia API (Arabic & English)
    lang = "ar" if any("\u0600" <= c <= "\u06FF" for c in q) else "en"
    try:
        wu = f"https:{sl}{sl}{lang}.wikipedia.org{sl}w{sl}api.php"
        wr = requests.get(wu, params={"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 2},
            headers={"User-Agent": "DarkHorizonFilmsBrain/11.0"}, timeout=5)
        if wr.status_code == 200:
            for item in (wr.json().get("query") or {}).get("search") or []:
                clean_snip = item.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
                chunks.append(f"[Wikipedia - {item.get('title')}]: {clean_snip}")
    except Exception: pass

    # 2. Tavily Deep Tech & Media Search
    tk = os.environ.get("TAVILY_API_KEY", "").strip()
    if tk:
        try:
            u = "https:" + sl + sl + "api." + "tavily.com" + sl + "search"
            r = requests.post(u, json={"api_key": tk, "query": q, "max_results": 3}, timeout=7)
            if r.status_code == 200 and r.json().get("results"):
                for x in r.json()["results"]:
                    chunks.append(f"[Web - {x.get('title')}]: {x.get('content','')[:260]}")
        except Exception: pass

    # 3. DuckDuckGo Global Knowledge
    if len(chunks) < 3:
        try:
            from ddgs import DDGS
            for x in list(DDGS().text(q, max_results=3)):
                chunks.append(f"[DDG - {x.get('title')}]: {x.get('body','')[:250]}")
        except Exception: pass
    return "\n".join(chunks)

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
    sys_dir = (
        MASTER_STUDIO_BRAIN +
        "\nTASK: Analyze the user request in ANY language/dialect. Automatically detect the exact subject and intended visual medium "
        "(Live-Action Film, Japanese Anime Sakuga, 3D CGI Pixar/Maya, 2D Cartoon Cel, AAA Game Unreal Engine 5, or Creative Photo). "
        "Output ONLY a vivid, master-level English prompt (max 30 words, zero text/watermarks) applying the exact camera lens, lighting, and studio rendering style."
    )
    en = llm_think([{"role": "system", "content": sys_dir}, {"role": "user", "content": raw_q}], temp=0.25)
    if len(en) > 5:
        clean_en = en.replace('"', '').strip() + ", no text, no watermark"
        save_memory(f"[BRAIN_VISUAL] {raw_q}", clean_en)
        return clean_en
    return raw_q + ", cinematic masterpiece, 8k, no text"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON FILMS MASTER BRAIN v11.0 AUTONOMOUS SELF-EVOLVING ONLINE"}), 200, cors()

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

    sys_msg = MASTER_STUDIO_BRAIN + "\nAlways reply in the exact same language or dialect used by the user." + ctx
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
    return jsonify({"error": "img_busy"}), 503, cors()

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
