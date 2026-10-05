import logging
import os
import tempfile
from pathlib import Path
from contentAutomation.workflow.structure import PipelineState
from contentAutomation.utils import extract_audio_with_ffmpeg

logger = logging.getLogger("contentAutomation.extractor")


def extract_audio_node(state: PipelineState) -> PipelineState:
    """
    Extract speech-optimized audio from the input video file.
    Prefers ffmpeg for 10x speed and memory efficiency, falling back to moviepy.
    Audio is extracted to a dedicated temporary directory.
    """
    video_path = state["video_path"]
    logger.info(f"Node 1: Extracting audio from video: {video_path}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Ensure a managed temp directory exists for this pipeline run
    temp_dir = state.get("temp_dir")
    if not temp_dir or not os.path.isdir(temp_dir):
        temp_dir = tempfile.mkdtemp(prefix="cms_job_")
        state["temp_dir"] = temp_dir

    audio_output_path = os.path.join(temp_dir, "audio_full.mp3")

    # Method 1: Fast direct extraction using ffmpeg (speech-optimized: mono, 16kHz, 64kbps)
    success = extract_audio_with_ffmpeg(video_path, audio_output_path)

    # Method 2: Fallback to moviepy
    if not success or not os.path.exists(audio_output_path) or os.path.getsize(audio_output_path) == 0:
        logger.info("FFmpeg direct extraction unavailable or failed, falling back to MoviePy...")
        from moviepy import VideoFileClip

        video = None
        try:
            video = VideoFileClip(video_path)
            if video.audio is None:
                raise ValueError(f"Video file has no audio stream: {video_path}")
            video.audio.write_audiofile(
                audio_output_path,
                fps=16000,
                nbytes=2,
                codec="libmp3lame",
                ffmpeg_params=["-ac", "1", "-b:a", "64k"],
                logger=None,
            )
        finally:
            if video is not None:
                video.close()

    if not os.path.exists(audio_output_path) or os.path.getsize(audio_output_path) == 0:
        raise RuntimeError(f"Audio extraction failed: output file is missing or empty at {audio_output_path}")

    audio_size_mb = os.path.getsize(audio_output_path) / (1024 * 1024)
    logger.info(f"Audio extracted successfully: {audio_output_path} ({audio_size_mb:.2f} MB)")

    state["audio_path"] = audio_output_path
    return state
