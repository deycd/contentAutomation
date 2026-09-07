from contentAutomation.youtube.authentication import get_authenticated_service

METADATA_SCOPE = ['https://www.googleapis.com/auth/youtube']
youtube_service = get_authenticated_service(scopes=METADATA_SCOPE, token_filename='token_metadata.json')

def update_video_metadata(video_id, new_title, new_description):
    """Edits the metadata of an existing video."""
    print(f"Updating metadata for Video ID: {video_id}")

    
    get_request = youtube_service.videos().list(part='snippet', id=video_id)
    get_response = get_request.execute()
    
    if not get_response.get('items'):
        print("Video not found.")
        return
    
    video_snippet = get_response['items'][0]['snippet']
    

    video_snippet['title'] = new_title
    video_snippet['description'] = new_description


    update_request = youtube_service.videos().update(
        part='snippet',
        body={
            'id': video_id,
            'snippet': video_snippet
        }
    )
    update_response = update_request.execute()
    print("Metadata updated successfully!")
    print(f"New Title: {update_response['snippet']['title']}")

if __name__ == "__main__":
    update_video_metadata(
        video_id="jdhzPz865yo",
        new_title="Updated Modified Title",
        new_description="dscription has been updated using the videos().update method!"
    )
