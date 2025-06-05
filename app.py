from flask import Flask, request, render_template, send_file
import requests, time, random
from PIL import Image, ImageDraw
from io import BytesIO

app = Flask(__name__)

# Insert your real Black Forest Lab API key here
API_KEY = 'API_CODE_COMES_HERE'
API_URL = 'https://api.eu1.bfl.ai/v1/flux-pro-1.1-ultra'
GET_URL = "https://api.eu1.bfl.ai/v1/get_result"

@app.route('/', methods=['GET', 'POST'])
def index():
    image_url = None
    error = None

    # Generate a random seed on GET request
    if request.method == 'GET':
        seed_value = random.randint(1, 100)
    else:
        # Use seed value from the form (default is 42)
        seed_value = int(request.form.get('seed', 42))

    if request.method == 'POST':
        # Combine prompt input and additional input
        p1 = request.form['prompt']
        p2 = request.form['cicd']
        prompt = f"{p1}. {p2}"

        # Debug output to track prompt and seed
        print(">>> Submitted Prompt:", prompt)
        print(">>> Submitted Seed:", seed_value)

        try:
            # Submit image generation request
            post = requests.post(
                API_URL,
                headers={
                    "accept": "application/json",
                    "x-key": API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "seed": seed_value,
                    "aspect_ratio": "16:9",
                    "safety_tolerance": 2,
                    "output_format": "jpeg",
                    "raw": True,
                },
                timeout=10
            )

            post.raise_for_status()
            job_id = post.json()["id"]

            # Poll the API to check if the image is ready
            for attempt in range(10):
                poll = requests.get(GET_URL, params={"id": job_id})
                poll.raise_for_status()
                data = poll.json()
                print(f">>> Poll Attempt {attempt+1}: Status = {data.get('status')}")
                if data.get("status") == "Ready" and data.get("result"):
                    image_url = data["result"]["sample"]
                    break
                time.sleep(2)

            # Output the image URL (or None if not available)
            print(">>> Generated Image URL:", image_url)

        except requests.exceptions.HTTPError as http_err:
            error = f"{http_err.response.status_code}: {http_err.response.text}"
        except Exception as e:
            error = str(e)

    return render_template(
        'index.html',
        image_url=image_url,
        error=error,
        seed=seed_value
    )

# Route to create a print-ready image version with bleed and crop marks
@app.route('/print_ready', methods=['POST'])
def print_ready():
    image_url = request.form['image_url']

    # 1) Download the image from the URL
    resp = requests.get(image_url, stream=True)
    resp.raise_for_status()
    img = Image.open(resp.raw).convert("RGB")

    # 2) Resize image to 300 DPI while preserving aspect ratio
    orig_dpi = img.info.get("dpi", (72, 72))[0]
    scale = 300 / orig_dpi
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img_res = img.resize((new_w, new_h), Image.LANCZOS)

    # 3) Add a white bleed margin (e.g. 10 mm)
    bleed_mm = 10
    bleed_px = int((bleed_mm / 25.4) * 300)
    canvas_w = new_w + 2 * bleed_px
    canvas_h = new_h + 2 * bleed_px
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    canvas.paste(img_res, (bleed_px, bleed_px))

    # 4) Draw black cross crop marks on all corners
    draw = ImageDraw.Draw(canvas)
    mark_len = 120  # Total length of crop mark lines
    half = mark_len // 2
    corners = [
        (bleed_px, bleed_px),
        (canvas_w - bleed_px, bleed_px),
        (bleed_px, canvas_h - bleed_px),
        (canvas_w - bleed_px, canvas_h - bleed_px),
    ]
    for cx, cy in corners:
        draw.line([(cx - half, cy), (cx + half, cy)], fill="black", width=5)
        draw.line([(cx, cy - half), (cx, cy + half)], fill="black", width=5)

    # 5) Save the result in memory with DPI metadata
    buf = BytesIO()
    canvas.save(buf, format='JPEG', dpi=(300, 300))
    buf.seek(0)

    return send_file(
        buf,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='bild_print_ready.jpg'
    )

if __name__ == '__main__':
    app.run(debug=True)
