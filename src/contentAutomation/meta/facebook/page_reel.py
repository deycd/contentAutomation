import requests
import os
from dotenv import load_dotenv

load_dotenv()

PAGE_ID = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

BASE_URL = f"https://graph.facebook.com/v26.0"

def post_reel(description, video_file_path):
    print("\n--- Posting Reel... ---")
    if not os.path.exists(video_file_path):
        print("Error: Reel video file not found.")
        return
        
    file_size = os.path.getsize(video_file_path)

    # Step 3.1: Initialize Session
    init_url = f"{BASE_URL}/{PAGE_ID}/video_reels"
    init_payload = {"upload_phase": "start", "access_token": PAGE_ACCESS_TOKEN}
    init_res = requests.post(init_url, data=init_payload).json()
    
    video_id = init_res.get("video_id")
    if not video_id:
        print("Reel Initialization Failed:", init_res)
        return

    # Step 3.2: Stream Upload File (Note: rupload subdomain)
    upload_url = f"https://rupload.facebook.com/video-upload/v26.0/{video_id}"
    upload_headers = {
        "Authorization": f"OAuth {PAGE_ACCESS_TOKEN}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream"
    }
    with open(video_file_path, "rb") as f:
        upload_res = requests.post(upload_url, headers=upload_headers, data=f).json()
        
    if not upload_res.get("success"):
        print("Reel File Upload Failed:", upload_res)
        return

    # Step 3.3: Publish Reel
    publish_url = f"{BASE_URL}/{PAGE_ID}/video_reels"
    publish_payload = {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": description,
        "access_token": PAGE_ACCESS_TOKEN
    }
    print("Publish Response:", requests.post(publish_url, data=publish_payload).json())