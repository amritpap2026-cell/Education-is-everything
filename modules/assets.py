"""Free asset fetcher for Pollinations.ai, Pexels, and Pixabay."""
import os, requests, random, urllib.parse, time
from pathlib import Path

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (AutoVideoPipeline)"}


def fetch_pollinations_image(prompt: str, scene_id: str) -> str:
    """Downloads a free AI image from Pollinations.ai"""
    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1920&height=1080&nologo=true&seed={int(time.time())}"
    filepath = TEMP_DIR / f"{scene_id}_image.jpg"
    try:
        response = requests.get(url, timeout=120, headers=HEADERS)
        if response.status_code == 200 and len(response.content) > 5000:
            with open(filepath, "wb") as f:
                f.write(response.content)
            return str(filepath)
        else:
            print(f"      Pollinations returned status {response.status_code}, size {len(response.content)}")
    except Exception as e:
        print(f"      Pollinations exception: {e}")
    return None


def fetch_pexels_video(query: str, scene_id: str) -> str:
    """Searches and downloads a stock video from Pexels."""
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        print("      PEXELS_API_KEY missing in .env")
        return None
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page=1&orientation=landscape"
    try:
        res = requests.get(url, headers=headers, timeout=30).json()
        if res.get("videos"):
            video_url = res["videos"][0]["video_files"][0]["link"]
            filepath = TEMP_DIR / f"{scene_id}_pexels.mp4"
            vid_data = requests.get(video_url, timeout=120, headers=HEADERS)
            if len(vid_data.content) > 5000:
                with open(filepath, "wb") as f:
                    f.write(vid_data.content)
                return str(filepath)
        else:
            print(f"      Pexels returned no videos for '{query}'")
    except Exception as e:
        print(f"      Pexels exception: {e}")
    return None


def fetch_pixabay_video(query: str, scene_id: str) -> str:
    """Searches and downloads a stock video from Pixabay."""
    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        print("      PIXABAY_API_KEY missing in .env")
        return None
    url = f"https://pixabay.com/api/videos/?key={api_key}&q={urllib.parse.quote(query)}&per_page=3"
    try:
        res = requests.get(url, timeout=30, headers=HEADERS).json()
        if res.get("hits"):
            video_url = res["hits"][0]["videos"]["large"]["url"]
            filepath = TEMP_DIR / f"{scene_id}_pixabay.mp4"
            vid_data = requests.get(video_url, timeout=120, headers=HEADERS)
            if len(vid_data.content) > 5000:
                with open(filepath, "wb") as f:
                    f.write(vid_data.content)
                return str(filepath)
        else:
            print(f"      Pixabay returned no videos for '{query}'")
    except Exception as e:
        print(f"      Pixabay exception: {e}")
    return None


def fetch_asset_for_scene(scene: dict) -> str:
    """Routes the scene to the correct free API based on the LLM's instruction."""
    scene_id = scene.get("scene_id", "SCENE_000")
    visual_type = scene.get("visual_type", "AI_IMAGE")
    query = scene.get("prompt_or_query", "abstract background")
    source = scene.get("source", "Pollinations")

    print(f"      DEBUG: {scene_id} | type={visual_type} | source={source} | query='{query[:60]}'")

    result = None

    if source == "Pexels":
        result = fetch_pexels_video(query, scene_id)
    elif source == "Pixabay":
        result = fetch_pixabay_video(query, scene_id)
    elif source == "Library":
        library_dir = Path("assets/ai_video_loops")
        if library_dir.exists() and list(library_dir.glob("*.mp4")):
            result = str(random.choice(list(library_dir.glob("*.mp4"))))
    elif source == "Pollinations" or visual_type == "AI_IMAGE":
        result = fetch_pollinations_image(query, scene_id)
    else:
        result = fetch_pollinations_image(query, scene_id)

    # FALLBACK: If everything failed, try Pollinations with the query
    if not result:
        print(f"      FALLBACK: Trying Pollinations for {scene_id}")
        result = fetch_pollinations_image(query, scene_id)

    if result:
        print(f"      ✓ Downloaded: {result}")
    else:
        print(f"      ✗ FAILED for {scene_id}")

    return result