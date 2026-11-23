import os, base64, requests
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
    return jsonify({"status": "DARK HORIZON ULTRA FAST ONLINE", "v": "2.0"})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]

    groq_k = os.environ.get("GROQ_API_KEY", "")
    if groq_k:
        try:
            r = requests.post("https://groq.com",
                headers={"Authorization": f"Bearer {groq_k}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs}, timeout=12)
            if r.status_code == 200:
                ch = r.json().get("choices") or []
                if ch:
                    return jsonify({"reply": ch["message"]["content"]}), 200, cors()
        except Exception:
            pass

    gem_k = os.environ.get("GEMINI_API_KEY", "")
    if gem_k:
        try:
            u_txt = msgs[-1]["content"] if msgs else prompt
            r = requests.post(f"https:" + "//generativelanguage." + "://googleapis.com" + gem_k,
                json={"contents": [{"parts": [{"text": u_txt}]}]}, timeout=12)
            if r.status_code == 200:
                ca = r.json().get("candidates") or []
                if ca:
                    return jsonify({"reply": ca["content"]["parts"]["text"]}), 200, cors()
        except Exception:
            pass

    return jsonify({"error": "chat_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS":
        return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "majestic Arabian horse in golden desert sunset, 8k photorealistic")
    errors = []

    # 1. Cloudflare Workers AI FLUX-1-schnell
    cf_id = os.environ.get("CF_ACCOUNT_ID", "")
    cf_tok = os.environ.get("CF_API_TOKEN", "")
    if cf_id and cf_tok:
        try:
            r = requests.post(
                f"https:" + "//api." + "://cloudflare.com" + cf_id + "/ai/run/@cf/black-forest-labs/flux-1-schnell",
                headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 6}, timeout=20
            )
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64:
                    return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
            errors.append(f"CF:{r.status_code}")
        except Exception as e:
            errors.append(f"CF_ERR:{e}")

    # 2. Hugging Face Router (FLUX.1-schnell & FLUX.1-dev)
    hf_tok = os.environ.get("HF_TOKEN", "")
    if hf_tok:
        for mdl in ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]:
            try:
                r = requests.post(
                    f"https:" + "//router." + "huggingface.co/hf-inference/models/" + mdl,
                    headers={"Authorization": f"Bearer {hf_tok}", "Content-Type": "application/json"},
                    json={"inputs": prompt}, timeout=25
                )
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
                errors.append(f"{mdl}:{r.status_code}")
            except Exception as e:
                errors.append(f"HF_ERR:{e}")

    # 3. Fal.ai أو Together / OpenRouter Image إذا توفر مفتاح
    fal_k = os.environ.get("FAL_KEY", "")
    if fal_k:
        try:
            r = requests.post("https:" + "//fal." + "run/fal-ai/flux/schnell",
                headers={"Authorization": f"Key {fal_k}", "Content-Type": "application/json"},
                json={"prompt": prompt, "image_size": "square_hd"}, timeout=20)
            if r.status_code == 200:
                imgs = r.json().get("images") or []
                if imgs and imgs[0].get("url"):
                    img_b = requests.get(imgs[0]["url"], timeout=15).content
                    return Response(img_b, mimetype="image/jpeg", headers=cors())
            errors.append(f"FAL:{r.status_code}")
        except Exception as e:
            errors.append(f"FAL_ERR:{e}")

    return jsonify({"error": "all_failed", "details": errors}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
