"""Daily scheduler: processes next topic from queue, rotates languages."""
import json
import sys
from datetime import datetime
from pathlib import Path
import subprocess
from dotenv import load_dotenv

load_dotenv()

QUEUE_FILE = Path("topics_queue.json")
HISTORY_FILE = Path("output/upload_history.json")

def load_queue():
    if not QUEUE_FILE.exists():
        print(f"No queue file at {QUEUE_FILE}")
        sys.exit(1)
    return json.loads(QUEUE_FILE.read_text())

def save_queue(queue):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))

def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []

def save_history(history):
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))

def process_next():
    queue = load_queue()
    
    # Find first topic not yet done
    next_item = None
    for item in queue:
        if not item.get("done"):
            next_item = item
            break

    if not next_item:
        print("All topics in queue are done!")
        return

    topic = next_item["topic"]
    minutes = next_item.get("minutes", 3)
    language = next_item.get("language", "English")

    print(f"\n{'=' * 60}")
    print(f"  Processing: {topic}")
    print(f"  Language: {language}")
    print(f"  Duration: {minutes} min")
    print(f"{'=' * 60}\n")

    # Build command
    cmd = [
        sys.executable, "main.py",
        "--topic", topic,
        "--minutes", str(minutes),
        "--language", language,
        "--privacy", "public",
    ]

    result = subprocess.run(cmd)

    # Update history
    history = load_history()
    history.append({
        "topic": topic,
        "language": language,
        "minutes": minutes,
        "processed_at": datetime.now().isoformat(),
        "exit_code": result.returncode,
    })
    save_history(history)

    if result.returncode == 0:
        next_item["done"] = True
        next_item["done_at"] = datetime.now().isoformat()
        save_queue(queue)
        print(f"\nSUCCESS: {topic} uploaded and marked done.")
    else:
        print(f"\nFAILED: {topic} (exit {result.returncode})")

if __name__ == "__main__":
    process_next()
