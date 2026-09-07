from contentAutomation.workflow.structure import PipelineState
import os

def cleanup_node(state: PipelineState) -> PipelineState:
	print("Node 4: Cleaning up temporary assets...")
	if state["audio_path"] and os.path.exists(state["audio_path"]):
		os.remove(state["audio_path"])
	return state
