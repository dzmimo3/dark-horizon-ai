import os, io, base64, random, asyncio, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

def live_search_and_news(query):
    snippets = []
    tv = os.environ.get("TAVILY_API_KEY", "").strip()
    if tv:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e746176696c792e636f6d2f736561726368").decode()
            r = requests.post(u, json={"api_key": tv, "query": query, "search_depth": "advanced", "max_results": 4}, timeout=10).json()
            for item in r.get("results", []):
                snippets.append(f"- [{item.get('title')}]: {item.get('content', '')[:260]}")
        except Exception: pass

    if not snippets:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for res in ddgs.text(query, max_results=4):
                    snippets.append(f"- [{res.get('title')}]: {res.get('body', '')[:240]}")
        except Exception: pass

    if not snippets:
        try:
            u = bytes.fromhex("68747470733a2f2f61722e77696b6970656469612e6f72672f772f6170692e706870").decode()
            w = requests.get(u, params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 2}, timeout=6).json()
            for it in w.get("query", {}).get("search", []):
                snip = it.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
                snippets.append(f"- [ويكيبيديا - {it.get('title')}]: {snip}")
        except Exception: pass

    return "\n".join(snippets)

def save_to_cloud(q, ans):
    sb_u, sb_k = os.environ.get("SUPABASE_URL", "").strip().rstrip("/"), os.environ.get("SUPABASE_KEY", "").strip()
    if sb_u and sb_k:
        try:
            requests.post(f"{sb_u}/rest/v1/archives",
                headers={"apikey": sb_k, "Authorization": f"Bearer {sb_k}", "Content-Type": "application/json"},
                json={"prompt": q[:1000], "response": ans[:12000]}, timeout=5)
        except Exception: pass

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON FULL EMPIRE ONLINE"})

@app.route("/api/tts", methods=["POST", "OPTIONS"])
def api_tts():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()[:1500]
    voice = data.get("voice") or "ar-SA-HamedNeural"
    if not text: return jsonify({"error": "empty_text"}), 400, cors()
    try:
        import edge_tts
        async def _gen():
            comm = edge_tts.Communicate(text, voice)
            buf = io.BytesIO()
            async for chunk in comm.stream():
                if chunk["type"] == "audio": buf.write(chunk["data"])
            return buf.getvalue()
        mp3_bytes = asyncio.run(_gen())
        if len(mp3_bytes) > 500: return Response(mp3_bytes, mimetype="audio/mpeg", headers=cors())
    except Exception as e:
        return jsonify({"error": str(e)}), 500, cors()
    return jsonify({"error": "tts_failed"}), 503, cors()
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = next(reversed(msgs), {"content": prompt}).get("content", prompt)

    ctx = ""
    if any(k in last_q for k in ["بحث", "ابحث", "دراسة", "مقال", "تقرير", "أخبار", "اخبار", "ما هو", "من هو", "كيف"]):
        found = live_search_and_news(last_q)
        if found: ctx = f"\n\n[نتائج البحث والأخبار الحية الموثقة]:\n{found}"

    sys_msg = "أنت DARK HORIZON AI، نظام ذكاء اصطناعي متكامل للأبحاث والبرمجة والتصميم. أجب بالعربية الفصحى بدقة وتنظيم." + ctx
    final_msgs = [{"role": "system", "content": sys_msg}] + [m for m in msgs if m.get("role") != "system"]
    reply = None

    gk = os.environ.get("GROQ_API_KEY", "").strip()
    if gk and not reply:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e67726f712e636f6d2f6f70656e61692f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": final_msgs, "temperature": 0.6}, timeout=14)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: reply = ch.get("message", {}).get("content", "")
        except Exception: pass

    ork = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if ork and not reply:
        for fm in ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free"]:
            try:
                u = bytes.fromhex("68747470733a2f2f6f70656e726f757465722e61692f6170692f76312f636861742f636f6d706c6574696f6e73").decode()
                r = requests.post(u, headers={"Authorization": f"Bearer {ork}", "Content-Type": "application/json"},
                    json={"model": fm, "messages": final_msgs}, timeout=15)
                if r.status_code == 200:
                    ch = next(iter(r.json().get("choices") or []), None)
                    if ch: reply = ch.get("message", {}).get("content", ""); break
            except Exception: pass

    gem = os.environ.get("GEMINI_API_KEY", "").strip()
    if gem and not reply:
        try:
            u = bytes.fromhex("68747470733a2f2f67656e657261746976656c616e67756167652e676f6f676c65617069732e636f6d2f7631626574612f6d6f64656c732f67656d696e692d322e302d666c6173683a67656e6572617465436f6e74656e743f6b65793d").decode()
            r = requests.post(u + gem, json={"contents": [{"parts": [{"text": sys_msg + "\n\n" + last_q}]}]}, timeout=15)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    reply = pt.get("text", "")
        except Exception: pass

    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf and not reply:
        try:
            u = bytes.fromhex("68747470733a2f2f726f757465722e68756767696e67666163652e636f2f68662d696e666572656e63652f6d6f64656c732f5177656e2f5177656e322e352d3732422d496e7374727563742f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": final_msgs, "max_tokens": 900}, timeout=15)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: reply = ch.get("message", {}).get("content", "")
        except Exception: pass

    if reply:
        save_to_cloud(last_q, reply)
        return jsonify({"reply": reply}), 200, cors()
    return jsonify({"error": "busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic masterpiece, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    cid, ctok = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip()
    if cid and ctok:
        try:
            cf_base = bytes.fromhex("68747470733a2f2f6170692e636c6f7564666c6172652e636f6d2f636c69656e742f76342f6163636f756e74732f").decode()
            r = requests.post(cf_base + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell",
                headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 6, "seed": seed}, timeout=18)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass

    fk = os.environ.get("FAL_KEY", "").strip()
    if fk:
        try:
            u = bytes.fromhex("68747470733a2f2f66616c2e72756e2f66616c2d61692f666c75782f7363686e656c6c").decode()
            r = requests.post(u, headers={"Authorization": f"Key {fk}", "Content-Type": "application/json"},
                json={"prompt": prompt, "image_size": "square_hd", "seed": seed}, timeout=18)
            if r.status_code == 200:
                imgs = r.json().get("images") or []
                first_im = next(iter(imgs), None)
                if first_im and first_im.get("url"):
                    img_b = requests.get(first_im["url"], timeout=15).content
                    if len(img_b) > 8000: return Response(img_b, mimetype="image/jpeg", headers=cors())
        except Exception: pass

    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=hf)
            for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"]:
                try:
                    img = client.text_to_image(f"{prompt}, variation {seed}", model=mdl)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=92)
                    if buf.tell() > 8000: return Response(buf.getvalue(), mimetype="image/jpeg", headers=cors())
                except Exception: pass
        except Exception: pass

    return jsonify({"error": "busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
