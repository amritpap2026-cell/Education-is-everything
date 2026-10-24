"""AI Video generation using fal.ai (MiniMax H3)."""
import os, requests, fal_client
from pathlib import Path

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def _get_fal_keys():
    keys = []
    for name in ["FAL_KEY", "FAL_KEY_1", "FAL_KEY_2", "FAL_KEY_3"]:
        val = os.getenv(name, "").strip()
        if val: keys.append(val)
    return keys

def fetch_ai_video(prompt: str, scene_id: str, duration: int = 5) -> str:
    keys = _get_fal_keys()
    if not keys:
        print("      ❌ No FAL_KEY found.")
        return None

    for key in keys:
        try:
            os.environ["FAL_KEY"] = key
            print(f"      Generating AI Video (Key ...{key[-4:]})...")
            
            result = fal_client.subscribe(
                "minimax/h3-max/text-to-video",
                arguments={
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": "16:9",
                    "resolution": "720p"
                },
            )
            
            if result and "video" in result and "url" in result["video"]:
                video_url = result["video"]["url"]
                filepath = TEMP_DIR / f"{scene_id}_aivideo.mp4"
                vid_data = requests.get(video_url, timeout=120)
                if len(vid_data.content) > 5000:
                    with open(filepath, "wb") as f:
                        f.write(vid_data.content)
                    print(f"      ✓ AI Video saved: {filepath}")
                    return str(filepath)
        except Exception as e:
            print(f"      ❌ fal.ai error: {str(e)[:100]}")
            continue
    return None
