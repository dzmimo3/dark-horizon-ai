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

    sys_msg = "أنت DARK HORIZON AI، مساعد ذكي شامل للبحث العلمي والبرمجة. أجب بالعربية الفصحى بدقة ووضوح." + ctx
    clean_msgs = [{"role": "system", "content": sys_msg}] + [m for m in msgs if m.get("role") != "system"]
    errs = []

    gk = os.environ.get("GROQ_API_KEY", "").strip()
    if gk:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e67726f712e636f6d2f6f70656e61692f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": clean_msgs}, timeout=15)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch:
                    rep = ch.get("message", {}).get("content", "")
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"Groq:{r.status_code}")
        except Exception as e: errs.append(f"GroqErr:{e}")

    ork = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if ork:
        for mdl in ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"]:
            try:
                u = bytes.fromhex("68747470733a2f2f6f70656e726f757465722e61692f6170692f76312f636861742f636f6d706c6574696f6e73").decode()
                r = requests.post(u, headers={"Authorization": f"Bearer {ork}", "Content-Type": "application/json"},
                    json={"model": mdl, "messages": clean_msgs}, timeout=15)
                if r.status_code == 200:
                    ch = next(iter(r.json().get("choices") or []), None)
                    if ch:
                        rep = ch.get("message", {}).get("content", "")
                        save_db(last_q, rep)
                        return jsonify({"reply": rep}), 200, cors()
                errs.append(f"OR:{r.status_code}")
            except Exception as e: errs.append(f"ORErr:{e}")

    gem = os.environ.get("GEMINI_API_KEY", "").strip()
    if gem:
        try:
            u = bytes.fromhex("68747470733a2f2f67656e657261746976656c616e67756167652e676f6f676c65617069732e636f6d2f7631626574612f6d6f64656c732f67656d696e692d322e302d666c6173683a67656e6572617465436f6e74656e743f6b65793d").decode()
            r = requests.post(u + gem, json={"contents": [{"parts": [{"text": sys_msg + "\n\n" + last_q}]}]}, timeout=15)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    rep = pt.get("text", "")
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"Gem:{r.status_code}")
        except Exception as e: errs.append(f"GemErr:{e}")

    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            u = bytes.fromhex("68747470733a2f2f726f757465722e68756767696e67666163652e636f2f68662d696e666572656e63652f6d6f64656c732f5177656e2f5177656e322e352d3732422d496e7374727563742f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": clean_msgs, "max_tokens": 900}, timeout=15)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch:
                    rep = ch.get("message", {}).get("content", "")
                    save_db(last_q, rep)
                    return jsonify({"reply": rep}), 200, cors()
            errs.append(f"HF:{r.status_code}")
        except Exception as e: errs.append(f"HFErr:{e}")

    return jsonify({"reply": f"⚠️ تعذر الاتصال بالمحركات لحظياً ({', '.join(errs)})."}), 200, cors()

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
