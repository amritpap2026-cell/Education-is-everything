"""Voiceover generation: Gemini TTS primary, gTTS fallback, ASS subtitles."""
import asyncio, base64, json, os, shutil, subprocess, urllib.request
from pathlib import Path
from gtts import gTTS
import stable_whisper
from modules.subtitles import build_ass

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

LANG_CODES = {"English": "en", "Hindi": "hi", "Nepali": "ne"}
GEMINI_VOICES = {"English": "Kore", "Hindi": "Kore", "Nepali": "Kore"}

def _chunk_text(text, max_chars=4000):
    chunks, current = [], ""
    for sentence in text.replace("\n", " ").split(". "):
        if len(current) + len(sentence) < max_chars: current += sentence + ". "
        else:
            if current.strip(): chunks.append(current.strip())
            current = sentence + ". "
    if current.strip(): chunks.append(current.strip())
    return chunks

def _get_audio_duration(audio_path):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception: return 0.0

def _validate_audio_duration(audio_path, text):
    duration = _get_audio_duration(audio_path)
    if duration <= 0: return False
    word_count = len(text.split())
    expected_duration = word_count / 2.5
    if duration < (expected_duration * 0.6):
        print(f"      ⚠️ WARNING: Audio is only {duration:.2f}s, but expected ~{expected_duration:.2f}s.")
        return False
    return True

def _gemini_tts(text, language, output_path):
    from config1 import get_gemini_keys
    keys = get_gemini_keys()
    if not keys: return False
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    voice = GEMINI_VOICES.get(language, "Kore")
    chunks = _chunk_text(text)
    print(f"      Gemini TTS: {len(chunks)} chunk(s), voice={voice}")

    chunk_files = []
    for i, chunk in enumerate(chunks):
        body = {"model": "gemini-3.8-flash-tts", "input": [{"type": "user_input", "content": [{"type": "text", "text": chunk}]}], "response_format": {"type": "audio", "mime_type": "audio/wav"}, "generation_config": {"speech_config": [{"voice": voice}]}}
        success = False
        for key in keys:
            try:
                req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"x-goog-api-key": key, "Content-Type": "application/json", "User-Agent": "AutoVideoPipeline/1.0"}, method="POST")
                with urllib.request.urlopen(req, timeout=180) as r:
                    data = json.loads(r.read().decode())
                audio_b64 = None
                for step in data.get("steps", []):
                    if step.get("type") == "model_output":
                        for content in step.get("content", []):
                            if content.get("type") == "audio" and content.get("data"): audio_b64 = content["data"]
                if audio_b64:
                    wav_path = TEMP_DIR / f"gemini_chunk_{i:03d}.wav"
                    with open(wav_path, "wb") as f: f.write(base64.b64decode(audio_b64))
                    mp3_path = TEMP_DIR / f"gemini_chunk_{i:03d}.mp3"
                    subprocess.run(f'ffmpeg -y -i "{wav_path}" -c:a libmp3lame -b:a 128k "{mp3_path}"', shell=True, capture_output=True)
                    if mp3_path.exists() and mp3_path.stat().st_size > 1000:
                        chunk_files.append(str(mp3_path))
                        success = True
                        break
            except Exception: pass
        if not success: return False

    if not chunk_files: return False
    if len(chunk_files) == 1: shutil.copy(chunk_files[0], output_path)
    else:
        concat_file = TEMP_DIR / "gemini_concat.txt"
        with open(concat_file, "w") as f:
            for cf in chunk_files: f.write(f"file '{os.path.abspath(cf)}'\n")
        subprocess.run(f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"', shell=True)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

def _gtts_tts(text, language, output_path):
    lang_code = LANG_CODES.get(language, "en")
    chunks = _chunk_text(text)
    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_path = TEMP_DIR / f"gtts_chunk_{i:03d}.mp3"
        try:
            gTTS(text=chunk, lang=lang_code, slow=False).save(str(chunk_path))
            chunk_files.append(str(chunk_path))
        except Exception: pass
    if not chunk_files: return False
    if len(chunk_files) == 1: shutil.copy(chunk_files[0], output_path)
    else:
        concat_file = TEMP_DIR / "gtts_concat.txt"
        with open(concat_file, "w") as f:
            for cf in chunk_files: f.write(f"file '{os.path.abspath(cf)}'\n")
        subprocess.run(f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" -c copy "{output_path}"', shell=True)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000

def _estimate_timestamps(text):
    words = text.split()
    wps = 2.5
    duration = 1.0 / wps
    timestamps = []
    current_time = 0.5
    for word in words:
        timestamps.append({'word': word, 'start': current_time, 'end': current_time + duration})
        current_time += duration
    return timestamps

def generate_voiceover(full_script, language="English"):
    audio_path = TEMP_DIR / "voiceover.mp3"
    ass_path = TEMP_DIR / "subtitles.ass"

    print(f"   Trying Gemini TTS (language: {language})...")
    ok = _gemini_tts(full_script, language, str(audio_path))
    if ok:
        if not _validate_audio_duration(str(audio_path), full_script):
            print("   Gemini TTS audio seems truncated. Falling back to gTTS...")
            ok = _gtts_tts(full_script, language, str(audio_path))
    
    if not ok:
        print(f"   Gemini TTS failed. Falling back to gTTS...")
        ok = _gtts_tts(full_script, language, str(audio_path))
    
    if not ok: raise RuntimeError("All TTS engines failed.")

    print(f"   Aligning audio and text for perfect captions...")
    try:
        # UPGRADED TO 'small' MODEL for Hindi/Nepali accuracy
        model = stable_whisper.load_model('small')
        result = model.align(str(audio_path), full_script, language=LANG_CODES.get(language, "en"))
        
        word_timestamps = []
        for segment in result.segments:
            for word in segment.words:
                word_timestamps.append({
                    'word': word.word,
                    'start': word.start,
                    'end': word.end
                })
        print(f"   ✅ Successfully aligned {len(word_timestamps)} words.")
    except Exception as e:
        print(f"   ⚠️ Alignment failed ({str(e)[:50]}). Using estimated timestamps as fallback.")
        word_timestamps = _estimate_timestamps(full_script)

    print(f"   Building ASS subtitles...")
    build_ass(full_script, str(ass_path), word_timestamps)
    
    return str(audio_path), str(ass_path)
