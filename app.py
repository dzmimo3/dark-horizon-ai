import os, base64, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

def live_web_research(query):
    """جلب معلومات حية من الويب والموسوعات لدعم الأبحاث"""
    snippets = []
    try:
        r = requests.get("https://duckduckgo.com", params={"q": query, "format": "json", "no_html": 1}, timeout=8).json()
        if r.get("AbstractText"):
            snippets.append(f"- ملخص معرفي: {r['AbstractText']} (المصدر: {r.get('AbstractURL', 'Web')})")
        for topic in (r.get("RelatedTopics") or [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                snippets.append(f"- {topic['Text']}")
    except Exception:
        pass
    return "\n".join(snippets)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DARK HORIZON EMPIRE CORE ONLINE", "mode": "Autonomous Multi-Engine"})

@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    msgs = data.get("messages") or [{"role": "user", "content": prompt}]
    last_q = msgs[-1]["content"] if msgs else prompt

    # تفعيل البحث الحي تلقائياً عند طلب بحث أو معلومات حديثة
    web_context = ""
    if any(k in last_q for k in ["بحث", "ابحث", "دراسة", "مقال", "تقرير", "أخبار", "ما هو", "كيف يعمل", "تاريخ"]):
        web_data = live_web_research(last_q)
        if web_data:
            web_context = f"\n\n[بيانات حية من الإنترنت للاستعانة بها وتوثيق البحث]:\n{web_data}"

    sys_prompt = (
        "أنت DARK HORIZON AI، نظام ذكاء اصطناعي فائق وشامل. "
        "عند طلب بحث أو دراسة: اكتب بحثاً علمياً منظماً بعناوين رئيسية، مقدمة، تحليل عميق، نقاط دقيقة، وخاتمة. "
        "عند طلب برمجة: اكتب كوداً كاملاً نظيفاً جاهزاً للتنفيذ. "
        "تحدث بالعربية الفصحى السلسة والدقيقة." + web_context
    )

    final_msgs = [{"role": "system", "content": sys_prompt}] + [m for m in msgs if m.get("role") != "system"]

    # 1. Groq Llama-3.3-70B (سرعة خارقة)
    gk = os.environ.get("GROQ_API_KEY", "")
    if gk:
        try:
            r = requests.post("https://groq.com",
                headers={"Authorization": f"Bearer {gk}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": final_msgs, "temperature": 0.6}, timeout=15)
            if r.status_code == 200:
                ch = r.json().get("choices") or []
                if ch: return jsonify({"reply": ch[0]["message"]["content"]}), 200, cors()
        except Exception:
            pass

    # 2. Google Gemini 2.0 Flash (تحليل عميق وأبحاث طويلة)
    gem = os.environ.get("GEMINI_API_KEY", "")
    if gem:
        try:
            url = "https:" + "//generativelanguage." + "://googleapis.com" + gem
            full_text = sys_prompt + "\n\nالسؤال:\n" + last_q
            r = requests.post(url, json={"contents": [{"parts": [{"text": full_text}]}]}, timeout=15)
            if r.status_code == 200:
                ca = r.json().get("candidates") or []
                if ca: return jsonify({"reply": ca[0]["content"]["parts"][0]["text"]}), 200, cors()
        except Exception:
            pass

    return jsonify({"error": "all_engines_busy"}), 503, cors()

@app.route("/api/image", methods=["POST", "OPTIONS"])
def api_image():
    if request.method == "OPTIONS": return ("", 204, cors())
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "cinematic masterpiece, 8k photorealistic")

    # 1. Cloudflare Workers AI FLUX-1-schnell (سريع ونقي 100%)
    cid, ctok = os.environ.get("CF_ACCOUNT_ID", ""), os.environ.get("CF_API_TOKEN", "")
    if cid and ctok:
        try:
            url = "https:" + "//api." + "://cloudflare.com" + cid + "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            r = requests.post(url, headers={"Authorization": f"Bearer {ctok}", "Content-Type": "application/json"},
                json={"prompt": prompt, "steps": 6}, timeout=20)
            if r.status_code == 200:
                b64 = r.json().get("result", {}).get("image")
                if b64: return Response
        except Exception:
            pass

    # 2. Hugging Face FLUX.1-dev (واقعية فوتوغرافية فائقة 1024x1024)
    hf = os.environ.get("HF_TOKEN", "")
    if hf:
        for mdl in ["black-forest-labs/FLUX.1-dev", "black-forest-labs/FLUX.1-schnell"]:
            try:
                url = "https:" + "//router." + "huggingface.co/hf-inference/models/" + mdl
                r = requests.post(url, headers={"Authorization": f"Bearer {hf}", "Content-Type": "application/json"},
                    json={"inputs": prompt}, timeout=25)
                if r.status_code == 200 and len(r.content) > 8000:
                    return Response(r.content, mimetype="image/jpeg", headers=cors())
            except Exception:
                pass

    return jsonify({"error": "image_engines_busy"}), 503, cors()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
