# Video Content Automation Pipeline

An automation pipeline designed to streamline video content creation and multi-platform social media publishing. This system extracts audio, transcribes content, generates SEO-optimized metadata and custom thumbnails using Large Language Models (LLMs) and AI image generation, and facilitates publishing to YouTube, Facebook, and Instagram.

## Key Features

*   **Automated Audio Extraction**: Extracts audio tracks from input video files.
*   **Intelligent Audio Transcription**: Transcribes audio content into text, featuring automatic chunking for handling large video files efficiently, leveraging Groq's Whisper model.
*   **LLM-Powered Metadata Generation**: Generates SEO-friendly video titles, detailed descriptions, relevant tags, and a prompt for thumbnail creation using a structured LLM (LangChain Groq).
*   **AI Thumbnail Creation**: Dynamically generates and crops YouTube-optimized thumbnails (1280x720) using Cloudflare's FLUX.1 image generation model.
*   **LangGraph Workflow Orchestration**: Manages the entire content processing pipeline as a stateful, modular graph, ensuring robust and sequential execution.
*   **YouTube Integration**: Supports uploading videos and updating existing video metadata (title, description) via the YouTube Data API.
*   **Facebook Page Publishing**: Enables posting text updates, images, and video reels directly to a designated Facebook Page.
*   **Instagram Business Account Publishing**: Facilitates posting images and reels to an Instagram Business Account, including robust media processing status polling for reliable uploads.
*   **Temporary Asset Cleanup**: Automatically removes temporary audio files generated during the workflow to maintain a clean environment.

## Project Directory Layout

```
.
└── src/
    └── contentAutomation/
        ├── __init__.py
        ├── main.py
        ├── models/
        │   ├── __init__.py
        │   └── model.py
        ├── meta/
        │   ├── facebook/
        │   │   ├── page_image.py
        │   │   ├── page_reel.py
        │   │   ├── page_text.py
        │   │   └── page_upload.py
        │   └── instagram/
        │       ├── insta_post_image.py
        │       ├── insta_post_reels.py
        │       └── insta_utils.py
        ├── youtube/
        │   ├── authentication.py
        │   ├── content_update.py
        │   └── content_upload.py
        └── workflow/
            ├── __init__.py
            ├── cleanUp_node.py
            ├── extract_audio_node.py
            ├── generate_metadata_node.py
            ├── pipeline.py
            ├── prompt.py
            ├── structure.py
            ├── thumbnail_node.py
            └── transcribe_audio_node.py
```

## Installation Steps

Follow these steps to set up and run the project.

### Prerequisites

*   Python 3.8+

### 1. Clone the Repository (if applicable)

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Create and Activate a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
uv venv
source venv/bin/activate # On Windows: .\venv\Scripts\activate
```

### 3. Install Dependencies

Install all required Python packages:

```bash
uv pip install -r pyproject.toml
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory of your project and populate it with the necessary API keys and IDs.

```ini
# Groq API Key (for LLM and Whisper transcription)
GROQ_API_KEY="YOUR_GROQ_API_KEY"

# Cloudflare AI Gateway (for thumbnail generation)
CLOUDFLARE_ACCOUNT_ID="YOUR_CLOUDFLARE_ACCOUNT_ID"
CLOUDFLARE_API_TOKEN="YOUR_CLOUDFLARE_API_TOKEN"

# Facebook Page API (for Facebook publishing)
PAGE_ID="YOUR_FACEBOOK_PAGE_ID"
PAGE_ACCESS_TOKEN="YOUR_FACEBOOK_PAGE_ACCESS_TOKEN"

# Instagram Graph API (for Instagram publishing)
INSTAGRAM_ACCOUNT_ID="YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
ACCESS_TOKEN="YOUR_INSTAGRAM_ACCESS_TOKEN" # This is typically a long-lived Page Access Token linked to the Instagram Business Account
```

### 5. YouTube API Credentials

