"""FFmpeg video assembly engine for the free automated pipeline."""
import subprocess, os
from pathlib import Path

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

def _seconds(time_str: str) -> int:
    try:
        parts = str(time_str).split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception: return 0

def _run_ffmpeg(cmd: str, scene_index: int = 0):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n!!! FFmpeg FAILED on scene {scene_index} !!!")
        print(f"    STDERR:\n{result.stderr[-1500:]}\n")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

def render_scene(scene: dict, asset_path: str, output_path: str, index: int):
    start_sec = _seconds(scene.get("start_time", "00:00"))
    end_sec = _seconds(scene.get("end_time", "00:05"))
    duration = max(1, end_sec - start_sec)
    visual_type = scene.get("visual_type", "AI_IMAGE")
    motion = scene.get("motion", "none") or "none"
    print(f"   Scene {index}: {duration}s | {visual_type} | motion={motion}")

    if not asset_path or not os.path.exists(asset_path):
        print(f"   WARNING: No asset for scene {index}, using black screen.")
        cmd = f'ffmpeg -y -f lavfi -i color=c=black:s=1920x1080:d={duration} -vf "format=yuv420p,setsar=1" -c:v libx264 -preset ultrafast -t {duration} -r 25 "{output_path}"'
        _run_ffmpeg(cmd, index)
        return

    is_image = asset_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    if is_image:
        if motion == "zoom_in": zoom_filter = f"zoompan=z='min(zoom+0.0015,1.5)':d={duration * 25}:s=1920x1080:fps=25,setsar=1"
        elif motion == "zoom_out": zoom_filter = f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={duration * 25}:s=1920x1080:fps=25,setsar=1"
        else: zoom_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
        cmd = f'ffmpeg -y -loop 1 -i "{asset_path}" -vf "{zoom_filter}" -c:v libx264 -preset ultrafast -threads 2 -pix_fmt yuv420p -r 25 -t {duration} -an "{output_path}"'
        _run_ffmpeg(cmd, index)
    else:
        cmd = f'ffmpeg -y -stream_loop -1 -i "{asset_path}" -t {duration} -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,format=yuv420p" -c:v libx264 -preset ultrafast -threads 2 -pix_fmt yuv420p -r 25 -an "{output_path}"'
        _run_ffmpeg(cmd, index)

def _concat_two(a, b, output):
    txt = TEMP_DIR / f"concat_pair_{abs(hash(a+b))}.txt"
    txt.write_text(f"file '{os.path.abspath(a)}'\nfile '{os.path.abspath(b)}'\n")
    cmd = f'ffmpeg -y -f concat -safe 0 -i "{txt}" -c copy -movflags +faststart "{output}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        cmd = f'ffmpeg -y -f concat -safe 0 -i "{txt}" -c:v libx264 -preset ultrafast -threads 2 -pix_fmt yuv420p -r 25 -an "{output}"'
        _run_ffmpeg(cmd, -1)
    try: txt.unlink()
    except Exception: pass

def _chunk_concat(scene_files, output_path):
    current = list(scene_files)
    round_num = 0
    while len(current) > 1:
        next_round = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                merged = str(TEMP_DIR / f"merge_{round_num}_{i}.mp4")
                _concat_two(current[i], current[i + 1], merged)
                next_round.append(merged)
            else:
                next_round.append(current[i])
        current = next_round
        round_num += 1
        print(f"      Chunk merge round {round_num}: {len(current)} files remaining")
    import shutil
    shutil.copy(current[0], output_path)

def render_final_video(timeline: list, audio_path: str, srt_path: str, output_path: str):
    print("\nRendering individual scenes...")
    scene_files = []
    for i, scene in enumerate(timeline):
        scene_output = TEMP_DIR / f"scene_{i:03d}.mp4"
        asset_path = scene.get("downloaded_asset")
        try:
            render_scene(scene, asset_path, str(scene_output), i)
            if os.path.exists(str(scene_output)) and os.path.getsize(str(scene_output)) > 1000:
                scene_files.append(str(scene_output))
        except Exception as e: print(f"      Scene {i} failed: {str(e)[:100]}")

    if not scene_files: raise RuntimeError("No scenes rendered successfully.")

    print(f"\nConcatenating {len(scene_files)} scenes (chunked)...")
    concatenated = TEMP_DIR / "concatenated.mp4"
    _chunk_concat(scene_files, str(concatenated))
    print("      Concatenation complete")

    print("Adding audio and subtitles...")
    use_subs = os.path.exists(srt_path) and os.path.getsize(srt_path) > 10

    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path], capture_output=True, text=True)
        audio_duration = float(result.stdout.strip())
    except Exception: audio_duration = 0.0

    trim_flag = f"-t {audio_duration}" if audio_duration > 0 else ""

    if use_subs:
        srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        sub_filter = f"subtitles='{srt_escaped}':force_style='FontName=Noto Sans Devanagari,FontSize=48,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,MarginV=100'"
        cmd = f'ffmpeg -y -i "{concatenated}" -i "{audio_path}" -vf "{sub_filter}" {trim_flag} -c:v libx264 -preset fast -c:a aac -pix_fmt yuv420p "{output_path}"'
    else:
        cmd = f'ffmpeg -y -i "{concatenated}" -i "{audio_path}" {trim_flag} -c:v libx264 -preset fast -c:a aac -pix_fmt yuv420p "{output_path}"'

    _run_ffmpeg(cmd, -1)
    print(f"\n✓ Final video rendered: {output_path}")
    return output_path
