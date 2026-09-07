from contentAutomation.workflow.structure import PipelineState
from contentAutomation.workflow.extract_audio_node import extract_audio_node
from contentAutomation.workflow.transcribe_audio_node import transcribe_audio_node
from contentAutomation.workflow.generate_metadata_node import generate_metadata_node
from contentAutomation.workflow.thumbnail_node import generate_thumbnail_node
from contentAutomation.workflow.cleanUp_node import cleanup_node
from langgraph.graph import StateGraph, END

workflow = StateGraph(PipelineState)

workflow.add_node("extract_audio", extract_audio_node)
workflow.add_node("transcribe_audio", transcribe_audio_node)
workflow.add_node("generate_metadata", generate_metadata_node)
workflow.add_node("generate_thumbnail", generate_thumbnail_node)
workflow.add_node("cleanup", cleanup_node)

workflow.set_entry_point("extract_audio")
workflow.add_edge("extract_audio", "transcribe_audio")
workflow.add_edge("transcribe_audio", "generate_metadata")
workflow.add_edge("generate_metadata", "generate_thumbnail")
workflow.add_edge("generate_thumbnail", "cleanup")
workflow.add_edge("cleanup", END)

app = workflow.compile()
