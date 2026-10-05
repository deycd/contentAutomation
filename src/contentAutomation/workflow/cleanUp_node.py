import logging
import os
import shutil
from contentAutomation.workflow.structure import PipelineState

logger = logging.getLogger("contentAutomation.cleanup")


def cleanup_node(state: PipelineState) -> PipelineState:
    """Safely cleans up temporary audio and intermediate processing files."""
    logger.info("Node 5: Cleaning up temporary assets...")

    audio_path = state.get("audio_path")
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
            logger.info(f"Removed temporary audio: {audio_path}")
        except OSError as e:
            logger.warning(f"Could not remove audio file {audio_path}: {e}")

    # If a temp directory was created and only contained intermediate chunk files
    temp_dir = state.get("temp_dir")
    if temp_dir and os.path.isdir(temp_dir):
        # Look for any lingering transcribe chunks
        for item in os.listdir(temp_dir):
            if item.startswith("transcribe_chunk_") or item.startswith("temp_"):
                try:
                    os.remove(os.path.join(temp_dir, item))
                except OSError:
                    pass

    return state
