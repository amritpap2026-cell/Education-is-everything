"""Asset fetcher with Cloudflare AI primary, multi-provider fallbacks."""
import base64, os, random, time, urllib.parse
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (AutoVideoPipeline/1.0)"}

def _valid(path):
    if not path or not os.path.exists(path): return False
    if os.path.getsize(path) < 5000:
        try: os.remove(path)
        except Exception: pass
        return False
    return True

def fetch_cloudflare_image(prompt: str, scene_id: str):
    from config1 import CF_API_URL, CF_IMAGE_MODEL, get_cloudflare_config
    cfg = get_cloudflare_config()
    if not cfg["account_id"] or not cfg["api_token"]: return None
    url = CF_API_URL.format(account_id=cfg["account_id"], model=CF_IMAGE_MODEL)
    filepath = TEMP_DIR / f"{scene_id}_cf.jpg"
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {cfg['api_token']}", "Content-Type": "application/json"}, json={"prompt": prompt[:2000]}, timeout=120)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                data = r.json()
                if data.get("success") and data.get("result", {}).get("image"):
                    with open(filepath, "wb") as f: f.write(base64.b64decode(data["result"]["image"]))
                    return str(filepath)
            elif content_type.startswith("image/"):
                with open(filepath, "wb") as f: f.write(r.content)
                return str(filepath)
    except Exception: pass
    return None

def fetch_hf_image(prompt: str, scene_id: str):
    from config1 import HF_API_URL, HF_IMAGE_MODEL, get_hf_key
    key = get_hf_key()
    if not key: return None
    url = HF_API_URL.format(model=HF_IMAGE_MODEL)
    filepath = TEMP_DIR / f"{scene_id}_hf.jpg"
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={"inputs": prompt[:1500]}, timeout=120)
        if r.status_code == 200 and len(r.content) > 5000:
            with open(filepath, "wb") as f: f.write(r.content)
            return str(filepath)
    except Exception: pass
    return None

def fetch_unsplash_image(prompt: str, scene_id: str):
    from config1 import UNSPLASH_API_URL, get_unsplash_key
    key = get_unsplash_key()
    if not key: return None
    search_term = " ".join(prompt.split()[:6])
    try:
        r = requests.get(UNSPLASH_API_URL, params={"query": search_term, "per_page": 1, "orientation": "landscape"}, headers={"Authorization": f"Client-ID {key}"}, timeout=30)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                img_url = results[0]["urls"]["regular"]
                filepath = TEMP_DIR / f"{scene_id}_unsplash.jpg"
                img = requests.get(img_url, timeout=60, headers=HEADERS)
                if len(img.content) > 5000:
                    with open(filepath, "wb") as f: f.write(img.content)
                    return str(filepath)
    except Exception: pass
    return None

def fetch_pexels_video(query: str, scene_id: str):
    from config1 import PEXELS_API_URL, get_pexels_key
    key = get_pexels_key()
    if not key: return None
    try:
        r = requests.get(PEXELS_API_URL, params={"query": query, "per_page": 1, "orientation": "landscape"}, headers={"Authorization": key}, timeout=30)
        if r.status_code == 200:
            videos = r.json().get("videos", [])
            if videos:
                vid_url = videos[0]["video_files"][0]["link"]
                filepath = TEMP_DIR / f"{scene_id}_pexels.mp4"
                vid = requests.get(vid_url, timeout=120, headers=HEADERS)
                if len(vid.content) > 5000:
                    with open(filepath, "wb") as f: f.write(vid.content)
                    return str(filepath)
    except Exception: pass
    return None

def fetch_pixabay_video(query: str, scene_id: str):
    from config1 import PIXABAY_API_URL, get_pixabay_key
    key = get_pixabay_key()
    if not key: return None
    try:
        r = requests.get(PIXABAY_API_URL, params={"key": key, "q": query, "per_page": 3}, timeout=30)
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            if hits:
                vid_url = hits[0]["videos"]["large"]["url"]
                filepath = TEMP_DIR / f"{scene_id}_pixabay.mp4"
                vid = requests.get(vid_url, timeout=120, headers=HEADERS)
                if len(vid.content) > 5000:
                    with open(filepath, "wb") as f: f.write(vid.content)
                    return str(filepath)
    except Exception: pass
    return None

def _image_chain(prompt: str, scene_id: str):
    result = fetch_cloudflare_image(prompt, scene_id)
    if result: return result
    result = fetch_hf_image(prompt, scene_id)
    if result: return result
    return fetch_unsplash_image(prompt, scene_id)

def _video_chain(query: str, scene_id: str, primary="pexels"):
    if primary == "pexels":
        result = fetch_pexels_video(query, scene_id)
        if result: return result
        result = fetch_pixabay_video(query, scene_id)
        if result: return result
    else:
        result = fetch_pixabay_video(query, scene_id)
        if result: return result
        result = fetch_pexels_video(query, scene_id)
        if result: return result
    return _image_chain(query, scene_id)

def fetch_asset_for_scene(scene: dict):
    scene_id = scene.get("scene_id", "SCENE_000")
    vtype = scene.get("visual_type", "AI_IMAGE")
    query = scene.get("prompt_or_query", "abstract background")
    source = scene.get("source", "Cloudflare")

    print(f"      DEBUG: {scene_id} | type={vtype} | source={source} | query='{query[:50]}'")

    if vtype == "AI_IMAGE" or source == "Cloudflare":
        result = _image_chain(query, scene_id)
        if result and _valid(result): return result
        vtype = "STOCK_VIDEO"

    if vtype == "STOCK_VIDEO" or source in ("Pexels", "Pixabay"):
        primary = "pixabay" if source == "Pixabay" else "pexels"
        result = _video_chain(query, scene_id, primary=primary)
        if result and _valid(result): return result

    return _image_chain(query, scene_id)

def generate_custom_thumbnail(prompt: str, header_text: str, subheader_text: str, language: str) -> str:
    """Generates a background (rotating AI/Unsplash) and overlays centered YouTube-style text."""
    if random.choice([True, False]):
        print("      Thumbnail Background: Cloudflare AI")
        bg_path = fetch_cloudflare_image(prompt, "THUMBNAIL")
        if not bg_path: bg_path = fetch_unsplash_image(prompt, "THUMBNAIL")
    else:
        print("      Thumbnail Background: Unsplash Stock")
        bg_path = fetch_unsplash_image(prompt, "THUMBNAIL")
        if not bg_path: bg_path = fetch_cloudflare_image(prompt, "THUMBNAIL")

    if not bg_path or not _valid(bg_path): return None

    img = Image.open(bg_path).convert("RGBA")
    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
    
    # Dark overlay for text readability
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 100))
    img = Image.alpha_composite(img, overlay)
    
    draw = ImageDraw.Draw(img)
    
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if language in ["Hindi", "Nepali"]:
        font_path = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
    
    try:
        header_font = ImageFont.truetype(font_path, 140)
        sub_font = ImageFont.truetype(font_path, 70)
    except Exception:
        header_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    # Center Header
    draw.text((640, 300), header_text.upper(), font=header_font, fill="#FFE600", stroke_width=14, stroke_fill="black", anchor="mm")
    # Center Subheader
    draw.text((640, 450), subheader_text, font=sub_font, fill="white", stroke_width=8, stroke_fill="black", anchor="mm")

    final_thumb_path = TEMP_DIR / "final_thumbnail.jpg"
    img.convert("RGB").save(final_thumb_path, quality=95)
    
    print(f"      ✓ Thumbnail generated: {final_thumb_path}")
    return str(final_thumb_path)
