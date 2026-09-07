import time
import requests
from dotenv import load_dotenv
import os

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
API_VERSION = "v26.0"

BASE_URL = f"https://graph.instagram.com/{API_VERSION}"


# =====================================================================
# CORE UTILITY: Container Polling (Crucial for Videos & Reels)
# =====================================================================
def wait_for_container_processing(container_id, max_retries=30, delay=10):
    """
    Videos and Reels take time to encode on Meta servers.
    We must poll the status until it returns 'FINISHED'.
    """
    print(f"Waiting for container {container_id} to finish processing...")
    status_url = f"{BASE_URL}/{container_id}"
    params = {
        "fields": "status_code,status",
        "access_token": ACCESS_TOKEN
    }
    
    for attempt in range(max_retries):
        response = requests.get(status_url, params=params).json()
        status_code = response.get("status_code")
        
        if status_code == "FINISHED":
            print("✅ Media processing complete!")
            return True
        elif status_code == "ERROR":
            print(f"❌ Processing failed! Error info: {response}")
            return False
        
        print(f"[{attempt + 1}/{max_retries}] Still processing (Status: {status_code}). Waiting {delay}s...")
        time.sleep(delay)
        
    print("⏳ Polling timed out.")
    return False


# =====================================================================
# CORE UTILITY: Publish Container
# =====================================================================
def publish_media_container(container_id):
    """Publishes a fully processed media container live to the feed."""
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN
    }
    response = requests.post(url, data=payload).json()
    print("Publish Response:", response)
    return response
