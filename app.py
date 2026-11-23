import os, requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "DARK HORIZON PRO API ONLINE",
        "engine": "black-forest-labs/FLUX.1-dev"
    })

@app.route("/api/image", methods=["POST", "OPTIONS"])
def generate_image():
    if request.method == "OPTIONS":
        return ("", 204, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS"
        })

    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "majestic Arabian horse in golden desert sunset, 8k photorealistic")
    hf_token = os.environ.get("HF_TOKEN", "")

    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    # المولد الأصلي الذي صمم صور الأمس (FLUX.1-dev)
    api_url = "https://huggingface.co"
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 28,
            "guidance_scale": 3.5
        }
    }

    try:
        res = requests.post(api_url, headers=headers, json=payload, timeout=50)
        if res.status_code == 200 and len(res.content) > 10000:
            return Response(res.content, mimetype="image/jpeg", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "الخادم مشغول حالياً، أعد المحاولة"}), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
