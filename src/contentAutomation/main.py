import argparse
import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from contentAutomation.config import setup_logging
from contentAutomation.utils import save_pipeline_outputs
from contentAutomation.workflow.pipeline import app
from contentAutomation.workflow.structure import PipelineState, VideoMetadata

logger = logging.getLogger("contentAutomation")


def run_pipeline(
    video_path: str,
    translate_to_english: bool = True,
    generate_reels: bool = True,
    max_reels: int = 2,
    output_dir: str = "output",
) -> Dict[str, Any]:
    """
    Execute the end-to-end CMS video processing pipeline.
    Extracts audio, transcribes with timestamps, translates to English,
    generates marketing metadata, AI thumbnail, viral 9:16 reels, and saves all artifacts.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Create a managed job temp directory
    job_temp_dir = tempfile.mkdtemp(prefix="cms_job_")

    initial_state: PipelineState = {
        "video_path": video_path,
        "audio_path": None,
        "temp_dir": job_temp_dir,
        "transcript": None,
        "transcript_timestamps": None,
        "original_transcript": None,
        "translated_segments": None,
        "detected_language": None,
        "segments": None,
        "translate_to_english": translate_to_english,
        "metadata": None,
        "thumbnail_path": None,
        "generate_reels": generate_reels,
        "max_reels": max_reels,
        "reels": None,
        "reel_paths": None,
    }

    logger.info(f"=== Starting CMS Pipeline for: {video_path} ===")
    logger.info(f"Translation to English: {translate_to_english}")
    logger.info(f"Generate 9:16 Reels: {generate_reels} (Max: {max_reels})")

    try:
        final_output = app.invoke(initial_state)

        # Save all generated artifacts (subtitles, metadata JSON/MD, thumbnail, reels)
        saved_files = save_pipeline_outputs(output_dir, video_path, final_output)
        final_output["saved_artifacts"] = saved_files

        return final_output

    finally:
        # Guaranteed cleanup of intermediate temporary directory
        if os.path.exists(job_temp_dir):
            shutil.rmtree(job_temp_dir, ignore_errors=True)
            logger.debug(f"Removed job temporary directory: {job_temp_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CMS AI Video Content Pipeline - Transcribe, Translate, Generate Metadata, Thumbnails & 9:16 Reels"
    )
    parser.add_argument(
        "--video",
        "-v",
        type=str,
        default="demo.mp4",
        help="Path to input video file (default: demo.mp4)",
    )
    parser.add_argument(
        "--no-translate",
        dest="translate",
        action="store_false",
        help="Disable automatic translation to English",
    )
    parser.add_argument(
        "--no-reels",
        dest="reels",
        action="store_false",
        help="Disable automatic 9:16 short-form reel generation",
    )
    parser.add_argument(
        "--max-reels",
        type=int,
        default=2,
        help="Maximum number of 9:16 reels to generate (default: 2)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="output",
        help="Directory to save generated artifacts (default: output/)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging output",
    )

    args = parser.parse_args()

    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)

    if not os.path.exists(args.video):
        logger.error(f"Error: Video file '{args.video}' does not exist.")
        sys.exit(1)

    final_output = run_pipeline(
        video_path=args.video,
        translate_to_english=args.translate,
        generate_reels=args.reels,
        max_reels=args.max_reels,
        output_dir=args.output_dir,
    )

    metadata: Optional[VideoMetadata] = final_output.get("metadata")

    print("\n" + "=" * 60)
    print("              CMS PIPELINE COMPLETE")
    print("=" * 60)
    if metadata:
        print(f"\n📌 Title:\n   {metadata.title}")
        print(f"\n📝 Description:\n   {metadata.description}")
        print(f"\n🏷️  Tags:\n   {', '.join(metadata.tags)}")
        print(f"\n🎨 Thumbnail Prompt:\n   {metadata.image_prompt}")

    print(f"\n🌐 Detected Language: {final_output.get('detected_language')}")
    orig_segs = final_output.get("segments") or []
    trans_segs = final_output.get("translated_segments") or []
    print(f"📊 Segments: {len(orig_segs)} original, {len(trans_segs)} translated")

    reels_data = final_output.get("reels") or []
    if reels_data:
        print(f"\n🎬 Generated {len(reels_data)} Short-Form Reel(s):")
        for i, reel in enumerate(reels_data, 1):
            r = reel if isinstance(reel, dict) else reel.model_dump()
            print(f"   [{i}] '{r.get('title')}' ({r.get('start_time', 0.0):.1f}s - {r.get('end_time', 0.0):.1f}s, dur: {r.get('duration', 0.0):.1f}s)")
            print(f"       Hook: {r.get('hook')}")
            print(f"       Caption: {r.get('caption')}")

    saved = final_output.get("saved_artifacts", {})
    if saved:
        print("\n📁 Saved Artifacts:")
        for name, path in saved.items():
            print(f"   - {name}: {path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

