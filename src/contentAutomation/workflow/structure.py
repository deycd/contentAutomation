from pydantic import BaseModel, Field
from typing import TypedDict, List, Optional
from contentAutomation.workflow.prompt import title,description,tags,image_prompt

class VideoMetadata(BaseModel):
	title: str = Field(description=title)
	description: str = Field(description=description)
	tags: List[str] = Field(description=tags)
	image_prompt: str = Field(description=image_prompt)

class PipelineState(TypedDict):
	video_path: str
	audio_path: Optional[str]
	transcript: Optional[str]
	metadata: Optional[VideoMetadata]

