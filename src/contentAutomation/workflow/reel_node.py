import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from contentAutomation.models.model import get_chat_llm
from contentAutomation.utils import create_bordered_reel, format_timestamp
from contentAutomation.workflow.prompt import reel_system_prompt
from contentAutomation.workflow.structure import PipelineState, ReelCandidate, ReelsResponse

logger = logging.getLogger("contentAutomation.reels")

MIN_REEL_DURATION_SEC = 30.0
MAX_REEL_DURATION_SEC = 90.0
DEFAULT_MAX_REELS = 2


def _extract_reel_candidates_with_llm(
    transcript_timestamps: str,
    max_reels: int = DEFAULT_MAX_REELS,
    max_retries: int = 3,
) -> List[ReelCandidate]:
    """
    Query the LLM with structured output to analyze timestamped transcript
    and return the top standalone viral reel candidates.
    """
    llm = get_chat_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(ReelsResponse)

    # Context window protection: keep within first 40,000 characters if very long
    prompt_transcript = transcript_timestamps
    if len(prompt_transcript) > 40000:
        logger.info("Truncating timestamped transcript for reel prompt to first 40,000 chars.")
        prompt_transcript = prompt_transcript[:40000] + "\n\n[Transcript continues...]"

    user_prompt = (
        f"Analyze the following timestamped video transcript and select up to {max_reels} "
        f"of the most engaging, viral, standalone short-form video clips (30 to 90 seconds each).\n\n"
        f"Video Timestamped Transcript:\n"
        f"{prompt_transcript}\n\n"
        f"Return up to {max_reels} candidates with exact start_time (in seconds) and end_time (in seconds), "
        f"a strong hook, catchy title, social media caption with hashtags, and strategic reasoning."
    )

    delay = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Analyzing transcript for reel clips (attempt {attempt}/{max_retries})...")
            response = structured_llm.invoke([
                ("system", reel_system_prompt),
                ("user", user_prompt),
            ])

            if response and hasattr(response, "reels") and response.reels:
                logger.info(f"LLM identified {len(response.reels)} reel candidate(s).")
                return response.reels[:max_reels]
            break

        except Exception as e:
            logger.warning(f"Reel extraction attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2.0

    logger.warning("Could not extract reel candidates via structured LLM.")
    return []


def generate_reels_node(state: PipelineState) -> PipelineState:
    """
    LangGraph workflow node:
    1. Analyzes timestamped transcript using LLM to locate viral clips.
    2. Cuts each clip and renders a 9:16 vertical bordered reel video via FFmpeg.
    3. Populates state['reels'] and state['reel_paths'].
    """
    if state.get("generate_reels") is False:
        logger.info("Reel generation is disabled. Skipping reel node.")
        state["reels"] = []
        state["reel_paths"] = []
        return state

    video_path = state.get("video_path")
    if not video_path or not os.path.exists(video_path):
        logger.warning(f"Input video file not found for reel generation: {video_path}")
        state["reels"] = []
        state["reel_paths"] = []
        return state

    transcript_timestamps = state.get("transcript_timestamps")
    if not transcript_timestamps:
        # Fallback: try building from segments
        segments = state.get("translated_segments") or state.get("segments") or []
        if segments:
            transcript_timestamps = "\n".join(
                f"{format_timestamp(s['start'])} {s['text']}" for s in segments
            )

    if not transcript_timestamps:
        logger.warning("No timestamped transcript available. Skipping reel generation.")
        state["reels"] = []
        state["reel_paths"] = []
        return state

    max_reels = state.get("max_reels", DEFAULT_MAX_REELS) or DEFAULT_MAX_REELS
    logger.info(f"Node: Analyzing transcript to create up to {max_reels} short-form reels...")

    candidates = _extract_reel_candidates_with_llm(
        transcript_timestamps=transcript_timestamps,
        max_reels=max_reels,
    )

    if not candidates:
        logger.info("No valid reel candidates found.")
        state["reels"] = []
        state["reel_paths"] = []
        return state

    temp_dir = state.get("temp_dir") or tempfile.gettempdir()
    rendered_paths: List[str] = []
    valid_reels: List[Dict[str, Any]] = []

    for idx, cand in enumerate(candidates, 1):
        start_sec = float(cand.start_time)
        end_sec = float(cand.end_time)
        duration = end_sec - start_sec

        # Validate duration bounds
        if duration < MIN_REEL_DURATION_SEC:
            logger.warning(
                f"Candidate {idx} duration ({duration:.1f}s) is too short (<{MIN_REEL_DURATION_SEC}s). Adjusting or skipping."
            )
            if duration <= 0:
                continue

        if duration > MAX_REEL_DURATION_SEC:
            logger.info(f"Candidate {idx} duration ({duration:.1f}s) exceeds max limit, capping at {MAX_REEL_DURATION_SEC}s.")
            duration = MAX_REEL_DURATION_SEC
            end_sec = start_sec + duration

        out_reel_path = os.path.join(temp_dir, f"reel_{idx}.mp4")

        success = create_bordered_reel(
            input_file=video_path,
            output_file=out_reel_path,
            start_sec=start_sec,
            duration_sec=duration,
            border_thickness=4,
            border_color="white",
            target_width=1080,
            target_height=1920,
        )

        if success and os.path.exists(out_reel_path):
            rendered_paths.append(out_reel_path)
            cand_dict = cand.model_dump()
            cand_dict["start_time"] = start_sec
            cand_dict["end_time"] = end_sec
            cand_dict["duration"] = round(duration, 2)
            valid_reels.append(cand_dict)
            logger.info(f"Created Reel {idx}: '{cand.title}' ({duration:.1f}s) -> {out_reel_path}")

    state["reels"] = valid_reels
    state["reel_paths"] = rendered_paths
    logger.info(f"Reel generation complete: {len(rendered_paths)} reel(s) rendered.")
    return state
