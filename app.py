import os, base64, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON PRO API ONLINE", "engine": "FLUX.1-dev + Cloudflare + Gemini + Groq"})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]

    # 1. Groq Llama-3.3-70B (سريع جداً)
    groq_k = os.environ.get("GROQ_API_KEY", "")
    if groq_k:
        try:
            r = requests.post("https://groq.com",
                headers={"Authorization": f"Bearer {groq_k}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs}, timeout=20)
            if r.status_code == 200:
                rep = r.json()["choices"][0]["message"]["content"]
                return jsonify({"reply": rep}), 200, cors_headers()
        except Exception:
            pass

    # 2. Gemini 2.0 Flash
    gem_k = os.environ.get("GEMINI_API_KEY", "")
    if gem_k:
        try:
            user_txt = msgs[-1]["content"] if msgs else prompt
            r = requests.post(f"https://googleapis.com{gem_k}",
                json={"contents": [{"parts": [{"text": user_txt}]}]}, timeout=20)
            if r.status_code == 200:
                rep = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"reply": rep}), 200, cors_headers()
        except Exception:
            pass

    return jsonify({"error": "chat_busy"}), 503, cors_headers()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "majestic Arabian horse in golden desert sunset, 8k photorealistic")

    # 1. Hugging Face FLUX.1-dev & FLUX.1-schnell (نفس مولد صور الأمس 1024x1024)
    hf_tok = os.environ.get("HF_TOKEN", "")
    if hf_tok:
        for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"]:
            try:
                r = requests.post(
                    f"https://huggingface.co{mdl}",
                    headers={"Authorization": f"Bearer {hf_tok}", "Content-Type": "application/json"},
                    json={"inputs": prompt, "parameters": {"width": 1024, "height": 1024}},
                    timeout=45
                )
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors_headers())
            except Exception:
                pass

    # 2. Cloudflare Workers AI FLUX-1-schnell (موجود لديك CF_ACCOUNT_ID و CF_API_TOKEN في Render!)
    cf_id = os.environ.get("CF_ACCOUNT_ID", "")
    cf_tok = os.environ.get("CF_API_TOKEN", "")
    if cf_id and cf_tok:
        try:
            r = requests.post(
                f"https://cloudflare.com{cf_id}/ai/run/@cf/black-forest-labs/flux-1-schnell",
                headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 8},
                timeout=35
            )
            if r.status_code == 200:
                res_j = r.json()
                b64 = res_j.get("result", {}).get("image")
                if b64:
                    return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors_headers())
        except Exception:
            pass

    return jsonify({"error": "image_busy"}), 503, cors_headers()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
