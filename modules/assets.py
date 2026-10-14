"""Asset fetcher with Cloudflare AI primary, multi-provider fallbacks."""
import base64
import os
import random
import time
import urllib.parse
from pathlib import Path

import requests

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (AutoVideoPipeline/1.0)"}


def _valid(path):
    if not path or not os.path.exists(path):
        return False
    if os.path.getsize(path) < 5000:
        try:
            os.remove(path)
        except Exception:
            pass
        return False
    return True


# ==================== CLOUDFLARE WORKERS AI ====================
def fetch_cloudflare_image(prompt: str, scene_id: str):
    """Cloudflare Workers AI - FLUX.1-schnell (10,000 free neurons/day)."""
    from config1 import CF_API_URL, CF_IMAGE_MODEL, get_cloudflare_config
    cfg = get_cloudflare_config()
    if not cfg["account_id"] or not cfg["api_token"]:
        print(f"      Cloudflare: missing account_id or token")
        return None

    url = CF_API_URL.format(account_id=cfg["account_id"], model=CF_IMAGE_MODEL)
    filepath = TEMP_DIR / f"{scene_id}_cf.jpg"
    try:
        r = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {cfg['api_token']}",
                "Content-Type": "application/json",
            },
                        json={"prompt": prompt[:2000]},
            timeout=120,
        )
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "")
            # FLUX via Cloudflare returns JSON with base64 image
            if content_type.startswith("application/json"):
                data = r.json()
                if data.get("success") and data.get("result", {}).get("image"):
                    img_bytes = base64.b64decode(data["result"]["image"])
                    with open(filepath, "wb") as f:
                        f.write(img_bytes)
                    return str(filepath)
                print(f"      Cloudflare JSON error: {str(data)[:150]}")
            # Some models return raw bytes
            elif content_type.startswith("image/"):
                with open(filepath, "wb") as f:
                    f.write(r.content)
                return str(filepath)
        print(f"      Cloudflare status {r.status_code} body {r.text[:200]}")
    except Exception as e:
        print(f"      Cloudflare exception: {str(e)[:120]}")
    return None


# ==================== HUGGING FACE (fallback) ====================
def fetch_hf_image(prompt: str, scene_id: str):
    """Hugging Face router - FLUX.1-schnell."""
    from config1 import HF_API_URL, HF_IMAGE_MODEL, get_hf_key
    key = get_hf_key()
    if not key:
        return None
    url = HF_API_URL.format(model=HF_IMAGE_MODEL)
    filepath = TEMP_DIR / f"{scene_id}_hf.jpg"
    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"inputs": prompt[:1500]},
            timeout=120,
        )
        if r.status_code == 200 and len(r.content) > 5000:
            with open(filepath, "wb") as f:
                f.write(r.content)
            return str(filepath)
        print(f"      HF status {r.status_code} size {len(r.content)}")
    except Exception as e:
        print(f"      HF exception: {str(e)[:100]}")
    return None


