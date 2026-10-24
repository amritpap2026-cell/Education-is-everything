"""Automatically generates new topics when the queue is running low."""
import json, os, urllib.parse, urllib.request
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from config1 import GEMINI_API_URL, GEMINI_MODELS, get_gemini_keys

QUEUE_FILE = Path("topics_queue.json")
MIN_REMAINING = 10
TOPICS_TO_GENERATE = 60

def generate_new_topics():
    existing_queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8")) if QUEUE_FILE.exists() else []
    remaining = sum(1 for item in existing_queue if not item.get("done", False))
    print(f"Current queue status: {remaining} topics remaining.")
    if remaining >= MIN_REMAINING:
        print("Queue is healthy."); return
    print(f"Queue is low! Generating {TOPICS_TO_GENERATE} new topics...")
    existing_topics = [item["topic"] for item in existing_queue]
    existing_topics_str = "\n".join(existing_topics[-100:])
    prompt = f"""Generate exactly {TOPICS_TO_GENERATE} highly engaging, unique topics for 5-minute videos.
Rotate: English, Hindi, Nepali. 
DO NOT use any of these existing topics:
{existing_topics_str}
Return ONLY a valid JSON array: [ {{"topic": "...", "minutes": 5, "language": "English", "done": false}}, ... ]"""
    keys = get_gemini_keys()
    if not keys: return
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.8, "responseMimeType": "application/json"}}
    for key in keys:
        for model in GEMINI_MODELS:
            try:
                url = GEMINI_API_URL.format(model=model, key=urllib.parse.quote(key, safe=""))
                req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "QueueGen/1.0"}, method="POST")
                with urllib.request.urlopen(req, timeout=90) as response:
                    data = json.loads(response.read().decode())
                new_topics = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                if isinstance(new_topics, list) and len(new_topics) > 0:
                    print(f"Successfully generated {len(new_topics)} new topics!")
                    existing_queue.extend(new_topics)
                    QUEUE_FILE.write_text(json.dumps(existing_queue, ensure_ascii=False, indent=2), encoding="utf-8")
                    return
            except Exception: continue
if __name__ == "__main__": generate_new_topics()
