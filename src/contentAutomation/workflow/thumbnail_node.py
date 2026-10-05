import base64
import logging
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Optional
import requests
from PIL import Image

from contentAutomation.config import settings
from contentAutomation.workflow.structure import PipelineState

logger = logging.getLogger("contentAutomation.thumbnail")


def create_thumbnail(prompt: str, output_path: str, max_retries: int = 3) -> Optional[str]:
    """
    Generate an AI thumbnail using Cloudflare Flux-1-schnell model,
    crop to 16:9, resize to 1280x720, and save as JPEG.
    """
    account_id = settings.cloudflare_account_id
    api_token = settings.cloudflare_api_token

    if not account_id or not api_token:
        logger.warning("Cloudflare credentials not configured. Skipping thumbnail generation.")
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": prompt}

    delay = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Generating thumbnail via Cloudflare Flux (attempt {attempt}/{max_retries})...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            image_b64 = data.get("result", {}).get("image")
            if not image_b64:
                raise ValueError(f"No image data returned in Cloudflare response: {data}")

            # Decode and process image
            raw_bytes = base64.b64decode(image_b64)
            with Image.open(BytesIO(raw_bytes)) as raw_image:
                orig_width, orig_height = raw_image.size
                target_width, target_height = 1280, 720
                target_aspect = target_width / target_height
                orig_aspect = orig_width / orig_height

                # Center crop to 16:9
                if orig_aspect > target_aspect:
                    new_width = int(target_aspect * orig_height)
                    left = (orig_width - new_width) // 2
                    top = 0
                    right = left + new_width
                    bottom = orig_height
                else:
                    new_height = int(orig_width / target_aspect)
                    left = 0
                    top = (orig_height - new_height) // 2
                    right = orig_width
                    bottom = top + new_height

                cropped = raw_image.crop((left, top, right, bottom))
                final_thumbnail = cropped.resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                )

                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                final_thumbnail.convert("RGB").save(output_path, "JPEG", quality=90)

            logger.info(f"Thumbnail successfully saved: {output_path} (1280x720)")
            return output_path

        except Exception as e:
            logger.warning(f"Thumbnail generation attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2.0

    logger.error("Failed to generate thumbnail after retries.")
    return None


def generate_thumbnail_node(state: PipelineState) -> PipelineState:
    """Thumbnail generation node for the LangGraph pipeline."""
    metadata = state.get("metadata")
    prompt = getattr(metadata, "image_prompt", None) if metadata else None
    if not prompt:
        logger.warning("No image prompt available in metadata. Skipping thumbnail.")
        state["thumbnail_path"] = None
        return state

    temp_dir = state.get("temp_dir") or "."
    target_path = os.path.join(temp_dir, "thumbnail.jpg")

    saved_path = create_thumbnail(prompt, target_path)
    state["thumbnail_path"] = saved_path
    return state


if __name__ == "__main__":
    import sys
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else "High resolution API development in VS Code"
    out = create_thumbnail(test_prompt, "output/test_thumbnail.jpg")
    print("Thumbnail created at:", out)
