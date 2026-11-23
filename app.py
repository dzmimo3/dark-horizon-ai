import os, io, base64, random, asyncio, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

def web_search(query):
    out = []
    tv = os.environ.get("TAVILY_API_KEY", "").strip()
    if tv:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e746176696c792e636f6d2f736561726368").decode()
            r = requests.post(u, json={"api_key": tv, "query": query, "max_results": 3}, timeout=8).json()
            for x in r.get("results", []):
                out.append(f"- {x.get('title')}: {x.get('content', '')[:250]}")
        except Exception: pass
    if not out:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for x in ddgs.text(query, max_results=3):
                    out.append(f"- {x.get('title')}: {x.get('body', '')[:220]}")
        except Exception: pass
    return "\n".join(out)

def save_db(q, ans):
    su, sk = os.environ.get("SUPABASE_URL", "").strip().rstrip("/"), os.environ.get("SUPABASE_KEY", "").strip()
    if su and sk:
        try:
            requests.post(f"{su}/rest/v1/archives",
                headers={"apikey": sk, "Authorization": f"Bearer {sk}", "Content-Type": "application/json"},
                json={"prompt": q[:1000], "response": ans[:12000]}, timeout=4)
        except Exception: pass

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON PURE CLEAN V5 (NO G4F)"})

@app.route("/api/tts", methods=["POST", "OPTIONS"])
def api_tts():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()[:1500]
    if not text: return jsonify({"error": "empty"}), 400, cors()
    try:
        import edge_tts
        async def _run():
            comm = edge_tts.Communicate(text, "ar-SA-HamedNeural")
            buf = io.BytesIO()
            async for ch in comm.stream():
                if ch["type"] == "audio": buf.write(ch["data"])
            return buf.getvalue()
        mp3 = asyncio.run(_run())
        return Response(mp3, mimetype="audio/mpeg", headers=cors())
    except Exception as e:
        return jsonify({"error": str(e)}), 500, cors()
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = next(reversed(msgs), {"content": prompt}).get("content", prompt)

    ctx = ""
    if any(w in last_q for w in ["بحث", "ابحث", "دراسة", "مقال", "تقرير", "أخبار", "ما هو", "كيف"]):
        found = web_search(last_q)
        if found: ctx = f"\n\n[معلومات حية من البحث]:\n{found}"

    sys_msg = (
        "You are DARK HORIZON AI PRO, a universal polyglot AI assistant. "
        "Understand and respond fluently in ANY world language (Arabic, English, French, Spanish, etc.), "
        "ANY regional dialect (Algerian Darja, Moroccan, Tunisian, Egyptian, Gulf, Levantine), "
        "and ALL programming languages (Python, JS, C++, Rust, HTML/CSS, SQL, Bash, etc.). "
        "Always reply in the exact same language or dialect the user used, with high precision." + ctx
    )
    clean_msgs = [{"role": "system", "content": sys_msg}] + [m for m in msgs if m.get("role") != "system"]
    sl = chr(47)
    errs = []

    # 1. Groq Llama-3.3-70B
    gk = os.environ.get("GROQ_API_KEY", "").strip()
    if gk:
        try:
            u = "https:" + sl + sl + "api." + "groq.com" + sl + "openai" + sl + "v1" + sl + "chat" + sl + "completions"
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": clean_msgs}, timeout=15)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch:
                    rep = ch.get("message", {}).get("content", "")
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"Groq:{r.status_code}")
        except Exception as e: errs.append(f"GroqE:{e}")

    # 2. Cloudflare Workers AI Llama-3.3-70B (مجاني وسريع بنفس مفتاح الصور)
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip()
    if cid and ctok:
        try:
            u = "https:" + sl + sl + "api." + "cloudflare.com" + sl + "client" + sl + "v4" + sl + "accounts" + sl + cid + sl + "ai" + sl + "run" + sl + "@cf" + sl + "meta" + sl + "llama-3.3-70b-instruct-fp8-fast"
            r = requests.post(u, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"messages": clean_msgs}, timeout=16)
            if r.status_code == 200:
                rep = (r.json().get("result") or {}).get("response", "")
                if rep:
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"CF:{r.status_code}")
        except Exception as e: errs.append(f"CFE:{e}")

    # 3. Hugging Face Router v1 (Qwen 2.5 72B)
    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            u = "https:" + sl + sl + "router." + "huggingface.co" + sl + "v1" + sl + "chat" + sl + "completions"
            r = requests.post(u, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": clean_msgs, "max_tokens": 900}, timeout=15)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch:
                    rep = ch.get("message", {}).get("content", "")
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"HF:{r.status_code}")
        except Exception as e: errs.append(f"HFE:{e}")

    # 4. Google Gemini 2.0 Flash
    gem = os.environ.get("GEMINI_API_KEY", "").strip()
    if gem:
        try:
            u = "https:" + sl + sl + "generativelanguage." + "googleapis.com" + sl + "v1beta" + sl + "models" + sl + "gemini-2.0-flash:generateContent?key=" + gem
            r = requests.post(u, json={"contents": [{"parts": [{"text": sys_msg + "\n\n" + last_q}]}]}, timeout=15)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    rep = pt.get("text", "")
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"Gem:{r.status_code}")
        except Exception as e: errs.append(f"GemE:{e}")

    return jsonify({"reply": f"⚠️ تعذر الاتصال بالمحركات لحظياً ({', '.join(errs)})."}), 200, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    raw_p = data.get("prompt", "cinematic masterpiece, 8k photorealistic")
    prompt = raw_p
    gk_tr = os.environ.get("GROQ_API_KEY", "").strip()
    if gk_tr and any(ord(c) > 127 for c in raw_p):
        try:
            sl_t = chr(47)
            u_tr = "https:" + sl_t + sl_t + "api." + "groq.com" + sl_t + "openai" + sl_t + "v1" + sl_t + "chat" + sl_t + "completions"
            tr_r = requests.post(u_tr, headers={"Authorization": f"Bearer {gk_tr}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [
                    {"role": "system", "content": "Translate the user request from any language or dialect (like Algerian, Egyptian, Arabic, French) into a clean, vivid English image generation prompt (max 20 words, photorealistic, no text/watermarks). Output ONLY the English prompt."},
                    {"role": "user", "content": raw_p}
                ], "temperature": 0.3}, timeout=8)
            if tr_r.status_code == 200:
                tr_txt = (next(iter(tr_r.json().get("choices") or []), {}).get("message") or {}).get("content", "").strip()
                if len(tr_txt) > 4: prompt = tr_txt + ", ultra detailed, cinematic lighting, no text"
        except Exception: pass
    errs = []

    # أسرع محركات Cloudflare Workers AI المجانية (1.5 - 3 ثوانٍ)
    cid = os.environ.get("CF_ACCOUNT_ID", "").strip()
    ctok = os.environ.get("CF_API_TOKEN", "").strip()
    if cid and ctok:
        cf_base = bytes.fromhex("68747470733a2f2f6170692e636c6f7564666c6172652e636f6d2f636c69656e742f76342f6163636f756e74732f").decode()
        models = [
            "@cf/lykon/dreamshaper-8-lcm",
            "@cf/stabilityai/stable-diffusion-xl-base-1.0",
            "@cf/black-forest-labs/flux-1-schnell"
        ]
        for mdl in models:
            try:
                r = requests.post(
                    f"{cf_base}{cid}/ai/run/{mdl}",
                    headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                    json={"prompt": prompt},
                    timeout=15
                )
                if r.status_code == 200:
                    ct = r.headers.get("Content-Type", "")
                    if "image" in ct and len(r.content) > 5000:
                        return Response(r.content, mimetype=ct, headers=cors())
                    j = r.json()
                    b64 = (j.get("result") or {}).get("image")
                    if b64:
                        return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
                errs.append(f"{mdl.split('/')[-1]}:{r.status_code}")
            except Exception as e:
                errs.append(f"CF_E:{e}")

    return jsonify({"error": "img_busy", "details": errs}), 503, cors()

