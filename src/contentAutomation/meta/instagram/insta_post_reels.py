from contentAutomation.meta.instagram.insta_utils import publish_media_container, wait_for_container_processing,ACCESS_TOKEN, BASE_URL, INSTAGRAM_ACCOUNT_ID
import requests

def post_instagram_reel(video_url, caption):
    print("\n--- Creating Instagram Reel... ---")
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload).json()
    container_id = response.get("id")
    
    if not container_id:
        print("Failed to create Reel container:", response)
        return

    # Check status loop before publishing
    if wait_for_container_processing(container_id):
        publish_media_container(container_id)