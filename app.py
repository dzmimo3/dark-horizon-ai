import os
import requests as http
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors_json(data, status=200):
    r = jsonify(data)
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    r.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return r, status

@app.route("/", methods=["GET"])
def home():
    return cors_json({"status": "DARK HORIZON PRO API ONLINE", "features": ["Text-to-Video", "Image-to-Video", "Gemini 2.0", "Groq", "Cloudflare"]})

@app.route("/health", methods=["GET"])
def health():
    return cors_json({"ok": True})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return cors_json({}, 204)
    d = request.get_json(silent=True) or {}
    msgs = d.get("messages", [])
    img_b64 = d.get("image")
    sys_txt = "أنت DARK HORIZON PRO، مساعد ذكاء اصطناعي خبير تتحدث بالعربية والجزائرية والفرنسية والإنجليزية بطلاقة وأسلوب إنساني ذكي."
    sl = chr(47)

    gem_k = os.environ.get("GEMINI_API_KEY")
    if gem_k:
        try:
            u = f"https:{sl}{sl}://googleapis.com{sl}v1beta{sl}models{sl}gemini-2.0-flash:generateContent?key={gem_k}"
            parts = [{"text": sys_txt + "\n\n" + "\n".join([f"{m.get('role')}: {m.get('content')}" for m in msgs[-6:]])}]
            if img_b64 and "," in img_b64:
                mime, b64d = img_b64.split(",", 1)
                mime = mime.replace("data:", "").replace(";base64", "")
                parts.append({"inline_data": {"mime_type": mime, "data": b64d}})
            r = http.post(u, json={"contents": [{"parts": parts}]}, timeout=25)
            if r.status_code == 200:
                txt = r.json()["candidates"].pop()["content"]["parts"].pop()["text"]
                return cors_json({"reply": txt, "engine": "Gemini 2.0"})
        except Exception:
            pass

    groq_k = os.environ.get("GROQ_API_KEY")
    if groq_k and not img_b64:
        try:
            u = f"https:{sl}{sl}://groq.com{sl}openai{sl}v1{sl}chat{sl}completions"
            r = http.post(u, headers={"Authorization": f"Bearer {groq_k}"}, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": sys_txt}] + msgs[-8:]}, timeout=20)
            if r.status_code == 200:
                txt = r.json()["choices"].pop()["message"]["content"]
                return cors_json({"reply": txt, "engine": "Groq Llama-70B"})
        except Exception:
            pass

    or_k = os.environ.get("OPENROUTER_API_KEY")
    if or_k and not img_b64:
        try:
            u = f"https:{sl}{sl}openrouter.ai{sl}api{sl}v1{sl}chat{sl}completions"
            r = http.post(u, headers={"Authorization": f"Bearer {or_k}"}, json={"model": "meta-llama/llama-3.3-70b-instruct:free", "messages": [{"role": "system", "content": sys_txt}] + msgs[-8:]}, timeout=25)
            if r.status_code == 200:
                txt = r.json()["choices"].pop()["message"]["content"]
                return cors_json({"reply": txt, "engine": "OpenRouter"})
        except Exception:
            pass

    return cors_json({"error": "fallback_to_client"}, 502)

@app.route("/api/cf-image", methods=["POST", "OPTIONS"])
def api_cf_image():
    if request.method == "OPTIONS":
        return cors_json({}, 204)
    d = request.get_json(silent=True) or {}
    prompt = str(d.get("prompt", "cinematic realistic 8k photo")).strip()
    cf_id = os.environ.get("CF_ACCOUNT_ID")
    cf_tok = os.environ.get("CF_API_TOKEN")
    sl = chr(47)
    if cf_id and cf_tok:
        try:
            u = f"https:{sl}{sl}://cloudflare.com{sl}client{sl}v4{sl}accounts{sl}{cf_id}{sl}ai{sl}run{sl}@cf{sl}black-forest-labs{sl}flux-1-schnell"
            r = http.post(u, headers={"Authorization": f"Bearer {cf_tok}"}, json={"prompt": prompt}, timeout=45)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64:
                    return cors_json({"image_b64": f"data:image/jpeg;base64,{b64}"})
        except Exception:
            pass
    return cors_json({"error": "cf_fallback"}, 502)

@app.route("/api/video", methods=["POST", "OPTIONS"])
def api_video():
    if request.method == "OPTIONS":
        return cors_json({}, 204)
    d = request.get_json(silent=True) or {}
    prompt = str(d.get("prompt", "cinematic realistic smooth motion")).strip()
    aspect = str(d.get("aspect", "16:9")).strip()
    img_url = d.get("image_url")
    fal_key = os.environ.get("FAL_KEY")
    if not fal_key:
        return cors_json({"error": "مفتاح FAL_KEY غير مضاف في إعدادات Render"}, 500)
    sl = chr(47)

    if img_url:
        endpoints = [
            f"https:{sl}{sl}fal.run{sl}fal-ai{sl}wan-i2v",
            f"https:{sl}{sl}fal.run{sl}fal-ai{sl}wan{sl}v2.1{sl}image-to-video",
            f"https:{sl}{sl}fal.run{sl}fal-ai{sl}fast-svd"
        ]
        payload = {"prompt": prompt, "image_url": img_url, "aspect_ratio": aspect}
    else:
        endpoints = [
            f"https:{sl}{sl}fal.run{sl}fal-ai{sl}wan-t2v",
            f"https:{sl}{sl}fal.run{sl}fal-ai{sl}wan{sl}v2.1{sl}text-to-video",
            f"https:{sl}{sl}fal.run{sl}fal-ai{sl}fast-svd"
        ]
        payload = {"prompt": prompt, "aspect_ratio": aspect}

    last_err = ""
    for ep in endpoints:
        try:
            res = http.post(
                ep,
                headers={"Authorization": f"Key {fal_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=115
            )
            if res.status_code == 200:
                j = res.json()
                vid_url = (j.get("video") or {}).get("url") or j.get("video_url")
                if vid_url:
                    return cors_json({"video_url": vid_url})
            last_err = f"{res.status_code}: {res.text[:140]}"
        except Exception as ex:
            last_err = str(ex)

    # مسار الطوارئ المجاني عبر Hugging Face عند انتهاء رصيد Fal.ai
    hf_tok = os.environ.get("HF_TOKEN")
    if hf_tok and not img_url:
        for hfm in [f"Wan-AI{sl}Wan2.1-T2V-1.3B", f"zai-org{sl}CogVideoX-2b"]:
            try:
                hu = f"https:{sl}{sl}router.huggingface.co{sl}hf-inference{sl}models{sl}{hfm}"
                hr = http.post(hu, headers={"Authorization": f"Bearer {hf_tok}", "Content-Type": "application/json"}, json={"inputs": prompt}, timeout=90)
                if hr.status_code == 200 and len(hr.content) > 15000:
                    import base64
                    b64v = base64.b64encode(hr.content).decode("utf-8")
                    return cors_json({"video_url": f"data:video/mp4;base64,{b64v}"})
            except Exception:
                pass
    return cors_json({"error": "fallback_to_storyboard"}, 502)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
