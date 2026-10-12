from dotenv import load_dotenv
load_dotenv()
import json, urllib.request, urllib.error, os
from config1 import GROQ_API_URL, GROQ_MODELS, get_groq_keys

key = get_groq_keys()[0]
print(f"Key preview: {key[:8]}...{key[-6:]} (length: {len(key)})")
print(f"Model: {GROQ_MODELS[0]}")
print()

body = {
    "model": GROQ_MODELS[0],
    "messages": [{"role": "user", "content": "Say hi in 3 words"}],
    "temperature": 0.7
}

req = urllib.request.Request(
    GROQ_API_URL,
    data=json.dumps(body).encode(),
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "AutoVideoPipeline/1.0",
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("STATUS:", r.status)
        print("RESPONSE:", r.read().decode()[:500])
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print("REASON:", e.reason)
    print("BODY:", e.read().decode()[:1000])
except Exception as e:
    print("OTHER ERROR:", type(e).__name__, str(e))
