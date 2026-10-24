"""Main orchestrator for the 100% free automated video pipeline."""
import argparse, json, os, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from agents.researcher import research
from agents.scriptwriter import write_script
from modules.tts import generate_voiceover
from modules.assets import fetch_asset_for_scene
from modules.renderer import render_final_video
from modules.uploader import upload

def main():
    parser = argparse.ArgumentParser(description="Automated YouTube Video Pipeline")
    parser.add_argument("--topic", type=str, required=True)
    parser.add_argument("--minutes", type=int, default=5)
    parser.add_argument("--language", type=str, default="English")
    parser.add_argument("--privacy", type=str, default="private")
    parser.add_argument("--skip-upload", action="store_true")
    args = parser.parse_args()

    topic = args.topic
    print(f"\n=== Starting Pipeline for: {topic} ===")
    print(f"=== Language: {args.language} ===\n")

    print("1. Researching topic...")
    dossier = research(topic, args.language, "General public")
    
    print("\n2. Writing script and generating timeline...")
    package = write_script(dossier, args.minutes, args.language)
    timeline = package.get("timeline", [])
    full_script = package.get("full_script", "")
    
    if not timeline:
        print("ERROR: No timeline generated.")
        sys.exit(1)

    Path("output").mkdir(exist_ok=True)
    with open("output/package.json", "w", encoding="utf-8") as f:
        json.dump(package, f, ensure_ascii=False, indent=2)

    print("\n3. Generating voiceover and subtitles...")
    audio_path, ass_path = generate_voiceover(full_script, args.language)
    
    print("\n4. Downloading assets...")
    for scene in timeline:
        asset_path = fetch_asset_for_scene(scene)
        scene["downloaded_asset"] = asset_path

    print("\n5. Rendering final video...")
    output_video = "output/final_video.mp4"
    render_final_video(timeline, audio_path, ass_path, output_video)
    
    if args.skip_upload:
        print("\n=== Rendering complete (skip upload) ===")
        return

    print("\n6. Uploading to YouTube...")
    try:
        result = upload(
            video_path=output_video,
            title=package.get("title", topic),
            description=package.get("description", ""),
            tags=package.get("tags", []),
            language=args.language,
            privacy=args.privacy if args.privacy != "private" else None,
        )
        print(f"\n=== SUCCESS! {result['url']} ===")
    except Exception as e:
        print(f"\nUpload failed: {e}")
        print(f"Video still available at: {output_video}")
        sys.exit(1)

if __name__ == "__main__":
    main()
