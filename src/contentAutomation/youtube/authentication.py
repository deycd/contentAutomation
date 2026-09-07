from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

def get_authenticated_service(scopes, token_filename):
    creds = None
    if os.path.exists(token_filename):
        creds = Credentials.from_authorized_user_file(token_filename, scopes)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', scopes)
            creds = flow.run_local_server(port=0)
            
        with open(token_filename, 'w') as token:
            token.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)
