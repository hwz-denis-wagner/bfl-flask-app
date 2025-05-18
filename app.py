from flask import Flask, render_template, request
import requests
import time
import os

app = Flask(__name__)

# API-Konfiguration
# API_KEY = os.getenv("BFL_API_KEY")  # wird bei Render als Environment Variable gesetzt
API_KEY = os.getenv("BFL_API_KEY") or "f678b2cb-31e9-40e0-b553-739ed37f48fc"
POST_URL = "https://api.us1.bfl.ai/v1/flux-pro-1.1-ultra"
GET_URL = "https://api.us1.bfl.ai/v1/get_result"

@app.route("/", methods=["GET", "POST"])
def index():
    image_url = None
    prompt = ""

    if request.method == "POST":
        prompt = request.form.get("prompt")
        print(f">>> Prompt empfangen: {prompt}")

        payload = {
            "prompt": prompt,
            "prompt_upsampling": False,
            "seed": 42,
            "aspect_ratio": "16:9",
            "safety_tolerance": 2,
            "output_format": "jpeg",
            "raw": False,
            "image_prompt": "",
            "image_prompt_strength": 0.1,
            "webhook_url": "",
            "webhook_secret": ""
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        try:
            res = requests.post(POST_URL, json=payload, headers=headers)
            print(">>> BFL POST Status:", res.status_code)
            print(">>> BFL POST Response:", res.text)

            if res.status_code == 200 and "id" in res.json():
                job_id = res.json()["id"]
                print(f">>> Job ID erhalten: {job_id}")

                for i in range(10):
                    poll_res = requests.get(GET_URL, params={"id": job_id})
                    print(f"[{i}] Polling Status:", poll_res.status_code)
                    print(f"[{i}] Polling Response:", poll_res.text)

                    if poll_res.status_code == 200:
                        data = poll_res.json()
                        if data["status"] == "succeeded" and data.get("result"):
                            image_url = data["result"].get("image_url")
                            print(">>> Bild URL:", image_url)
                            break
                    time.sleep(2)

        except Exception as e:
            print(">>> Fehler bei API-Anfrage:", e)

    return render_template("index.html", image_url=image_url, prompt=prompt)

# WICHTIG: Kein app.run() in Render!
