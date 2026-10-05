import logging
import time
from contentAutomation.workflow.structure import PipelineState, VideoMetadata
from contentAutomation.models.model import get_chat_llm

logger = logging.getLogger("contentAutomation.metadata")


def generate_metadata_node(state: PipelineState) -> PipelineState:
    """
    Generate high-performing YouTube/video metadata (title, description, tags, thumbnail prompt)
    using Groq LLM with structured output.
    """
    logger.info("Node 3: Generating metadata using LLM...")
    transcript = state.get("transcript") or state.get("original_transcript") or ""

    if not transcript:
        logger.warning("Transcript is empty, using fallback metadata.")
        state["metadata"] = VideoMetadata(
            title="Video Content",
            description="Video upload",
            tags=["video", "content"],
            image_prompt="A high quality cinematic video thumbnail",
        )
        return state

    # Keep transcript within reasonable token budget (first 30k characters if very long)
    if len(transcript) > 30000:
        logger.info("Truncating transcript context for metadata prompt to first 30,000 chars.")
        transcript = transcript[:30000] + "\n\n[Transcript continues...]"

    detected_lang = state.get("detected_language", "unknown")

    llm = get_chat_llm()
    structured_llm = llm.with_structured_output(VideoMetadata)

    system_prompt = (
        "You are a top-tier video marketing strategist and SEO specialist.\n"
        f"The original video language was '{detected_lang}'.\n"
        "Analyze the transcript and generate compelling, high-converting metadata:\n"
        "- Title: Catchy, clear, click-worthy, SEO-optimized title.\n"
        "- Description: Comprehensive overview, timestamps summary if applicable, calls to action.\n"
        "- Tags: 7-12 highly relevant SEO keywords/tags.\n"
        "- Image Prompt: Detailed visual scene description optimized for FLUX.1 image generation that represents the core subject."
    )
    user_prompt = f"Here is the video transcript:\n\n{transcript}"

    max_retries = 3
    delay = 1.0
    metadata = None

    for attempt in range(1, max_retries + 1):
        try:
            metadata = structured_llm.invoke([
                ("system", system_prompt),
                ("user", user_prompt),
            ])
            break
        except Exception as e:
            logger.warning(f"Metadata generation attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2.0
            else:
                logger.error("Failed to generate metadata via structured LLM, falling back to default.")
                metadata = VideoMetadata(
                    title="Engaging Video Presentation",
                    description="Detailed video discussion and presentation.",
                    tags=["presentation", "educational", "discussion"],
                    image_prompt="Cinematic shot of modern technology workspace with vibrant lighting",
                )

    state["metadata"] = metadata
    logger.info(f"Generated Title: {metadata.title}")
    return state
