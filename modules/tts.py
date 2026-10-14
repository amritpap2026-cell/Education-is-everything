"""Voiceover generation: Gemini TTS primary, gTTS fallback."""
import asyncio
import base64
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from gtts import gTTS

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Language codes for gTTS
LANG_CODES = {
    "English": "en",
    "Hindi": "hi",
    "Nepali": "ne",
}

# Gemini TTS voices (prebuilt studio voices)
GEMINI_VOICES = {
    "English": "Kore",
    "Hindi": "Kore",
    "Nepali": "Kore",
}


# ==================== GEMINI TTS ====================
def _gemini_tts(text: str, language: str, output_path: str) -> bool:
    """Generate speech using Gemini TTS. Returns True on success."""
    from config1 import get_gemini_keys

    keys = get_gemini_keys()
    if not keys:
        print("      Gemini TTS: no API keys found")
        return False

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    voice = GEMINI_VOICES.get(language, "Kore")

    # Gemini TTS has a 8192 token input limit; split if needed
    max_chars = 4000
    chunks = []
    current = ""
    for sentence in text.replace("\n", " ").split(". "):
        if len(current) + len(sentence) < max_chars:
            current += sentence + ". "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + ". "
    if current.strip():
        chunks.append(current.strip())

    print(f"      Gemini TTS: {len(chunks)} chunk(s), voice={voice}")

    chunk_files = []
    for i, chunk in enumerate(chunks):
        body = {
            "model": "gemini-3.8-flash-tts",
            "input": [{
                "type": "user_input",
                "content": [{"type": "text", "text": chunk}]
            }],
            "response_format": {"type": "audio", "mime_type": "audio/wav"},
            "generation_config": {
                "speech_config": [{"voice": voice}]
            },
        }

        success = False
        for key in keys:
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode(),
                    headers={
                        "x-goog-api-key": key,
                        "Content-Type": "application/json",
                        "User-Agent": "AutoVideoPipeline/1.0",
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode())

                # Extract base64 audio from steps[].content[].data
                audio_b64 = None
                for step in data.get("steps", []):
                    if step.get("type") == "model_output":
                        for content in step.get("content", []):
                            if content.get("type") == "audio" and content.get("data"):
                                audio_b64 = content["data"]

                if audio_b64:
                    wav_path = TEMP_DIR / f"gemini_chunk_{i:03d}.wav"
                    with open(wav_path, "wb") as f:
                        f.write(base64.b64decode(audio_b64))

                    # Convert WAV to MP3 via FFmpeg
                    mp3_path = TEMP_DIR / f"gemini_chunk_{i:03d}.mp3"
                    conv = subprocess.run(
                        f'ffmpeg -y -i "{wav_path}" -c:a libmp3lame -b:a 128k "{mp3_path}"',
                        shell=True, capture_output=True, text=True
                    )
                    if conv.returncode == 0 and mp3_path.exists() and mp3_path.stat().st_size > 1000:
                        chunk_files.append(str(mp3_path))
                        print(f"      Gemini TTS chunk {i+1}/{len(chunks)} OK ({mp3_path.stat().st_size} bytes)")
                        success = True
                        break  # this key worked
                    else:
                        print(f"      Gemini TTS: FFmpeg conversion failed")
            except Exception as e:
                print(f"      Gemini TTS key ...{key[-6:]} failed: {str(e)[:100]}")
                continue

        if not success:
            # Clean up partial chunks
            for cf in chunk_files:
                try:
                    os.remove(cf)
                except Exception:
                    pass
            return False

    if not chunk_files:
        return False

    # Concatenate MP3 chunks
    if len(chunk_files) == 1:
        import shutil
        shutil.copy(chunk_files[0], output_path)
    else:
        concat_file = TEMP_DIR / "gemini_concat.txt"
        with open(concat_file, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{os.path.abspath(cf)}'\n")
        cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c:a libmp3lame "{output_path}"'
            subprocess.run(cmd, shell=True, check=True)

    # Clean up
    for cf in chunk_files:
        try:
            os.remove(cf)
        except Exception:
            pass

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000


# ==================== gTTS FALLBACK ====================
def _gtts_tts(text: str, language: str, output_path: str) -> bool:
    """Fallback gTTS engine."""
    lang_code = LANG_CODES.get(language, "en")
    print(f"      gTTS: language={lang_code}")

    max_chars = 4000
    chunks = []
    current = ""
    for sentence in text.replace("\n", " ").split(". "):
        if len(current) + len(sentence) < max_chars:
            current += sentence + ". "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + ". "
    if current.strip():
        chunks.append(current.strip())

    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_path = TEMP_DIR / f"gtts_chunk_{i:03d}.mp3"
        try:
            tts = gTTS(text=chunk, lang=lang_code, slow=False)
            tts.save(str(chunk_path))
            chunk_files.append(str(chunk_path))
        except Exception as e:
            print(f"      gTTS chunk {i+1} failed: {e}")
            continue

    if not chunk_files:
        return False

    if len(chunk_files) == 1:
        import shutil
        shutil.copy(chunk_files[0], output_path)
    else:
        concat_file = TEMP_DIR / "gtts_concat.txt"
        with open(concat_file, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{os.path.abspath(cf)}'\n")
        cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"'
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c:a libmp3lame "{output_path}"'
            subprocess.run(cmd, shell=True, check=True)

    for cf in chunk_files:
        try:
            os.remove(cf)
        except Exception:
            pass

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000


# ==================== SRT GENERATION ====================
def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(text: str, srt_path: str):
    """Generate estimated SRT from text."""
    lines = [ln.strip() for ln in text.split(". ") if ln.strip()]
    words_per_second = 2.5
    with open(srt_path, "w", encoding="utf-8") as f:
        current_time = 0.0
        for i, line in enumerate(lines, 1):
            duration = max(1.5, len(line.split()) / words_per_second)
            start = _format_time(current_time)
            end = _format_time(current_time + duration)
            f.write(f"{i}\n{start} --> {end}\n{line}\n\n")
            current_time += duration


# ==================== MAIN ====================
def generate_voiceover(full_script: str, language: str = "English") -> tuple[str, str]:
    """Try Gemini TTS first, fall back to gTTS."""
    audio_path = TEMP_DIR / "voiceover.mp3"
    srt_path = TEMP_DIR / "subtitles.srt"

    # Try Gemini TTS first
    print(f"   Trying Gemini TTS (language: {language})...")
    if _gemini_tts(full_script, language, str(audio_path)):
        print(f"   Gemini TTS succeeded")
        _write_srt(full_script, str(srt_path))
        return str(audio_path), str(srt_path)

    # Fall back to gTTS
    print(f"   Gemini TTS failed, falling back to gTTS...")
    if _gtts_tts(full_script, language, str(audio_path)):
        print(f"   gTTS succeeded")
        _write_srt(full_script, str(srt_path))
        return str(audio_path), str(srt_path)

    raise RuntimeError("All TTS engines failed.")