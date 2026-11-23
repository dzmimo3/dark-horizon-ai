from concurrent.futures import ThreadPoolExecutor
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

def fetch_google_facts_fast(q):
    sl = chr(47)
    enc = urllib.parse.quote(q)
    is_ar = any("\u0600" <= c <= "\u06FF" for c in q)

    def get_gnews():
        try:
            hl = "ar&gl=DZ&ceid=DZ:ar" if is_ar else "en-US&gl=US&ceid=US:en"
            r = requests.get(f"https:{sl}{sl}://google.com{sl}rss{sl}search?q={enc}&hl={hl}", timeout=3)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                return [f"GoogleNews: {i.findtext('title','')}" for i in root.findall(".//item")[:2]]
        except Exception: pass
        return []

    def get_wiki():
        try:
            lang = "ar" if is_ar else "en"
            r = requests.get(f"https:{sl}{sl}{lang}.wikipedia.org{sl}w{sl}api.php",
                params={"action": "query", "list": "search", "srsearch": q, "format": "json", "srlimit": 2},
                headers={"User-Agent": "DarkHorizonFilms/16.0"}, timeout=3)
            if r.status_code == 200:
                return [f"Wiki({x.get('title')}): {x.get('snippet','').replace('<span class="searchmatch">','').replace('</span>','')}"
                        for x in (r.json().get("query") or {}).get("search") or []]
        except Exception: pass
        return []

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1, f2 = ex.submit(get_gnews), ex.submit(get_wiki)
        res = f1.result(timeout=3.5) + f2.result(timeout=3.5)
    return "\n".join(res)

def web_search(q):
    return fetch_google_facts_fast(q)

def craft_visual_prompt(raw_q):
    facts = ""
    try: facts = fetch_google_facts_fast(raw_q)[:500]
    except Exception: pass
    sys_dir = (
        "You are the Visual Director of DARK HORIZON FILMS. Using the Google/Wikipedia facts provided, "
        "translate and describe the exact real-world appearance of the subject in English (max 25 words, photorealistic 8k, no text/watermarks). "
        "Output ONLY the English prompt."
    )
    user_msg = f"Request: {raw_q}\nGoogle/Wiki Facts:\n{facts}" if facts else raw_q
    en = llm_think([{"role": "system", "content": sys_dir}, {"role": "user", "content": user_msg}], temp=0.2)
    if len(en) > 5:
        clean_en = en.replace('"', '').strip() + ", photorealistic 8k, no text"
        threading.Thread(target=save_memory, args=(f"[GOOGLE_VISUAL] {raw_q}", clean_en), daemon=True).start()
        return clean_en
    return raw_q + ", photorealistic 8k, cinematic, no text"

@app.route("/", methods=["GET"])
def home():
    mem_preview = recall_memory().splitlines()[:3]
    return jsonify({
        "studio": "DARK HORIZON FILMS MASTER BRAIN v16.0 PARALLEL GOOGLE BRAIN",
        "status": "ONLINE & SELF-EVOLVING 24/7",
        "active_engines": {
            "cloudflare_ai": bool(os.environ.get("CF_ACCOUNT_ID") and os.environ.get("CF_API_TOKEN")),
            "groq_llm": bool(os.environ.get("GROQ_API_KEY")),
            "huggingface": bool(os.environ.get("HF_TOKEN")),
            "supabase_memory": bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")),
            "google_news_and_wiki": True
        },
        "recent_learned_memory": mem_preview
    }), 200, cors()

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
    errs = []

    # 1. Hugging Face FLUX.1-schnell (سريع ومجاني بمفتاح HF_TOKEN)
    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        for hf_mdl in ["black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-xl-base-1.0"]:
            try:
                from huggingface_hub import InferenceClient
                pil_img = InferenceClient(token=hf).text_to_image(prompt, model=hf_mdl)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=92)
                return Response(buf.getvalue(), mimetype="image/jpeg", headers=cors())
            except Exception as e:
                errs.append(f"HF:{str(e)[:60]}")

    # 2. Cloudflare Workers AI
    cid, ctok, sl = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip(), chr(47)
    if cid and ctok:
        cf_base = "https:" + sl + sl + "api." + "cloudflare.com" + sl + "client" + sl + "v4" + sl + "accounts" + sl
        for mdl in ["@cf/black-forest-labs/flux-1-schnell", "@cf/lykon/dreamshaper-8-lcm"]:
            try:
                r = requests.post(f"{cf_base}{cid}/ai/run/{mdl}",
                    headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                    json={"prompt": prompt}, timeout=12)
                if r.status_code == 200:
                    ct = r.headers.get("Content-Type", "")
                    if "image" in ct and len(r.content) > 4000: return Response(r.content, mimetype=ct, headers=cors())
                    b64 = (r.json().get("result") or {}).get("image")
                    if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
                errs.append(f"CF:{r.status_code}")
            except Exception as e:
                errs.append(f"CFE:{str(e)[:50]}")

    return jsonify({"error": "img_busy", "details": errs}), 503, cors()

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
