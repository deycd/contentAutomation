from contentAutomation.workflow.structure import PipelineState
from moviepy import VideoFileClip

def extract_audio_node(state: PipelineState) -> PipelineState:
	print("Node 1: Extracting audio from video...")
	video_path = state["video_path"]
	a_path = "temp_full_audio.mp3"
	
	video = VideoFileClip(video_path)
	video.audio.write_audiofile(a_path, logger=None)
	video.close()
	
	state["audio_path"] = a_path
	return state