For YouTube integration, you need to set up a project in the Google Cloud Console, enable the YouTube Data API v3, and download your `client_secret.json` file. Place this file in the root directory of your project. The authentication flow will automatically generate `token_upload.json` and `token_metadata.json` upon first use.

## Usage Examples

### 1. Run the Core Content Automation Pipeline

This executes the LangGraph workflow to extract audio, transcribe, generate metadata, and create a thumbnail for a given video.

Ensure you have a video file (e.g., `video_file.mp4`) in the project root or update the `video_path` in `main.py`.

```bash
uv pip install -e .
uv run python -m contentAutomation/main.py
```

**Expected Output:**
The script will print the generated video title, description, tags, and thumbnail prompt. A `thumbnail.jpg` file will be saved in the current directory.

```
 Starting LangGraph Pipeline Execution...
Node 1: Extracting audio from video...
Node 2: Transcribing audio (with auto-chunking)...
File size okay. Transcribing directly...
Node 3: Generating metadata using LLM...
Node 4: Cleaning up temporary assets...
Perfectly scaled 1280x720 YouTube thumbnail saved!

================ FINAL OUTPUT ================
    Title: Your Generated Video Title
    Description:
Your detailed video description generated by LLM.

    Tags: keyword1, keyword2, keyword3, keyword4, keyword5, keyword6, keyword7

    Thumbnail Prompt: A detailed prompt for AI image generation based on video content.
==============================================
```

### 2. YouTube Video Upload

**YouTube API Credentials**:
    For YouTube integration, you need to set up a project in the Google Cloud Console, enable the YouTube Data API v3, and download your `client_secret.json` file. Place this file in the `src/contentAutomation/youtube/` directory (or where `authentication.py` is executed from). The first time you run a YouTube-related script, it will open a browser for authentication and save `token_upload.json` and `token_metadata.json`.
    
Uploads a video to YouTube with specified title, description, and tags.

```bash
uv run src/contentAutomation/youtube/content_upload.py
```

**Note:**
*   Modify `src/contentAutomation/youtube/content_upload.py` to point to your actual video file path and desired metadata.
*   The first time you run this, a browser window will open for Google authentication.

### 3. YouTube Video Metadata Update

Updates the title and description of an existing YouTube video.

```bash
uv run src/contentAutomation/youtube/content_update.py
```

**Note:**
*   Modify `src/contentAutomation/youtube/content_update.py` with the `video_id` of the video you wish to update and the new title/description.
*   The first time you run this, a browser window will open for Google authentication.

### 4. Facebook Page Publishing

Posts text, an image, or a video reel to your configured Facebook Page.

```bash
python src/contentAutomation/meta/facebook/page_upload.py
```

**Note:**
*   Ensure `image.jpg` and `reel.mp4` exist in the `src/contentAutomation/meta/facebook/` directory or update the paths in `page_upload.py` if you intend to test image/reel uploads.

### 5. Instagram Publishing (Conceptual Usage)

The Instagram posting functions (`insta_post_image`, `insta_post_reel`) are designed to be called from other scripts, as they do not contain direct execution blocks (`if __name__ == "__main__":`).

Here's an example of how you might integrate them into another Python script:

```python
# my_instagram_publisher.py
from src.contentAutomation.meta.instagram.insta_post_image import post_instagram_image
from src.contentAutomation.meta.instagram.insta_post_reels import post_instagram_reel

if __name__ == "__main__":
    # Example: Post an image to Instagram
    # The image_url MUST be a publicly accessible URL.
    post_instagram_image(
        image_url="https://example.com/your-public-image.jpg",
        caption="This is a great image! #photography #instadaily"
    )

    # Example: Post a reel to Instagram
    # The video_url MUST be a publicly accessible URL.
    post_instagram_reel(
        video_url="https://example.com/your-public-reel.mp4",
        caption="Check out this new reel! #reels #viralvideo"
    )
```

To run this conceptual example (after creating `my_instagram_publisher.py`):

```bash
python my_instagram_publisher.py
```