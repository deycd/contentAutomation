from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
from contentAutomation.workflow.prompt import title, description, tags, image_prompt


class VideoMetadata(BaseModel):
    title: str = Field(description=title)
    description: str = Field(description=description)
    tags: List[str] = Field(description=tags)
    image_prompt: str = Field(description=image_prompt)


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TranslatedSegmentItem(BaseModel):
    id: int
    text: str


class BatchTranslationResponse(BaseModel):
    translations: List[TranslatedSegmentItem]


class ReelCandidate(BaseModel):
    title: str = Field(description="Catchy title or hook description for the reel")
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    hook: str = Field(description="The opening hook or key engaging sentence of this clip")
    caption: str = Field(description="Social media caption including 3-5 relevant hashtags")
    reasoning: str = Field(description="Why this segment makes a great standalone short-form reel")


class ReelsResponse(BaseModel):
    reels: List[ReelCandidate] = Field(
        default_factory=list,
        description="List of best viral short-form reel candidates (15-60 seconds each)",
    )


class PipelineState(TypedDict, total=False):
    video_path: str
    audio_path: Optional[str]
    temp_dir: Optional[str]
    transcript: Optional[str]
    transcript_timestamps: Optional[str]
    original_transcript: Optional[str]
    translated_segments: Optional[List[Dict[str, Any]]]
    detected_language: Optional[str]
    segments: Optional[List[Dict[str, Any]]]
    translate_to_english: Optional[bool]
    metadata: Optional[VideoMetadata]
    thumbnail_path: Optional[str]
    generate_reels: Optional[bool]
    max_reels: Optional[int]
    reels: Optional[List[Dict[str, Any]]]
    reel_paths: Optional[List[str]]
    error: Optional[str]

