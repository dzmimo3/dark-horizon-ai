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
    return jsonify({"status": "DARK HORIZON 100% FIXED", "ok": True})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_msg = next(reversed(msgs), {"content": prompt})
    last_q = last_msg.get("content", prompt)

    # 1. Groq Llama-3.3-70B
    gk = os.environ.get("GROQ_API_KEY", "")
    if gk:
        try:
            u = "".join(map(chr, [104,116,116,112,115,58,47,47,97,112,105,46,103,114,111,113,46,99,111,109,47,111,112,101,110,97,105,47,118,49,47,99,104,97,116,47,99,111,109,112,108,101,116,105,111,110,115]))
            r = requests.post(u, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": msgs, "temperature": 0.6}, timeout=15)
            if r.status_code == 200:
                first_ch = next(iter(r.json().get("choices") or []), None)
                if first_ch:
                    return jsonify({"reply": first_ch.get("message", {}).get("content", "")}), 200, cors()
        except Exception: pass

    # 2. Google Gemini 2.0 Flash
    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            base_g = "".join(map(chr, [104,116,116,112,115,58,47,47,103,101,110,101,114,97,116,105,118,101,108,97,110,103,117,97,103,101,46,103,111,111,103,108,101,97,112,105,115,46,99,111,109,47,118,49,98,101,116,97,47,109,111,100,101,108,115,47,103,101,109,105,110,105,45,50,46,48,45,102,108,97,115,104,58,103,101,110,101,114,97,116,101,67,111,110,116,101,110,116,63,107,101,121,61]))
            r = requests.post(base_g + gem, json={"contents": [{"parts": [{"text": last_q}]}]}, timeout=15)
            if r.status_code == 200:
                first_ca = next(iter(r.json().get("candidates") or []), None)
                if first_ca:
                    first_pt = next(iter(first_ca.get("content", {}).get("parts") or []), {})
                    return jsonify({"reply": first_pt.get("text", "")}), 200, cors()
        except Exception: pass

    return jsonify({"error": "chat_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "luxury sports car at sunset, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)
    errs = []

    # 1. Cloudflare Workers AI FLUX-1-schnell
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            cf_prefix = "".join(map(chr, [104,116,116,112,115,58,47,47,97,112,105,46,99,108,111,117,100,102,108,97,114,101,46,99,111,109,47,99,108,105,101,110,116,47,118,52,47,97,99,99,111,117,110,116,115,47]))
            cf_suffix = "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            r = requests.post(cf_prefix + cid + cf_suffix,
                headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 5, "seed": seed}, timeout=20)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
            errs.append(f"CF:{r.status_code}")
        except Exception as e:
            errs.append(f"CF_E:{e}")

    # 2. Hugging Face Router (FLUX.1-schnell & FLUX.1-dev)
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        hf_prefix = "".join(map(chr, [104,116,116,112,115,58,47,47,114,111,117,116,101,114,46,104,117,103,103,105,110,103,102,97,99,101,46,99,111,47,104,102,45,105,110,102,101,114,101,110,99,101,47,109,111,100,101,108,115,47]))
        for mdl in ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]:
            try:
                r = requests.post(hf_prefix + mdl,
                    headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": f"{prompt}, variation {seed}"}, timeout=25)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
                errs.append(f"{mdl}:{r.status_code}")
            except Exception as e:
                errs.append(f"HF_E:{e}")

    return jsonify({"error": "image_busy", "details": errs}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
