"""Voiceover generation: Gemini TTS primary, gTTS fallback, ASS subtitles."""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from gtts import gTTS

from modules.subtitles import build_ass

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

LANG_CODES = {"English": "en", "Hindi": "hi", "Nepali": "ne"}
GEMINI_VOICES = {"English": "Kore", "Hindi": "Kore", "Nepali": "Kore"}


def _chunk_text(text, max_chars=4000):
    """Split long text into chunks for TTS."""
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
    return chunks


def _gemini_tts(text, language, output_path):
    """Generate audio using Gemini TTS. Returns True on success."""
    from config1 import get_gemini_keys

    keys = get_gemini_keys()
    if not keys:
        print("      Gemini TTS: no API keys found")
        return False

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    voice = GEMINI_VOICES.get(language, "Kore")
    chunks = _chunk_text(text)
    print(f"      Gemini TTS: {len(chunks)} chunk(s), voice={voice}")

    chunk_files = []
    for i, chunk in enumerate(chunks):
        body = {
            "model": "gemini-3.8-flash-tts",
            "input": [
                {
                    "type": "user_input",
                    "content": [{"type": "text", "text": chunk}],
                }
            ],
            "response_format": {"type": "audio", "mime_type": "audio/wav"},
            "generation_config": {"speech_config": [{"voice": voice}]},
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
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode())

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

                    mp3_path = TEMP_DIR / f"gemini_chunk_{i:03d}.mp3"
                    subprocess.run(
                        f'ffmpeg -y -i "{wav_path}" -c:a libmp3lame -b:a 128k "{mp3_path}"',
                        shell=True,
                        capture_output=True,
                    )

                    if mp3_path.exists() and mp3_path.stat().st_size > 1000:
                        chunk_files.append(str(mp3_path))
                        print(f"      Gemini TTS chunk {i+1}/{len(chunks)} OK ({mp3_path.stat().st_size} bytes)")
                        success = True
                        break
                    else:
                        print(f"      Gemini TTS: FFmpeg conversion failed for chunk {i+1}")
            except Exception as e:
                print(f"      Gemini TTS key ...{key[-6:]} failed: {str(e)[:100]}")
                continue

        if not success:
            for cf in chunk_files:
                try:
                    os.remove(cf)
                except Exception:
                    pass
            return False

    if not chunk_files:
        return False

    # Concatenate all chunk MP3s
    if len(chunk_files) == 1:
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

    for cf in chunk_files:
        try:
            os.remove(cf)
        except Exception:
            pass

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000


def _gtts_tts(text, language, output_path):
    """Fallback gTTS engine. Returns True on success."""
    lang_code = LANG_CODES.get(language, "en")
    print(f"      gTTS: language={lang_code}")

    chunks = _chunk_text(text)
    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_path = TEMP_DIR / f"gtts_chunk_{i:03d}.mp3"
        try:
            tts = gTTS(text=chunk, lang=lang_code, slow=False)
            tts.save(str(chunk_path))
            chunk_files.append(str(chunk_path))
            print(f"      gTTS chunk {i+1}/{len(chunks)} OK")
        except Exception as e:
            print(f"      gTTS chunk {i+1} failed: {e}")
            continue

    if not chunk_files:
        return False

    if len(chunk_files) == 1:
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


def generate_voiceover(full_script, language="English"):
    """Generate voiceover MP3 + ASS subtitle file. Returns (audio_path, ass_path)."""
    audio_path = TEMP_DIR / "voiceover.mp3"
    ass_path = TEMP_DIR / "subtitles.ass"

    # Try Gemini TTS first
    print(f"   Trying Gemini TTS (language: {language})...")
    ok = False
    if _gemini_tts(full_script, language, str(audio_path)):
        print(f"   Gemini TTS succeeded")
        ok = True
    else:
        print(f"   Gemini TTS failed, falling back to gTTS...")
        if _gtts_tts(full_script, language, str(audio_path)):
            print(f"   gTTS succeeded")
            ok = True

    if not ok:
        raise RuntimeError("All TTS engines failed.")

    # Generate ASS subtitles with word highlighting
    print(f"   Building ASS subtitles...")
    build_ass(full_script, str(ass_path))
    print(f"   Subtitles: {ass_path}")

    return str(audio_path), str(ass_path)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    a, s = generate_voiceover("Hello world. This is a test of the subtitle system.", "English")
    print("Audio:", a)
    print("Subtitles:", s)