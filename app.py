import os, base64, random, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON PRIMARY GATEWAYS ACTIVE (g4f + HF + OpenRouter + CF + Groq)"})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = next(reversed(msgs), {"content": prompt}).get("content", prompt)

    # 1. أساسي: Groq Llama-3.3-70B (أسرع استجابة في العالم)
    gk = os.environ.get("GROQ_API_KEY", "").strip()
    if gk:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e67726f712e636f6d2f6f70656e61692f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.6}, timeout=12)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: return jsonify({"reply": ch.get("message", {}).get("content", ""), "engine": "groq-primary"}), 200, cors()
        except Exception: pass

    # 2. أساسي: OpenRouter Free Pool (مئات النماذج المجانية المتجددة)
    ork = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if ork:
        for fm in ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"]:
            try:
                u = bytes.fromhex("68747470733a2f2f6f70656e726f757465722e61692f6170692f76312f636861742f636f6d706c6574696f6e73").decode()
                r = requests.post(u, headers={"Authorization": f"Bearer {ork}", "Content-Type": "application/json"},
                    json={"model": fm, "messages": msgs}, timeout=14)
                if r.status_code == 200:
                    ch = next(iter(r.json().get("choices") or []), None)
                    if ch: return jsonify({"reply": ch.get("message", {}).get("content", ""), "engine": fm}), 200, cors()
            except Exception: pass

    # 3. أساسي: bوابة g4f (GPT4Free - مزودون مفتوحون بدون قيود)
    try:
        import g4f
        resp = g4f.ChatCompletion.create(model=g4f.models.default, messages=msgs)
        if resp and len(str(resp)) > 2:
            return jsonify({"reply": str(resp), "engine": "g4f-primary"}), 200, cors()
    except Exception: pass

    # 4. أساسي: Google Gemini 2.0 Flash
    gem = os.environ.get("GEMINI_API_KEY", "").strip()
    if gem:
        try:
            u = bytes.fromhex("68747470733a2f2f67656e657261746976656c616e67756167652e676f6f676c65617069732e636f6d2f7631626574612f6d6f64656c732f67656d696e692d322e302d666c6173683a67656e6572617465436f6e74656e743f6b65793d").decode()
            r = requests.post(u + gem, json={"contents": [{"parts": [{"text": last_q}]}]}, timeout=14)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    return jsonify({"reply": pt.get("text", ""), "engine": "gemini-primary"}), 200, cors()
        except Exception: pass

    return jsonify({"error": "busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic masterpiece, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    # 1. أساسي: Cloudflare Workers AI FLUX-1-schnell (10,000 وحدة مجانية يومياً)
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

    # 2. أساسي: Fal.ai FLUX Schnell
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

    # 3. أساسي: Hugging Face InferenceClient (FLUX.1-dev & FLUX.1-schnell)
    hf = os.environ.get("HF_TOKEN", "").strip()
    if hf:
        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=hf)
            for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"]:
                try:
                    img = client.text_to_image(f"{prompt}, variation {seed}", model=mdl)
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=92)
                    if buf.tell() > 8000:
                        return Response(buf.getvalue(), mimetype="image/jpeg", headers=cors())
                except Exception: pass
        except Exception: pass

    # 4. أساسي: بوابة g4f Images (توليد صور مجاني مفتوح بدون قيود)
    try:
        from g4f.client import Client
        gclient = Client()
        res = gclient.images.generate(model="flux", prompt=prompt, response_format="url")
        d_list = getattr(res, "data", []) or []
        first_d = next(iter(d_list), None)
        if first_d and getattr(first_d, "url", None):
            img_b = requests.get(first_d.url, timeout=15).content
            if len(img_b) > 8000:
                return Response(img_b, mimetype="image/jpeg", headers=cors())
    except Exception: pass

    return jsonify({"error": "busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
