import requests
from dotenv import load_dotenv
import os

load_dotenv()

PAGE_ID = os.getenv("PAGE_ID")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

BASE_URL = f"https://graph.facebook.com/v26.0"

def post_text(message):
    print("\n--- Posting Text... ---")
    url = f"{BASE_URL}/{PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload)
    print("Response:", response.json())