# ==================== UNSPLASH (fallback) ====================
def fetch_unsplash_image(prompt: str, scene_id: str):
    from config1 import UNSPLASH_API_URL, get_unsplash_key
    key = get_unsplash_key()
    if not key:
        return None
    search_term = " ".join(prompt.split()[:6])
    try:
        r = requests.get(
            UNSPLASH_API_URL,
            params={"query": search_term, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {key}"},
            timeout=30,
        )
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                img_url = results[0]["urls"]["regular"]
                filepath = TEMP_DIR / f"{scene_id}_unsplash.jpg"
                img = requests.get(img_url, timeout=60, headers=HEADERS)
                if len(img.content) > 5000:
                    with open(filepath, "wb") as f:
                        f.write(img.content)
                    return str(filepath)
        else:
            print(f"      Unsplash status {r.status_code}")
    except Exception as e:
        print(f"      Unsplash exception: {str(e)[:80]}")
    return None


# ==================== PEXELS VIDEO ====================
def fetch_pexels_video(query: str, scene_id: str):
    from config1 import PEXELS_API_URL, get_pexels_key
    key = get_pexels_key()
    if not key:
        return None
    try:
        r = requests.get(
            PEXELS_API_URL,
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": key},
            timeout=30,
        )
        if r.status_code == 200:
            videos = r.json().get("videos", [])
            if videos:
                vid_url = videos[0]["video_files"][0]["link"]
                filepath = TEMP_DIR / f"{scene_id}_pexels.mp4"
                vid = requests.get(vid_url, timeout=120, headers=HEADERS)
                if len(vid.content) > 5000:
                    with open(filepath, "wb") as f:
                        f.write(vid.content)
                    return str(filepath)
        print(f"      Pexels status {r.status_code}")
    except Exception as e:
        print(f"      Pexels exception: {str(e)[:80]}")
    return None


# ==================== PIXABAY VIDEO ====================
def fetch_pixabay_video(query: str, scene_id: str):
    from config1 import PIXABAY_API_URL, get_pixabay_key
    key = get_pixabay_key()
    if not key:
        return None
    try:
        r = requests.get(PIXABAY_API_URL, params={"key": key, "q": query, "per_page": 3}, timeout=30)
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            if hits:
                vid_url = hits[0]["videos"]["large"]["url"]
                filepath = TEMP_DIR / f"{scene_id}_pixabay.mp4"
                vid = requests.get(vid_url, timeout=120, headers=HEADERS)
                if len(vid.content) > 5000:
                    with open(filepath, "wb") as f:
                        f.write(vid.content)
                    return str(filepath)
    except Exception as e:
        print(f"      Pixabay exception: {str(e)[:80]}")
    return None


# ==================== ROUTER ====================
def _image_chain(prompt: str, scene_id: str):
    """Tries: Cloudflare -> HuggingFace -> Unsplash."""
    result = fetch_cloudflare_image(prompt, scene_id)
    if result:
        return result
    print(f"      Fallback -> HuggingFace")
    result = fetch_hf_image(prompt, scene_id)
    if result:
        return result
    print(f"      Fallback -> Unsplash")
    return fetch_unsplash_image(prompt, scene_id)


def _video_chain(query: str, scene_id: str, primary="pexels"):
    """Tries: primary video -> other video -> image fallback."""
    if primary == "pexels":
        result = fetch_pexels_video(query, scene_id)
        if result:
            return result
        print(f"      Fallback -> Pixabay")
        result = fetch_pixabay_video(query, scene_id)
        if result:
            return result
    else:
        result = fetch_pixabay_video(query, scene_id)
        if result:
            return result
        print(f"      Fallback -> Pexels")
        result = fetch_pexels_video(query, scene_id)
        if result:
            return result
    print(f"      Fallback -> AI image")
    return _image_chain(query, scene_id)


def fetch_asset_for_scene(scene: dict):
    scene_id = scene.get("scene_id", "SCENE_000")
    vtype = scene.get("visual_type", "AI_IMAGE")
    query = scene.get("prompt_or_query", "abstract background")
    source = scene.get("source", "Pollinations")

    print(f"      DEBUG: {scene_id} | type={vtype} | source={source} | query='{query[:55]}'")

    result = None

    if source == "Pexels":
        result = _video_chain(query, scene_id, primary="pexels")
    elif source == "Pixabay":
        result = _video_chain(query, scene_id, primary="pixabay")
    elif vtype == "STOCK_VIDEO":
        result = _video_chain(query, scene_id, primary="pexels")
    elif vtype == "MOTION_GRAPHIC" or source == "Library":
        # Motion graphics rendered as image with Ken Burns
        result = _image_chain(query, scene_id)
    elif vtype in ("AI_IMAGE", "AI_VIDEO_LOOP"):
        result = _image_chain(query, scene_id)
    else:
        result = _image_chain(query, scene_id)

    if result and _valid(result):
        print(f"      OK {scene_id}: {result}")
        return result
    print(f"      FAIL {scene_id}: all sources exhausted")
    return None