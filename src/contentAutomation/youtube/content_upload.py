from googleapiclient.http import MediaFileUpload
import os
import sys
from contentAutomation.youtube.authentication import get_authenticated_service


UPLOAD_SCOPE = ['https://www.googleapis.com/auth/youtube.upload']

youtube = get_authenticated_service(scopes=UPLOAD_SCOPE, token_filename='token_upload.json')

def upload_video(video_file_path, title, description, tags, category_id="22"):
    """Uploads a video to YouTube with metadata."""
    print(f"Starting upload for: {video_file_path}")
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id 
        },
        'status': {
            'privacyStatus': 'private' 
        }
    }
    media = MediaFileUpload(video_file_path, chunksize=1024*1024, mimetype='video/*', resumable=True)
    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
            
    print(f"Upload Complete! Video ID: {response['id']}")
    return response['id']

if __name__ == "__main__":

    video_id = upload_video(
        video_file_path="../dem-test.mp4",
        title="Test Video Upload",
        description="This is a test video upload using the YouTube API.",
        tags=["test", "upload", "api"]
    )
    print(f"Uploaded Video ID: {video_id}")