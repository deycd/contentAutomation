import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydub import AudioSegment

from contentAutomation.models.model import get_groq_client
from contentAutomation.utils import format_timestamp
from contentAutomation.workflow.structure import PipelineState

logger = logging.getLogger("contentAutomation.transcribe")

MAX_CHUNK_DURATION_MS = 20 * 60 * 1000  # 20 minutes
GROQ_MAX_FILE_BYTES = 24 * 1024 * 1024  # 24 MB safe threshold for Groq Whisper


def _transcribe_file_with_retry(
    client: Any,
    file_path: str,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
) -> Any:
    """Call Groq Whisper transcription with automatic exponential backoff retry."""
    last_exc = None
    delay = 1.0

    for attempt in range(1, max_retries + 1):
        try:
            with open(file_path, "rb") as f:
                return client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), f),
                    model="whisper-large-v3",
                    temperature=0.0,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    timeout=600.0,
                )
        except Exception as exc:
            last_exc = exc
            logger.warning(
                f"Groq Whisper attempt {attempt}/{max_retries} failed for {os.path.basename(file_path)}: {exc}"
            )
            if attempt < max_retries:
                time.sleep(delay)
                delay *= backoff_factor

    raise RuntimeError(
        f"Groq Whisper transcription failed after {max_retries} attempts for {file_path}"
    ) from last_exc


def transcribe_audio_node(state: PipelineState) -> PipelineState:
    """
    Transcribes audio using Groq Whisper-large-v3 with timestamp precision.
    Intelligently chunks only when necessary and retries on network/rate-limit hiccups.
    """
    logger.info("Node 2: Transcribing audio with precise timestamps...")
    audio_path = state.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    temp_dir = state.get("temp_dir") or os.path.dirname(audio_path)
    file_size_bytes = os.path.getsize(audio_path)

    # Load audio to get duration
    audio = AudioSegment.from_file(audio_path)
    total_duration_ms = len(audio)
    if total_duration_ms <= 0:
        raise ValueError("Extracted audio file is empty.")

    logger.info(
        f"Audio duration: {total_duration_ms / 1000:.2f}s, size: {file_size_bytes / (1024*1024):.2f} MB"
    )

    client = get_groq_client()
    raw_segments: List[Dict[str, Any]] = []
    full_transcript_parts: List[str] = []
    detected_language: Optional[str] = None

    # Decide whether chunking is required:
    # If audio is under 24MB AND under 25 minutes, transcribe directly in one piece!
    needs_chunking = (file_size_bytes > GROQ_MAX_FILE_BYTES) or (total_duration_ms > 25 * 60 * 1000)

    if not needs_chunking:
        logger.info("Audio fits within single Groq Whisper request. Transcribing directly...")
        response = _transcribe_file_with_retry(client, audio_path)

        # Detect language
        detected_language = (
            response.get("language") if isinstance(response, dict) else getattr(response, "language", None)
        )
        if detected_language:
            detected_language = detected_language.lower().strip()

        resp_text = response.get("text", "") if isinstance(response, dict) else getattr(response, "text", "")
        if resp_text:
            full_transcript_parts.append(resp_text.strip())

        segs = response.get("segments", []) if isinstance(response, dict) else getattr(response, "segments", [])
        for seg in segs:
            seg_start = seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)
            seg_end = seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
            seg_text = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
            seg_text = seg_text.strip()
            if seg_text:
                raw_segments.append({
                    "start": float(seg_start),
                    "end": float(seg_end),
                    "text": seg_text,
                })
    else:
        num_chunks = math.ceil(total_duration_ms / MAX_CHUNK_DURATION_MS)
        logger.info(f"Audio requires chunking: splitting into {num_chunks} chunks...")

        for i in range(num_chunks):
            start_ms = i * MAX_CHUNK_DURATION_MS
            end_ms = min((i + 1) * MAX_CHUNK_DURATION_MS, total_duration_ms)
            time_offset_sec = start_ms / 1000.0

            chunk_path = os.path.join(temp_dir, f"transcribe_chunk_{i}.mp3")
            logger.info(f"Processing chunk {i + 1}/{num_chunks} ({start_ms/1000:.1f}s - {end_ms/1000:.1f}s)...")

            chunk_audio = audio[start_ms:end_ms]
            chunk_audio.export(chunk_path, format="mp3", bitrate="64k")

            try:
                response = _transcribe_file_with_retry(client, chunk_path)

                if detected_language is None:
                    lang = (
                        response.get("language")
                        if isinstance(response, dict)
                        else getattr(response, "language", None)
                    )
                    if lang:
                        detected_language = lang.lower().strip()

                resp_text = (
                    response.get("text", "") if isinstance(response, dict) else getattr(response, "text", "")
                )
                if resp_text:
                    full_transcript_parts.append(resp_text.strip())

                segs = (
                    response.get("segments", [])
                    if isinstance(response, dict)
                    else getattr(response, "segments", [])
                )
                for seg in segs:
                    seg_start = seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0)
                    seg_end = seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0)
                    seg_text = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                    seg_text = seg_text.strip()
                    if seg_text:
                        raw_segments.append({
                            "start": time_offset_sec + float(seg_start),
                            "end": time_offset_sec + float(seg_end),
                            "text": seg_text,
                        })
            finally:
                if os.path.exists(chunk_path):
                    try:
                        os.remove(chunk_path)
                    except OSError:
                        pass

    full_transcript = " ".join(full_transcript_parts).strip()
    timestamped_transcript = "\n".join(
        f"{format_timestamp(s['start'])} {s['text']}" for s in raw_segments
    )

    logger.info(f"Detected language: {detected_language}")
    logger.info(f"Total transcribed segments: {len(raw_segments)}")

    state["detected_language"] = detected_language
    state["segments"] = raw_segments
    state["original_transcript"] = full_transcript
    state["transcript"] = full_transcript
    state["transcript_timestamps"] = timestamped_transcript

    return state
