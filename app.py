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
    return jsonify({"status": "DARK HORIZON CLOUDFLARE + HF FLUX ACTIVE", "ok": True})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = next(reversed(msgs), {"content": prompt}).get("content", prompt)

    gk = os.environ.get("GROQ_API_KEY", "")
    if gk:
        try:
            u = bytes.fromhex("68747470733a2f2f6170692e67726f712e636f6d2f6f70656e61692f76312f636861742f636f6d706c6574696f6e73").decode()
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.6}, timeout=14)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: return jsonify({"reply": ch.get("message", {}).get("content", "")}), 200, cors()
        except Exception: pass

    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            u = bytes.fromhex("68747470733a2f2f67656e657261746976656c616e67756167652e676f6f676c65617069732e636f6d2f7631626574612f6d6f64656c732f67656d696e692d322e302d666c6173683a67656e6572617465436f6e74656e743f6b65793d").decode()
            r = requests.post(u + gem, json={"contents": [{"parts": [{"text": last_q}]}]}, timeout=14)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    return jsonify({"reply": pt.get("text", "")}), 200, cors()
        except Exception: pass

    return jsonify({"error": "chat_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic masterpiece, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    # 1. Cloudflare Workers AI FLUX-1-schnell (سريع ونقي 100%)
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

    # 2. Hugging Face Router (FLUX.1-dev & SD 3.5 Large)
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

    return jsonify({"error": "image_busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
