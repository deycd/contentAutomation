from contentAutomation.meta.facebook.page_image import post_image
from contentAutomation.meta.facebook.page_reel import post_reel
from contentAutomation.meta.facebook.page_text import post_text

if __name__ == "__main__":
    post_text("Hello from automated Python script!")
    
    post_image("Look at this beautiful view!", "image.jpg", is_url=False)
    
    post_reel("Trending content! #viral #shorts", "reel.mp4")