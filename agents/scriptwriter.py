"""Universal scriptwriter with key rotation and JSON timeline output."""
from __future__ import annotations
import json, os, urllib.parse, urllib.request
from typing import Any
from config1 import (
    GEMINI_API_URL, GROQ_API_URL, GROQ_MODELS, GEMINI_MODELS,
    get_groq_keys, get_gemini_keys
)


def _call_groq(prompt: str) -> dict | None:
    keys = get_groq_keys()
    if not keys:
        print("   No Groq keys found")
        return None
    for key in keys:
        for model in GROQ_MODELS:
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "response_format": {"type": "json_object"}
            }
            try:
                req = urllib.request.Request(
                    GROQ_API_URL,
                    data=json.dumps(body).encode(),
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=90) as response:
                    data = json.loads(response.read().decode())
                print(f"   Groq OK: {model} with key ...{key[-6:]}")
                return json.loads(data["choices"][0]["message"]["content"])
            except Exception as e:
                print(f"   Groq {model} key ...{key[-6:]} failed: {str(e)[:80]}")
                continue
    return None


def _call_gemini(prompt: str) -> dict | None:
    keys = get_gemini_keys()
    if not keys:
        print("   No Gemini keys found")
        return None
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"}
    }
    for key in keys:
        for model in GEMINI_MODELS:
            try:
                url = GEMINI_API_URL.format(model=model, key=urllib.parse.quote(key, safe=""))
                request = urllib.request.Request(
                    url, data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"}, method="POST"
                )
                with urllib.request.urlopen(request, timeout=90) as response:
                    data = json.loads(response.read().decode())
                print(f"   Gemini OK: {model} with key ...{key[-6:]}")
                return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
            except Exception as e:
                print(f"   Gemini {model} key ...{key[-6:]} failed: {str(e)[:80]}")
                continue
    return None


def _fallback(brief: dict, minutes: int) -> dict:
    topic = str(brief.get("topic", "an interesting topic"))
    return {
        "topic": topic, "title": topic,
        "full_script": f"Every story begins with a question: what is really happening with {topic}?",
        "description": f"A documentary about {topic}.", "tags": [topic],
        "timeline": [{
            "scene_id": "SCENE_001", "start_time": "00:00", "end_time": "00:10",
            "narration": f"Every story begins with a question: what is really happening with {topic}?",
            "visual_type": "AI_IMAGE", "prompt_or_query": f"documentary illustration of {topic}",
            "source": "Pollinations", "loop_behavior": None, "motion": "zoom_in"
        }]
    }


def write_script(brief: dict, minutes: int = 10) -> dict:
    minutes = max(1, int(minutes))
    topic = str(brief.get("topic", "an interesting topic"))
    target_words = minutes * 125

    prompt = f"""You are the lead documentary scriptwriter for a professional YouTube channel.
You have received a research dossier. Do not invent facts.

TOPIC: {topic}
TARGET LENGTH: {minutes} minutes, approximately {target_words} words.
RESEARCH DOSSIER:
{json.dumps(brief, ensure_ascii=False)}

Write the complete narration and break it into a timeline for video production.
You MUST output ONLY valid JSON with this exact structure:
{{
  "topic": "{topic}",
  "title": "SEO Optimized Title",
  "full_script": "The complete word-for-word narration.",
  "description": "YouTube description",
  "tags": ["tag1", "tag2"],
  "timeline": [
    {{
      "scene_id": "SCENE_001",
      "start_time": "00:00",
      "end_time": "00:08",
      "narration": "Exact words spoken during this scene",
      "visual_type": "STOCK_VIDEO",
      "prompt_or_query": "galaxy rotating space",
      "source": "Pexels",
      "loop_behavior": null,
      "motion": "none"
    }}
  ]
}}

RULES:
1. Every scene must have precise MM:SS start and end times.
2. visual_type MUST be one of: STOCK_VIDEO, AI_IMAGE, AI_VIDEO_LOOP, MOTION_GRAPHIC.
3. If STOCK_VIDEO: source is "Pexels" or "Pixabay", prompt_or_query is search term.
4. If AI_IMAGE: source is "Cloudflare", prompt_or_query is a detailed image generation prompt.
5. If AI_VIDEO_LOOP: source is "Library".
6. motion is REQUIRED for AI_IMAGE and MOTION_GRAPHIC scenes.
   - Alternate between "zoom_in" and "zoom_out" for variety.
   - Use "none" ONLY for STOCK_VIDEO and AI_VIDEO_LOOP scenes (motion is ignored for those).
7. Timeline MUST cover the ENTIRE script from 00:00 to end.
8. Create at least 6-8 scenes for a 2-minute video.
"""

    result = _call_gemini(prompt) or _call_groq(prompt)
    if not isinstance(result, dict) or "timeline" not in result:
        print("   ALL LLMs failed, using fallback.")
        return _fallback(brief, minutes)

    result["topic"] = topic
    return result


create_script = write_script
