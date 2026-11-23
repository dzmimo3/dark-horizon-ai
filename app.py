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
    return jsonify({"status": "DARK HORIZON ALL ENGINES FIXED"})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = msgs[-1]["content"] if msgs else prompt

    gk = os.environ.get("GROQ_API_KEY", "")
    if gk:
        try:
            u = "https:" + "//api." + "://groq.com"
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.6}, timeout=15)
            if r.status_code == 200:
                ch = r.json().get("choices") or []
                if len(ch) > 0:
                    return jsonify({"reply": ch[0]["message"]["content"]}), 200, cors()
        except Exception: pass

    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            u = "https:" + "//generativelanguage." + "://googleapis.com" + gem
            r = requests.post(u, json={"contents": [{"parts": [{"text": last_q}]}]}, timeout=15)
            if r.status_code == 200:
                ca = r.json().get("candidates") or []
                if len(ca) > 0:
                    return jsonify({"reply": ca[0]["content"]["parts"][0]["text"]}), 200, cors()
        except Exception: pass

    return jsonify({"error": "chat_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "luxury sports car at sunset, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    # 1. Cloudflare Workers AI FLUX-1-schnell
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            u = "https:" + "//api." + "://cloudflare.com" + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            r = requests.post(u, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 5, "seed": seed}, timeout=20)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass

    # 2. Hugging Face Router FLUX.1-schnell & FLUX.1-dev
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        for mdl in ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]:
            try:
                u = "https:" + "//router." + "huggingface.co/hf-inference/models/" + mdl
                r = requests.post(u, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": f"{prompt}, variation {seed}"}, timeout=25)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
            except Exception: pass

    return jsonify({"error": "image_busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
