import os
import base64
from io import BytesIO
from dotenv import load_dotenv
import requests
from PIL import Image
from contentAutomation.workflow.structure import PipelineState
load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

def create_thumbnail(prompt):
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"

    headers = {
        "Authorization": f"Bearer {API_TOKEN}", 
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
    )

    response.raise_for_status()

    data = response.json()

    image_b64 = data["result"]["image"]

    raw_image = Image.open(
        BytesIO(base64.b64decode(image_b64))
    )

    raw_image.save("thumbnail.jpg")
    orig_width, orig_height = raw_image.size
    
    # Target criteria for YouTube
    target_width = 1280
    target_height = 720
    target_aspect = target_width / target_height  # 1.7777...
    orig_aspect = orig_width / orig_height
    
    # Calculate crop bounding box coordinates (left, upper, right, lower)
    if orig_aspect > target_aspect:
        # Image is too wide: crop the sides
        new_width = int(target_aspect * orig_height)
        left = (orig_width - new_width) // 2
        top = 0
        right = left + new_width
        bottom = orig_height
    else:
        # Image is too tall/square: crop the top and bottom
        new_height = int(orig_width / target_aspect)
        left = 0
        top = (orig_height - new_height) // 2
        right = orig_width
        bottom = top + new_height

    # Execute the crop framing the absolute center of the AI generation
    cropped_image = raw_image.crop((left, top, right, bottom))
    
    # Smoothly downscale to 1280x720 using the high-quality LANCZOS anti-aliasing filter
    final_thumbnail = cropped_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Save to your output file format (optimized at 90% quality to stay well beneath YT's 2MB limit)
    final_thumbnail.convert("RGB").save("thumbnail.jpg", "JPEG", quality=90)

    print("Perfectly scaled 1280x720 YouTube thumbnail saved!")

def generate_thumbnail_node(state: PipelineState) -> PipelineState:
	prompt = state["metadata"].image_prompt
	create_thumbnail(prompt)
	return state
