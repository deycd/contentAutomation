import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cms.utils")


def format_timestamp(seconds: float, srt_format: bool = False, vtt_format: bool = False) -> str:
    """
    Convert seconds into formatted timestamp string.
    - Default: [HH:MM:SS.mmm]
    - SRT:     HH:MM:SS,mmm
    - VTT:     HH:MM:SS.mmm
    """
    total_milliseconds = max(0, round(seconds * 1000))
    hours = total_milliseconds // 3_600_000
    remaining_ms = total_milliseconds % 3_600_000
    minutes = remaining_ms // 60_000
    remaining_ms %= 60_000
    secs = remaining_ms // 1_000
    milliseconds = remaining_ms % 1_000

    if srt_format:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    if vtt_format:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}]"


def generate_srt(segments: List[Dict[str, Any]]) -> str:
    """Generate a valid SubRip (.srt) subtitle string from structured segments."""
    srt_lines = []
    idx = 1
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        start_ts = format_timestamp(float(seg.get("start", 0.0)), srt_format=True)
        end_ts = format_timestamp(float(seg.get("end", 0.0)), srt_format=True)
        srt_lines.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")
        idx += 1
    return "\n".join(srt_lines)


def generate_vtt(segments: List[Dict[str, Any]]) -> str:
    """Generate a valid WebVTT (.vtt) subtitle string from structured segments."""
    vtt_lines = ["WEBVTT\n"]
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        start_ts = format_timestamp(float(seg.get("start", 0.0)), vtt_format=True)
        end_ts = format_timestamp(float(seg.get("end", 0.0)), vtt_format=True)
        vtt_lines.append(f"{start_ts} --> {end_ts}\n{text}\n")
    return "\n".join(vtt_lines)


def extract_audio_with_ffmpeg(video_path: str, output_path: str) -> bool:
    """
    Extract optimized mono 16kHz speech audio using system ffmpeg.
    Returns True on success, False if ffmpeg failed or not found.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        output_path,
    ]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"FFmpeg audio extraction failed or ffmpeg not found: {e}")
        return False


def create_bordered_reel(
    input_file: str | Path,
    output_file: str | Path,
    start_sec: float,
    duration_sec: float,
    border_thickness: int = 4,
    border_color: str = "white",
    target_width: int = 1080,
    target_height: int = 1920,
) -> bool:
    """
    Generate a 9:16 vertical short-form video (Reel/Short/TikTok) from an input video.
    Scales the video, adds a clean border, and letterboxes into a 1080x1920 frame.
    """
    input_str = str(input_file)
    output_str = str(output_file)

    if not os.path.exists(input_str):
        logger.error(f"Input video file not found for reel creation: {input_str}")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_str)), exist_ok=True)

    # Filter graph:
    # 1. Scale width to target_width - 2*border_thickness
    # 2. Add border using pad
    # 3. Center inside target 9:16 frame (1080x1920)
    filter_graph = (
        f"scale={target_width - 2 * border_thickness}:-1,"
        f"pad=iw+{2 * border_thickness}:ih+{2 * border_thickness}:{border_thickness}:{border_thickness}:{border_color},"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black"
    )

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        input_str,
        "-t",
        f"{duration_sec:.3f}",
        "-lavfi",
        filter_graph,
        "-c:v",
        "libx264",
        "-profile:v",
        "main",
        "-level:v",
        "4.0",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_str,
    ]

    try:
        logger.info(
            f"Rendering 9:16 bordered reel [{start_sec:.2f}s - {start_sec + duration_sec:.2f}s] -> {output_str}"
        )
        res = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        logger.info(f"Successfully generated reel: {output_str}")
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        stderr_msg = e.stderr.decode("utf-8", errors="replace") if hasattr(e, "stderr") and e.stderr else str(e)
        logger.error(f"FFmpeg reel rendering failed for {output_str}: {stderr_msg}")
        return False


def save_pipeline_outputs(
    output_dir: Path | str,
    video_path: str,
    state: Dict[str, Any],
) -> Dict[str, Path]:
    """
    Save structured pipeline artifacts (subtitles, metadata, transcript, thumbnail, reels)
    to a dedicated output directory.
    """
    out_path = Path(output_dir)
    video_stem = Path(video_path).stem
    job_dir = out_path / video_stem
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_files: Dict[str, Path] = {}

    metadata = state.get("metadata")
    if metadata:
        meta_dict = {
            "title": getattr(metadata, "title", ""),
            "description": getattr(metadata, "description", ""),
            "tags": getattr(metadata, "tags", []),
            "image_prompt": getattr(metadata, "image_prompt", ""),
            "detected_language": state.get("detected_language"),
        }
        meta_file = job_dir / "metadata.json"
        meta_file.write_text(json.dumps(meta_dict, indent=2, ensure_ascii=False), encoding="utf-8")
        saved_files["metadata_json"] = meta_file

        # Markdown summary
        md_content = f"""# {meta_dict['title']}

