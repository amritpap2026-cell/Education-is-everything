"""Complete API configuration with case-insensitive key lookup."""
from __future__ import annotations
import os


# ==================== LLM ENDPOINTS ====================
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# ==================== GROQ MODELS ====================
GROQ_MODELS = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
)

# ==================== GEMINI MODELS ====================
GEMINI_MODELS = (
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)

# ==================== HUGGING FACE ====================
HF_API_URL = "https://router.huggingface.co/hf-inference/models/{model}"
HF_VIDEO_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"

# ==================== CLOUDFLARE WORKERS AI ====================
CF_API_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
CF_IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
CF_IMAGE_MODEL_FAST = "@cf/stabilityai/stable-diffusion-xl-base-1.0"

# ==================== STOCK/IMAGE APIs ====================
PEXELS_API_URL = "https://api.pexels.com/videos/search"
PIXABAY_API_URL = "https://pixabay.com/api/videos/"
COVERR_API_URL = "https://api.coverr.co/videos"
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"
POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt/{prompt}"

# ==================== TTS VOICES ====================
EDGE_TTS_VOICES = {
    "English": "en-US-AndrewMultilingualNeural",
    "Hindi": "hi-IN-MadhurNeural",
    "Nepali": "ne-NP-HemkalaNeural",
}


# ==================== HELPER ====================
def _env(*names):
    for name in names:
        val = os.getenv(name, "").strip()
        if val:
            return val
    return ""


# ==================== KEY LOOKUP ====================
def get_groq_keys():
    keys = []
    for name in ["GROQ_API_KEY", "groq_api_key", "GROQ_API_KEY_1", "GROQ_API_KEY1", "groq_api_key_1", "groq_api_key1", "GROQ_API_KEY_2", "GROQ_API_KEY2"]:
        val = os.getenv(name, "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def get_gemini_keys():
    keys = []
    for name in ["GEMINI_API_KEY", "gemini_api_key",
                 "GEMINI_API_KEY_1", "GEMINI_API_KEY1",
                 "GEMINI_API_KEY_2", "GEMINI_API_KEY2",
                 "GEMINI_API_KEY_3", "GEMINI_API_KEY3",
                 "GEMINI_API_KEY_4", "GEMINI_API_KEY4",
                 "GEMINI_API_KEY_5", "GEMINI_API_KEY5"]:
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


def get_cloudflare_config():
    return {
        "account_id": _env("CLOUDFLARE_ACCOUNT_ID", "cloudflare_account_id", "CF_ACCOUNT_ID"),
        "api_token": _env("CLOUDFLARE_API_TOKEN", "cloudflare_api_token", "CF_API_TOKEN"),
    }


def get_cloudinary_config():
    return {
        "cloud_name": _env("CLOUDINARY_CLOUD_NAME", "cloudinary_cloud_name"),
        "api_key": _env("CLOUDINARY_API_KEY", "cloudinary_api_key"),
        "api_secret": _env("CLOUDINARY_API_SECRET", "cloudinary_api_secret"),
    }


def candidates(role):
    return list(GEMINI_MODELS)


def check_all_keys():
    cf = get_cloudflare_config()
    return {
        "groq_keys": len(get_groq_keys()),
        "gemini_keys": len(get_gemini_keys()),
        "huggingface": bool(get_hf_key()),
        "cloudflare": bool(cf["account_id"] and cf["api_token"]),
        "pexels": bool(get_pexels_key()),
        "pixabay": bool(get_pixabay_key()),
        "coverr": bool(get_coverr_key()),
        "unsplash": bool(get_unsplash_key()),
        "pollinations": bool(get_pollinations_key()),
        "cloudinary": bool(get_cloudinary_config()["cloud_name"]),
    }