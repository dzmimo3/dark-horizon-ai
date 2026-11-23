import os, base64, random, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

def deep_search(query):
    results = []
    tv_key = os.environ.get("TAVILY_API_KEY", "")
    if tv_key:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e746176696c792e636f6d2f736561726368").decode()
            r = requests.post(u, json={"api_key": tv_key, "query": query, "search_depth": "advanced", "max_results": 4}, timeout=10).json()
            for res in r.get("results", []):
                results.append(f"- [{res.get('title')}]: {res.get('content', '')[:280]}")
        except Exception: pass
    if not results:
        try:
            u = bytes.fromhex("68747470733a2f2f61722e77696b6970656469612e6f72672f772f6170692e706870").decode()
            w = requests.get(u, params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 2}, timeout=6).json()
            for item in w.get("query", {}).get("search", []):
                snip = item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                results.append(f"- [ويكيبيديا - {item.get('title')}]: {snip}")
        except Exception: pass
    return "\n".join(results)

def save_archive(q, ans):
    sb_u, sb_k = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_KEY", "")
    if sb_u and sb_k:
        try:
            requests.post(f"{sb_u}/rest/v1/archives",
                headers={"apikey": sb_k, "Authorization": f"Bearer {sb_k}", "Content-Type": "application/json"},
                json={"prompt": q[:1000], "response": ans[:12000]}, timeout=5)
        except Exception: pass

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON ALL DAILY QUOTAS ACTIVE", "engines": ["Groq", "Gemini", "OpenRouter", "HF-Qwen", "Cloudflare-FLUX", "HF-FLUX-Dev", "SD-3.5", "Wan2.1-Video"]})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = next(reversed(msgs), {"content": prompt}).get("content", prompt)

    search_ctx = ""
    if any(k in last_q for k in ["بحث", "ابحث", "دراسة", "مقال", "تقرير", "أخبار", "ما هو", "كيف"]):
        found = deep_search(last_q)
        if found: search_ctx = f"\n\n[نتائج البحث الحي الموثقة]:\n{found}"

    sys_msg = "أنت DARK HORIZON AI، نظام ذكاء اصطناعي متكامل. أجب بالعربية الفصحى بدقة ووضوح." + search_ctx
    final_msgs = [{"role": "system", "content": sys_msg}] + [m for m in msgs if m.get("role") != "system"]
    reply_text = None

    # الحصة 1: Groq Llama-3.3-70B (14,400 طلب يومياً)
    gk = os.environ.get("GROQ_API_KEY", "")
    if gk and not reply_text:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e67726f712e636f6d2f6f70656e61692f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": final_msgs, "temperature": 0.6}, timeout=14)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: reply_text = ch.get("message", {}).get("content", "")
        except Exception: pass

    # الحصة 2: Google Gemini 2.0 Flash (تتجدد يومياً)
    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem and not reply_text:
        try:
            u = bytes.fromhex("68747470733a2f2f67656e657261746976656c616e67756167652e676f6f676c65617069732e636f6d2f7631626574612f6d6f64656c732f67656d696e692d322e302d666c6173683a67656e6572617465436f6e74656e743f6b65793d").decode()
            r = requests.post(u + gem, json={"contents": [{"parts": [{"text": sys_msg + "\n\n" + last_q}]}]}, timeout=14)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    reply_text = pt.get("text", "")
        except Exception: pass

    # الحصة 3: OpenRouter Free Tier (200 طلب يومياً)
    ork = os.environ.get("OPENROUTER_API_KEY", "")
    if ork and not reply_text:
        try:
            u = bytes.fromhex("68747470733a2f2f6f70656e726f757465722e61692f6170692f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {ork}", "Content-Type": "application/json"},
                json={"model": "meta-llama/llama-3.3-70b-instruct:free", "messages": final_msgs}, timeout=15)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: reply_text = ch.get("message", {}).get("content", "")
        except Exception: pass

    # الحصة 4: Hugging Face Qwen 2.5 72B
    hf = os.environ.get("HF_TOKEN", "")
    if hf and not reply_text:
        try:
            u = bytes.fromhex("68747470733a2f2f726f757465722e68756767696e67666163652e636f2f68662d696e666572656e63652f6d6f64656c732f5177656e2f5177656e322e352d3732422d496e7374727563742f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": final_msgs, "max_tokens": 900}, timeout=16)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: reply_text = ch.get("message", {}).get("content", "")
        except Exception: pass

    if reply_text:
        save_archive(last_q, reply_text)
        return jsonify({"reply": reply_text}), 200, cors()

    return jsonify({"error": "all_chat_quotas_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic masterpiece, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    # الأولوية 0: Fal.ai FLUX.1 Schnell (أسرع وأوضح مولد صور في العالم - 1.5 ثانية)
    fk = os.environ.get("FAL_KEY", "")
    if fk:
        try:
            u = bytes.fromhex("68747470733a2f2f66616c2e72756e2f66616c2d61692f666c75782f7363686e656c6c").decode()
            r = requests.post(u, headers={"Authorization": f"Key {fk}", "Content-Type": "application/json"},
                json={"prompt": prompt, "image_size": "square_hd", "seed": seed}, timeout=15)
            if r.status_code == 200:
                imgs = r.json().get("images") or []
                first_im = next(iter(imgs), None)
                if first_im and first_im.get("url"):
                    img_bytes = requests.get(first_im["url"], timeout=15).content
                    if len(img_bytes) > 8000:
                        return Response(img_bytes, mimetype="image/jpeg", headers=cors())
        except Exception: pass


    # الحصة 1: Cloudflare Workers AI FLUX-1-schnell (10,000 وحدة يومياً)
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            cf_base = bytes.fromhex("68747470733a2f2f6170692e636c6f7564666c6172652e636f6d2f636c69656e742f76342f6163636f756e74732f").decode()
            r = requests.post(cf_base + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell",
                headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 6, "seed": seed}, timeout=20)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass

    # الحصص 2 و 3 و 4: Hugging Face Router (FLUX.1-dev + FLUX.1-schnell + SD 3.5 Large)
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        hf_base = bytes.fromhex("68747470733a2f2f726f757465722e68756767696e67666163652e636f2f68662d696e666572656e63652f6d6f64656c732f").decode()
        for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-3.5-large"]:
            try:
                r = requests.post(hf_base + mdl,
                    headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": f"{prompt}, variation {seed}"}, timeout=25)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
            except Exception: pass

    return jsonify({"error": "all_image_quotas_busy"}), 503, cors()

@app.route("/api/video", methods=["POST", "OPTIONS"])
def api_video():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic drone shot over golden desert sunset, 4k")
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        hf_base = bytes.fromhex("68747470733a2f2f726f757465722e68756767696e67666163652e636f2f68662d696e666572656e63652f6d6f64656c732f").decode()
        for vmdl in ["Wan-AI/Wan2.1-T2V-14B", "ali-vilab/text-to-video-ms-1.7b"]:
            try:
                r = requests.post(hf_base + vmdl,
                    headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": prompt}, timeout=45)
                if r.status_code == 200 and len(r.content) > 20000:
                    return Response(r.content, mimetype="video/mp4", headers=cors())
            except Exception: pass
    return jsonify({"error": "video_fallback_to_canvas"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
