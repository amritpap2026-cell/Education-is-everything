"""Daily scheduler: processes next topic from queue."""
import json, sys
from datetime import datetime
from pathlib import Path
import subprocess
from dotenv import load_dotenv

load_dotenv()
QUEUE_FILE = Path("topics_queue.json")

def load_queue():
    if not QUEUE_FILE.exists(): return []
    return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))

def save_queue(queue):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")

def process_next():
    queue = load_queue()
    next_item = None
    for item in queue:
        if not item.get("done"):
            next_item = item
            break
    if not next_item:
        print("All topics in queue are done!")
        return
    topic = next_item["topic"]
    minutes = next_item.get("minutes", 5)
    language = next_item.get("language", "English")
    print(f"\n{'=' * 60}\n  Processing: {topic}\n  Language: {language}\n  Duration: {minutes} min\n{'=' * 60}\n")
    cmd = [sys.executable, "main.py", "--topic", topic, "--minutes", str(minutes), "--language", language, "--privacy", "public"]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        next_item["done"] = True
        next_item["done_at"] = datetime.now().isoformat()
        save_queue(queue)
        print(f"\nSUCCESS: {topic} uploaded and marked done.")
    else:
        print(f"\nFAILED: {topic} (exit {result.returncode})")

if __name__ == "__main__": process_next()
