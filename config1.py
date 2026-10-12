"""Complete API configuration."""
from __future__ import annotations
import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

GROQ_MODELS = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
)

GEMINI_MODELS = (
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)

EDGE_TTS_VOICES = {
    "English": "en-US-AndrewMultilingualNeural",
    "Hindi": "hi-IN-MadhurNeural",
    "Nepali": "ne-NP-HemkalaNeural",
}


def _env(*names):
    for name in names:
        val = os.getenv(name, "").strip()
        if val:
            return val
    return ""


def get_groq_keys():
    keys = []
    for name in ["GROQ_API_KEY", "groq_api_key", "GROQ_API_KEY_1", "GROQ_API_KEY_2"]:
        val = os.getenv(name, "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def get_gemini_keys():
    keys = []
    for name in ["GEMINI_API_KEY", "gemini_api_key",
                 "GEMINI_API_KEY_1", "GEMINI_API_KEY_2",
                 "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]:
        val = os.getenv(name, "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def get_hf_key():
    return _env("HF_TOKEN", "HF_Token", "hf_token", "HF_token",
                "HUGGINGFACE_API_KEY", "HUGGINGFACE_TOKEN")


def get_pexels_key():
    return _env("PEXELS_API_KEY", "pexels_api_key")


def get_pixabay_key():
    return _env("PIXABAY_API_KEY", "pixabay_api_key")


def get_coverr_key():
    return _env("COVERR_API_KEY", "coverr_api_key")


def get_unsplash_key():
    return _env("UNSPLASH_ACCESS_KEY", "unsplash_access_key")


def get_pollinations_key():
    return _env("POLLINATIONS_API_KEY", "pollinations_api_key")


def get_cloudinary_config():
    return {
        "cloud_name": _env("CLOUDINARY_CLOUD_NAME", "cloudinary_cloud_name"),
        "api_key": _env("CLOUDINARY_API_KEY", "cloudinary_api_key"),
        "api_secret": _env("CLOUDINARY_API_SECRET", "cloudinary_api_secret"),
    }


def candidates(role):
    return list(GEMINI_MODELS)


def check_all_keys():
    return {
        "groq_keys": len(get_groq_keys()),
        "gemini_keys": len(get_gemini_keys()),
        "huggingface": bool(get_hf_key()),
        "pexels": bool(get_pexels_key()),
        "pixabay": bool(get_pixabay_key()),
        "coverr": bool(get_coverr_key()),
        "unsplash": bool(get_unsplash_key()),
        "pollinations": bool(get_pollinations_key()),
        "cloudinary": bool(get_cloudinary_config()["cloud_name"]),
    }