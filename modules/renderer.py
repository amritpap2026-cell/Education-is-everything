"""FFmpeg video assembly engine - final corrected version."""
import subprocess
import os
from pathlib import Path

TEMP_DIR = Path("assets/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def _seconds(time_str: str) -> int:
    try:
        parts = str(time_str).split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


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

    # Black screen fallback
    if not asset_path or not os.path.exists(asset_path):
        print(f"   WARNING: No asset for scene {index}, using black screen.")
        cmd = (
            f'ffmpeg -y -f lavfi -i color=c=black:s=1920x1080:d={duration} '
            f'-vf "format=yuv420p,setsar=1" -c:v libx264 -t {duration} -r 25 "{output_path}"'
        )
        _run_ffmpeg(cmd, index)
        return

    is_image = asset_path.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))

    if is_image:
        if motion == "zoom_in":
            zoom_filter = f"zoompan=z='min(zoom+0.0015,1.5)':d={duration * 25}:s=1920x1080:fps=25,setsar=1"
        elif motion == "zoom_out":
            zoom_filter = f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={duration * 25}:s=1920x1080:fps=25,setsar=1"
        else:
            zoom_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"

        cmd = (
            f'ffmpeg -y -loop 1 -i "{asset_path}" '
            f'-vf "{zoom_filter}" -c:v libx264 -t {duration} '
            f'-pix_fmt yuv420p -r 25 "{output_path}"'
        )
        _run_ffmpeg(cmd, index)
    else:
        cmd = (
            f'ffmpeg -y -stream_loop -1 -i "{asset_path}" -t {duration} '
            f'-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,fps=25" '
            f'-c:v libx264 -pix_fmt yuv420p -r 25 -an "{output_path}"'
        )
        _run_ffmpeg(cmd, index)


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
        except Exception as e:
            print(f"   Scene {i} failed: {e}")
            continue

    if not scene_files:
        raise RuntimeError("No scenes rendered successfully.")

    # === CONCATENATION using filter_complex (not demuxer) ===
    print(f"\nConcatenating {len(scene_files)} scenes via filter...")

    # Build list of inputs
    inputs = " ".join([f'-i "{f}"' for f in scene_files])
    # Build the concat filter chain
    streams = "".join([f"[{i}:v]" for i in range(len(scene_files))])
    filter_complex = f"{streams}concat=n={len(scene_files)}:v=1:a=0[outv]"

    concatenated = TEMP_DIR / "concatenated.mp4"
    concat_cmd = (
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[outv]" -c:v libx264 -pix_fmt yuv420p -r 25 -preset fast "{concatenated}"'
    )
    _run_ffmpeg(concat_cmd, -1)
    print("   Concatenation complete.")

    # === ADD AUDIO + SUBTITLES ===
    print("Adding audio and subtitles...")
    use_subtitles = os.path.exists(srt_path) and os.path.getsize(srt_path) > 10

    if use_subtitles:
        srt_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        sub_filter = (
            f"subtitles='{srt_escaped}':"
            f"force_style='FontName=DejaVu Sans,FontSize=22,"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"BorderStyle=1,Outline=2,Shadow=1,MarginV=40'"
        )
        final_cmd = (
            f'ffmpeg -y -i "{concatenated}" -i "{audio_path}" '
            f'-vf "{sub_filter}" '
            f'-c:v libx264 -preset fast -c:a aac -shortest -pix_fmt yuv420p "{output_path}"'
        )
    else:
        print("   No subtitles, rendering without them.")
        final_cmd = (
            f'ffmpeg -y -i "{concatenated}" -i "{audio_path}" '
            f'-c:v libx264 -preset fast -c:a aac -shortest -pix_fmt yuv420p "{output_path}"'
        )

    _run_ffmpeg(final_cmd, -1)
    print(f"\n✓ Final video rendered: {output_path}")
    return output_path