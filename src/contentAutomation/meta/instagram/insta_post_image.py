from contentAutomation.meta.instagram.insta_utils import publish_media_container
from contentAutomation.meta.instagram.insta_utils import ACCESS_TOKEN, BASE_URL, INSTAGRAM_ACCOUNT_ID
import requests

def post_instagram_image(image_url, caption):
    print("\n--- Creating Instagram Image Feed Post... ---")
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload).json()
    container_id = response.get("id")
    
    if not container_id:
        print("Failed to create image container:", response)
        return

    # Image containers process almost instantly, publish immediately
    publish_media_container(container_id)