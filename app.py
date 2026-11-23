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
    return jsonify({"status": "DARK HORIZON INTERNAL & EXTERNAL READY", "ok": True})

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
            u = "".join(map(chr,))
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.6}, timeout=14)
            if r.status_code == 200:
                ch = next(iter(r.json().get("choices") or []), None)
                if ch: return jsonify({"reply": ch.get("message", {}).get("content", "")}), 200, cors()
        except Exception: pass

    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            base_g = "".join(map(chr,))
            r = requests.post(base_g + gem, json={"contents": [{"parts": [{"text": last_q}]}]}, timeout=14)
            if r.status_code == 200:
                ca = next(iter(r.json().get("candidates") or []), None)
                if ca:
                    pt = next(iter(ca.get("content", {}).get("parts") or []), {})
                    return jsonify({"reply": pt.get("text", "")}), 200, cors()
        except Exception: pass

    return jsonify({"error": "internal_chat_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "majestic Arabian horse in golden desert sunset, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            cf_p = "".join(map(chr,))
            r = requests.post(cf_p + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell",
                headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 6, "seed": seed}, timeout=20)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass

    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        hf_p = "".join(map(chr,))
        for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"]:
            try:
                r = requests.post(hf_p + mdl,
                    headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": f"{prompt}, variation {seed}"}, timeout=25)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
            except Exception: pass

    return jsonify({"error": "internal_image_busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