## Description
{meta_dict['description']}

## Tags
{', '.join(meta_dict['tags'])}

## Detected Language
{meta_dict['detected_language']}

## Thumbnail Prompt
> {meta_dict['image_prompt']}
"""
        md_file = job_dir / "metadata.md"
        md_file.write_text(md_content, encoding="utf-8")
        saved_files["metadata_md"] = md_file

    # Save original transcript & subtitles
    orig_segments = state.get("segments")
    if orig_segments:
        orig_srt = job_dir / "subtitles_original.srt"
        orig_srt.write_text(generate_srt(orig_segments), encoding="utf-8")
        saved_files["subtitles_original_srt"] = orig_srt

    # Save translated transcript & subtitles
    trans_segments = state.get("translated_segments") or orig_segments
    if trans_segments:
        trans_srt = job_dir / "subtitles_english.srt"
        trans_srt.write_text(generate_srt(trans_segments), encoding="utf-8")
        saved_files["subtitles_english_srt"] = trans_srt

    # Save full text transcript
    transcript_text = state.get("transcript") or state.get("original_transcript")
    if transcript_text:
        txt_file = job_dir / "transcript.txt"
        txt_file.write_text(transcript_text, encoding="utf-8")
        saved_files["transcript_txt"] = txt_file

    # Save timestamped transcript
    timestamps_text = state.get("transcript_timestamps")
    if timestamps_text:
        ts_file = job_dir / "transcript_timestamps.txt"
        ts_file.write_text(timestamps_text, encoding="utf-8")
        saved_files["transcript_timestamps_txt"] = ts_file

    # Copy thumbnail if generated
    thumbnail_path = state.get("thumbnail_path")
    if thumbnail_path and os.path.exists(thumbnail_path):
        dest_thumb = job_dir / "thumbnail.jpg"
        if Path(thumbnail_path).resolve() != dest_thumb.resolve():
            shutil.copy2(thumbnail_path, dest_thumb)
        saved_files["thumbnail"] = dest_thumb

    # Save generated reels and reels metadata
    reels_data = state.get("reels") or []
    reel_paths = state.get("reel_paths") or []
    if reels_data or reel_paths:
        reels_dir = job_dir / "reels"
        reels_dir.mkdir(parents=True, exist_ok=True)

        saved_reels_meta = []
        for idx, reel in enumerate(reels_data):
            reel_dict = reel if isinstance(reel, dict) else reel.model_dump()
            saved_reels_meta.append(reel_dict)

        # Save reels_metadata.json
        reels_json_file = reels_dir / "reels_metadata.json"
        reels_json_file.write_text(
            json.dumps(saved_reels_meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        saved_files["reels_metadata_json"] = reels_json_file

        # Copy / verify generated reel video files
        reels_md_lines = ["# Generated Short-Form Reels\n"]
        for idx, (reel_meta, src_path) in enumerate(zip(saved_reels_meta, reel_paths), 1):
            dest_reel = reels_dir / f"reel_{idx}.mp4"
            if os.path.exists(src_path) and Path(src_path).resolve() != dest_reel.resolve():
                shutil.copy2(src_path, dest_reel)
            saved_files[f"reel_{idx}_video"] = dest_reel

            reels_md_lines.append(f"## Reel {idx}: {reel_meta.get('title', 'Reel Clip')}")
            reels_md_lines.append(f"- **Timeframe**: {format_timestamp(reel_meta.get('start_time', 0.0))} - {format_timestamp(reel_meta.get('end_time', 0.0))}")
            reels_md_lines.append(f"- **Hook**: {reel_meta.get('hook', '')}")
            reels_md_lines.append(f"- **Caption**: {reel_meta.get('caption', '')}")
            reels_md_lines.append(f"- **Reasoning**: {reel_meta.get('reasoning', '')}")
            reels_md_lines.append(f"- **File**: `{dest_reel.name}`\n")

        reels_md_file = reels_dir / "reels_summary.md"
        reels_md_file.write_text("\n".join(reels_md_lines), encoding="utf-8")
        saved_files["reels_summary_md"] = reels_md_file

    logger.info(f"Saved pipeline artifacts to: {job_dir}")
    return saved_files