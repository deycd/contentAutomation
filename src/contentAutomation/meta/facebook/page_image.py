import requests
import os
from dotenv import load_dotenv

load_dotenv()

PAGE_ID = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

BASE_URL = f"https://graph.facebook.com/v26.0"

def post_image(message, file_path_or_url, is_url=False):
    print("\n--- Posting Image... ---")
    url = f"{BASE_URL}/{PAGE_ID}/photos"
    
    payload = {
        "caption": message,
        "access_token": PAGE_ACCESS_TOKEN
    }
    
    if is_url:
        payload["url"] = file_path_or_url
        response = requests.post(url, data=payload)
    else:
        if not os.path.exists(file_path_or_url):
            print("Error: Local image file not found.")
            return
        with open(file_path_or_url, "rb") as img_file:
            files = {"source": img_file}
            response = requests.post(url, data=payload, files=files)
            
    print("Response:", response.json())
