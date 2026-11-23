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
    return jsonify({"status": "DARK HORIZON EMPIRE API ONLINE", "engines": ["Gemini-2.0", "Groq-Llama3", "Cloudflare-FLUX", "HF-FLUX-Dev", "Web-Search"]})

# 1. مسار البحث الحي في الإنترنت (بيانات حية مجانية)
@app.route("/api/search", methods=["POST", "OPTIONS"])
def api_search():
    if request.method == "OPTIONS": return ("", 204, cors())
    q = (request.get_json(silent=True) or {}).get("query", "")
    try:
        r = requests.get("https://duckduckgo.com", params={"q": q, "format": "json", "no_html": 1}, timeout=10).json()
        ans = r.get("AbstractText") or (r.get("RelatedTopics") or [{}]).get("Text", "")
        return jsonify({"result": ans or "تم البحث، جاري التحليل عبر الذكاء الاصطناعي."}), 200, cors()
    except Exception:
        return jsonify({"result": ""}), 200, cors()

# 2. مسار الدردشة وتدوير الحصص اليومية (Groq -> Gemini 2.0 -> HF Qwen)
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]

    # الحصة 1: Groq Llama-3.3-70B
    gk = os.environ.get("GROQ_API_KEY", "")
    if gk:
        try:
            r = requests.post("https://groq.com",
                headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs}, timeout=12)
            if r.status_code == 200:
                ch = r.json().get("choices") or []
                if ch: return jsonify({"reply": ch["message"]["content"]}), 200, cors()
        except Exception: pass

    # الحصة 2: Google Gemini 2.0 Flash
    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            ut = msgs[-1]["content"] if msgs else prompt
            url = "https:" + "//generativelanguage." + "://googleapis.com" + gem
            r = requests.post(url, json={"contents": [{"parts": [{"text": ut}]}]}, timeout=12)
            if r.status_code == 200:
                ca = r.json().get("candidates") or []
                if ca: return jsonify({"reply": ca["content"]["parts"]["text"]}), 200, cors()
        except Exception: pass

    # الحصة 3: Hugging Face Qwen 2.5
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        try:
            url = "https:" + "//router." + "huggingface.co/hf-inference/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions"
            r = requests.post(url, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": msgs, "max_tokens": 800}, timeout=15)
            if r.status_code == 200:
                ch = r.json().get("choices") or []
                if ch: return jsonify({"reply": ch["message"]["content"]}), 200, cors()
        except Exception: pass

    return jsonify({"error": "all_chat_quotas_busy"}), 503, cors()

# 3. مسار الصور النقية 8K وتدوير الحصص (Cloudflare FLUX -> HF FLUX.1-dev -> HF SD 3.5)
@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "majestic Arabian horse in golden desert sunset, 8k photorealistic")

    # الحصة 1: Cloudflare Workers AI FLUX-1-schnell
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            url = "https:" + "//api." + "://cloudflare.com" + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            r = requests.post(url, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 6}, timeout=20)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass

    # الحصة 2 و 3: Hugging Face FLUX.1-dev & SD 3.5 Large
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-3.5-large"]:
            try:
                url = "https:" + "//router." + "huggingface.co/hf-inference/models/" + mdl
                r = requests.post(url, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": prompt}, timeout=25)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
            except Exception: pass

    return jsonify({"error": "all_image_quotas_busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
