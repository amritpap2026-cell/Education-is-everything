"""Universal scriptwriter with key rotation and JSON timeline output."""
from __future__ import annotations
import json, os, urllib.parse, urllib.request, urllib.error
from typing import Any
from config1 import (
    GEMINI_API_URL, GROQ_API_URL, GROQ_MODELS, GEMINI_MODELS,
    get_groq_keys, get_gemini_keys
)

def _call_groq(prompt: str) -> dict | None:
    keys = get_groq_keys()
    if not keys: return None
    for key in keys:
        for model in GROQ_MODELS:
            body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7, "response_format": {"type": "json_object"}}
            try:
                req = urllib.request.Request(GROQ_API_URL, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "AutoVideoPipeline/1.0"}, method="POST")
                with urllib.request.urlopen(req, timeout=90) as response:
                    data = json.loads(response.read().decode())
                print(f"   Groq OK: {model} with key ...{key[-6:]}")
                return json.loads(data["choices"][0]["message"]["content"])
            except Exception as e:
                print(f"   Groq {model} failed: {str(e)[:80]}")
    return None

def _call_gemini(prompt: str) -> dict | None:
    keys = get_gemini_keys()
    if not keys: return None
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"}}
    for key in keys:
        for model in GEMINI_MODELS:
            try:
                url = GEMINI_API_URL.format(model=model, key=urllib.parse.quote(key, safe=""))
                request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "AutoVideoPipeline/1.0"}, method="POST")
                with urllib.request.urlopen(request, timeout=90) as response:
                    data = json.loads(response.read().decode())
                print(f"   Gemini OK: {model} with key ...{key[-6:]}")
                return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
            except Exception as e:
                print(f"   Gemini {model} failed: {str(e)[:80]}")
    return None

def _fallback(brief: dict, minutes: int) -> dict:
    return {"topic": brief.get("topic", "topic"), "title": brief.get("topic", "topic"), "full_script": "Fallback", "description": "Fallback", "tags": [], "thumbnail_prompt": "abstract", "thumbnail_header": "WAIT WHAT?", "thumbnail_subheader": "You won't believe this...", "timeline": [{"scene_id": "SCENE_001", "start_time": "00:00", "end_time": "00:10", "narration": "Fallback", "visual_type": "AI_IMAGE", "prompt_or_query": "abstract", "source": "Cloudflare", "loop_behavior": None, "motion": "zoom_in"}]}

def write_script(brief: dict, minutes: int = 5, language: str = "English") -> dict:
    minutes = max(1, int(minutes))
    topic = str(brief.get("topic", "an interesting topic"))
    target_words = minutes * 125

    prompt = f"""You are the lead documentary scriptwriter for a professional YouTube channel.
TOPIC: {topic}
LANGUAGE: {language}
TARGET LENGTH: {minutes} minutes, approximately {target_words} words.
RESEARCH DOSSIER:
{json.dumps(brief, ensure_ascii=False)}

Write the complete narration and break it into a timeline for video production.
You MUST output ONLY valid JSON with this exact structure:
{{
  "topic": "{topic}",
  "title": "SEO Optimized Title in {language}",
  "full_script": "The complete word-for-word narration in {language}.",
  "description": "YouTube description in {language}",
  "tags": ["tag1", "tag2"],
  "thumbnail_prompt": "A highly detailed, cinematic, dramatic image prompt in English describing the main subject (e.g., 'A glowing black hole in deep space')",
  "thumbnail_header": "SHORT PUNCHY QUESTION IN {language}? (2-4 words MAX)",
  "thumbnail_subheader": "A short, clickbaity, curiosity-inducing statement in {language} (e.g., 'You will die in a minute')",
  "timeline": [
    {{
      "scene_id": "SCENE_001", "start_time": "00:00", "end_time": "00:06", "narration": "Exact words spoken during this scene in {language}", "visual_type": "AI_IMAGE", "prompt_or_query": "highly detailed cinematic image of...", "source": "Cloudflare", "loop_behavior": null, "motion": "zoom_in"
    }}
  ]
}}

CRITICAL RULES:
1. The full_script, title, description, and all narration MUST be written entirely in {language}.
2. Create EXACTLY 50 scenes (roughly 6 seconds per scene).
3. Use "visual_type": "AI_IMAGE" for EXACTLY 32 scenes.
4. For ALL 32 AI_IMAGE scenes, you MUST alternate "motion": "zoom_in" and "motion": "zoom_out".
5. Use "visual_type": "STOCK_VIDEO" for the remaining 18 scenes. Set source to "Pexels" or "Pixabay", and "motion": "none".
6. visual_type MUST be one of: STOCK_VIDEO, AI_IMAGE.
7. "thumbnail_header" MUST be ALL CAPS, 2-4 words, and end with a question mark.
8. "thumbnail_subheader" MUST be a short, enticing statement.
"""

    result = _call_gemini(prompt) or _call_groq(prompt)
    if not isinstance(result, dict) or "timeline" not in result: 
        print("   ALL LLMs failed, using fallback.")
        return _fallback(brief, minutes)
    result["topic"] = topic
    return result
