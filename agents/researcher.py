"""Universal research agent (minimal fallback version)."""
import json, os, urllib.parse, urllib.request
from dataclasses import asdict, dataclass
from typing import Any
from config1 import GEMINI_API_URL, candidates

GEMINI_MODELS = candidates("research")


@dataclass
class ResearchDossier:
    topic: str
    language: str
    audience: str
    research_status: str
    current_search_signals: list
    key_claims: list
    verified_facts: list
    uncertainties: list
    important_people: list
    organizations: list
    statistics: list
    counterpoints: list
    timeline: list
    source_notes: list
    image_queries: list
    video_queries: list
    seo_keywords: list


def research(topic: str, language: str = "English", audience: str = "General public") -> dict[str, Any]:
    subject = topic.strip() or "a topic worth investigating"
    key = os.getenv("GEMINI_API_KEY")
    
    if key:
        prompt = f"""You are a Universal Research Agent. Research topic: {subject}
Output language: {language}, Audience: {audience}
Return ONLY JSON with arrays named: key_claims, verified_facts, uncertainties, important_people, organizations, statistics, counterpoints, timeline, source_notes, seo_keywords. Do not invent facts."""
        
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.25, "responseMimeType": "application/json"}}
        
        for model in GEMINI_MODELS:
            try:
                url = GEMINI_API_URL.format(model=model, key=urllib.parse.quote(key, safe=""))
                req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=45) as response:
                    data = json.loads(response.read().decode())
                result = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
                result.update({"topic": subject, "language": language, "audience": audience})
                return result
            except Exception:
                continue
    
    # Fallback
    return asdict(ResearchDossier(
        subject, language, audience, "Fallback mode", [],
        [f"Investigate {subject}"], [], [], [], [], [], [], [],
        ["Verify all claims before publishing"],
        [subject], [f"{subject} footage"], [subject]
    ))


create_brief = research