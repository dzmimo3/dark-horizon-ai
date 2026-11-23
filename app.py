import os, base64, random, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

def smart_web_search(query):
    results = []
    # مصدر 1: Wikipedia API (موسوعة علمية موثقة بالعربية والإنجليزية)
    try:
        w = requests.get("https://wikipedia.org",
            params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 2}, timeout=6).json()
        for item in w.get("query", {}).get("search", []):
            snippet = item.get("snippet", "").replace('<span class="searchmatch">', '').replace('</span>', '')
            results.append(f"- [ويكيبيديا - {item.get('title')}]: {snippet}")
    except Exception: pass

    # مصدر 2: DuckDuckGo Instant API
    try:
        d = requests.get("https://duckduckgo.com", params={"q": query, "format": "json", "no_html": 1}, timeout=6).json()
        if d.get("AbstractText"):
            results.append(f"- [ملخص الويب]: {d['AbstractText']}")
    except Exception: pass

    return "\n".join(results)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON SMART SEARCH & AI ONLINE"})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = msgs[-1]["content"] if msgs else prompt

    # تفعيل البحث الحي تلقائياً عند طلب بحث أو معلومات
    search_ctx = ""
    if any(k in last_q for k in ["بحث", "ابحث", "دراسة", "مقال", "تقرير", "أخبار", "ما هو", "من هو", "كيف"]):
        found = smart_web_search(last_q)
        if found:
            search_ctx = f"\n\n[نتائج البحث الحي الموثقة]:\n{found}"

    sys_msg = "أنت DARK HORIZON AI، محرك بحث ذكي ومساعد برمجي فائق الدقة. استعن بنتائج البحث الحي المرفقة لتقديم إجابات شاملة ومنظمة بالعربية." + search_ctx
    final_msgs = [{"role": "system", "content": sys_msg}] + [m for m in msgs if m.get("role") != "system"]

    gk = os.environ.get("GROQ_API_KEY", "")
    if gk:
        try:
            url = "https:" + "//api." + "://groq.com"
            r = requests.post(url, headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": final_msgs, "temperature": 0.6}, timeout=14)
            if r.status_code == 200:
                ch = r.json().get("choices") or []
                if ch: return jsonify({"reply": ch[0]["message"]["content"]}), 200, cors()
        except Exception: pass

    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            url = "https:" + "//generativelanguage." + "://googleapis.com" + gem
            r = requests.post(url, json={"contents": [{"parts": [{"text": sys_msg + "\n\n" + last_q}]}]}, timeout=14)
            if r.status_code == 200:
                ca = r.json().get("candidates") or []
                if ca: return jsonify({"reply": ca[0]["content"]["parts"][0]["text"]}), 200, cors()
        except Exception: pass

    return jsonify({"error": "busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic masterpiece, 8k photorealistic")
    seed = data.get("seed") or random.randint(1, 9999999)

    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            url = "https:" + "//api." + "://cloudflare.com" + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            r = requests.post(url, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 5, "seed": seed}, timeout=18)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response(base64.b64decode(b64), mimetype="image/jpeg", headers=cors())
        except Exception: pass

    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        for mdl in ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]:
            try:
                url = "https:" + "//router." + "huggingface.co/hf-inference/models/" + mdl
                r = requests.post(url, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": f"{prompt}, variation {seed}"}, timeout=22)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
            except Exception: pass

    return jsonify({"error": "busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
