from contentAutomation.workflow.structure import VideoMetadata
from contentAutomation.workflow.pipeline import app

if __name__ == "__main__":
    initial_state = {
        "video_path": "dem-test.mp4",
	    "audio_path": None,
	    "transcript": None,
	    "metadata": None
    }

    print(" Starting LangGraph Pipeline Execution...")

    final_output = app.invoke(initial_state)
        
    results: VideoMetadata = final_output["metadata"]
        
    print("\n================ FINAL OUTPUT ================")
    print(f"    Title: {results.title}\n")
    print(f"    Description:\n{results.description}\n")
    print(f"    Tags: {', '.join(results.tags)}\n")
    print(f"    Thumbnail Prompt: {results.image_prompt}\n")
    print("==============================================")