@app.route("/api/video", methods=["POST", "OPTIONS"])
def api_video():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "sleek Mercedes AMG sports car speeding on highway at sunset, spinning wheels, photorealistic 4k")
    sl = chr(47)
    errs = []

    # 1. Fal.ai LTX-Video (أسرع فيديو زمني حقيقي)
    fk = os.environ.get("FAL_KEY", "").strip()
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
            errs.append(f"Fal:{r.status_code}")
        except Exception as e: errs.append(f"FalE:{e}")

    # 2. Hugging Face InferenceClient (Wan 2.1 Text-to-Video)
    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=hf)
            vb = client.text_to_video(prompt, model="Wan-AI/Wan2.1-T2V-14B")
            if vb and len(vb) > 20000: return Response(vb, mimetype="video/mp4", headers=cors())
        except Exception as e: errs.append(f"WanE:{e}")

    # 3. استوديو LTX-Video Distilled المجاني على Hugging Face Spaces
    try:
        from gradio_client import Client
        gclient = Client("Lightricks/ltx-video-distilled")
        res = gclient.predict(prompt=prompt, api_name="/text_to_video")
        v_path = res.get("video") if isinstance(res, dict) else (res if isinstance(res, (list, tuple)) else res)
        if v_path and os.path.exists(str(v_path)):
            with open(str(v_path), "rb") as vf:
                return Response(vf.read(), mimetype="video/mp4", headers=cors())
    except Exception as e: errs.append(f"SpaceE:{e}")

    return jsonify({"error": "use_5stage_studio", "details": errs}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
