from contentAutomation.workflow.structure import PipelineState, VideoMetadata
from contentAutomation.models.model import llm

def generate_metadata_node(state: PipelineState) -> PipelineState:
	print("Node 3: Generating metadata using LLM...")
	transcript = state["transcript"]
	
	structured_llm = llm.with_structured_output(VideoMetadata)
	
	system_prompt = "You are an expert video marketer. Analyze the transcript and generate high-performing metadata."
	user_prompt = f"Here is the video transcript:\n\n{transcript}"
	
	metadata = structured_llm.invoke([
		("system", system_prompt),
		("user", user_prompt)
	])
	
	state["metadata"] = metadata
	return state