import concurrent.futures
import json
import logging
import re
import time
from typing import Any, Dict, List

from contentAutomation.config import settings
from contentAutomation.models.model import get_google_client
from contentAutomation.utils import format_timestamp
from contentAutomation.workflow.structure import (
    BatchTranslationResponse,
    PipelineState,
)

logger = logging.getLogger("cms.translate")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TRANSLATION_BATCH_SIZE = 150
MAX_PARALLEL_WORKERS = 1
MAX_RETRIES = 3

RETRY_INITIAL_DELAY = 1.0
REQUEST_TIMEOUT = 120.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_json_markdown(text: str) -> str:
    """
    Remove Markdown code fences if the model returns:

    ```json
    {...}
    ```

    Gemini structured output should normally return plain JSON,
    but this makes the parser more robust.
    """
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    return text.strip()


# ---------------------------------------------------------------------------
# Gemini translation
# ---------------------------------------------------------------------------

def _translate_batch_direct(
    segments: List[Dict[str, Any]],
    batch_start_index: int,
    max_retries: int = MAX_RETRIES,
) -> List[Dict[str, Any]]:
    """
    Translate one batch of transcript segments using Google Gemini.

    Guarantees:
    - Original IDs are preserved internally.
    - Original timestamps are preserved.
    - Output is validated using BatchTranslationResponse.
    - Failed batches are retried.
    - Large failed batches are subdivided.
    - Original text is returned as fallback if translation fails.
    """

    client = get_google_client()

    translation_input = [
        {
            "id": batch_start_index + idx,
            "text": seg["text"],
        }
        for idx, seg in enumerate(segments)
    ]

    system_instruction = """
You are a professional video translator and subtitle localization expert.

Translate the provided transcript segments into natural, fluent English.

Rules:

1. Translate every segment.
2. Preserve the meaning of the original speech.
3. Preserve the original spoken tone and conversational style.
4. Do not summarize.
5. Do not merge segments.
6. Do not split segments.
7. Do not add explanations.
8. Do not add timestamps.
9. Do not add commentary.
10. Preserve every input ID exactly.
11. Every input ID must appear exactly once in the output.
12. Only translate the "text" field.
"""

    user_prompt = f"""
Translate the following transcript segments into English.

Input:

{json.dumps(
    translation_input,
    ensure_ascii=False,
    indent=2,
)}

Return one translation for every input segment.
"""

    last_error = None
    delay = RETRY_INITIAL_DELAY

    for attempt in range(1, max_retries + 1):

        try:
            response = client.models.generate_content(
                model=settings.google_translation_model,
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "translations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {
                                            "type": "integer",
                                        },
                                        "text": {
                                            "type": "string",
                                        },
                                    },
                                    "required": [
                                        "id",
                                        "text",
                                    ],
                                },
                            }
                        },
                        "required": [
                            "translations",
                        ],
                    },
                },
            )

            raw_content = response.text or "{}"

            cleaned_content = _clean_json_markdown(
                raw_content
            )

            parsed = json.loads(cleaned_content)

            # --------------------------------------------------------------
            # Validate Gemini output using your existing Pydantic schema
            # --------------------------------------------------------------

            validated = BatchTranslationResponse.model_validate(
                parsed
            )

            items = validated.translations

            # --------------------------------------------------------------
            # Build ID -> translated text lookup
            # --------------------------------------------------------------

            lookup = {
                item.id: item.text.strip()
                for item in items
                if item.text
            }

            # --------------------------------------------------------------
            # Validate that Gemini returned all expected IDs
            # --------------------------------------------------------------

            expected_ids = {
                item["id"]
                for item in translation_input
            }

            returned_ids = set(lookup.keys())

            missing_ids = expected_ids - returned_ids

            if missing_ids:
                raise ValueError(
                    f"Gemini response is missing IDs: "
                    f"{sorted(missing_ids)}"
                )

            # --------------------------------------------------------------
            # Reconstruct segments while preserving timestamps
            # --------------------------------------------------------------

            result: List[Dict[str, Any]] = []

            for seg, input_item in zip(
                segments,
                translation_input,
            ):
                expected_id = input_item["id"]

                translated_text = lookup.get(
                    expected_id,
                    seg["text"],
                )

                result.append(
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": translated_text,
                    }
                )

            return result

        except Exception as exc:

            last_error = exc

            logger.warning(
                "Gemini translation batch "
                f"(ids {batch_start_index}-"
                f"{batch_start_index + len(segments) - 1}) "
                f"attempt {attempt}/{max_retries} failed: {exc}"
            )

            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2.0

    # ----------------------------------------------------------------------
    # Retry using smaller batches
    # ----------------------------------------------------------------------

    if len(segments) > 5:

        logger.info(
            f"Sub-dividing failed batch of "
            f"{len(segments)} segments."
        )

        mid = len(segments) // 2

        first_half = _translate_batch_direct(
            segments[:mid],
            batch_start_index,
            max_retries=2,
        )

        second_half = _translate_batch_direct(
            segments[mid:],
            batch_start_index + mid,
            max_retries=2,
        )

        return first_half + second_half

    # ----------------------------------------------------------------------
    # Final fallback
    # ----------------------------------------------------------------------

    logger.error(
        f"Failed translating batch starting at "
        f"{batch_start_index}: {last_error}"
    )

    logger.warning(
        "Returning original text for failed translation batch."
    )

    return [
        {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
        }
        for seg in segments
    ]


# ---------------------------------------------------------------------------
# LangGraph translation node
# ---------------------------------------------------------------------------

def translate_to_english_node(
    state: PipelineState,
) -> PipelineState:
    """
    Translate transcript segments into natural English.

    Features:
    - Gemini translation
    - Batch processing
    - Parallel translation
    - JSON structured output
    - Pydantic validation
    - Retry handling
    - Batch subdivision
    - Exact timestamp preservation
    """

    logger.info(
        "Node: Translating transcript to English using Gemini..."
    )

    segments = state.get("segments") or []

    if not segments:

        logger.info(
            "No transcript segments available for translation."
        )

        state["translated_segments"] = []

        return state

    # Preserve original transcript before replacing state["transcript"]
    if not state.get("original_transcript"):

        state["original_transcript"] = state.get(
            "transcript",
            "",
        )

    total_segments = len(segments)

    logger.info(
        f"Total segments to translate: {total_segments}"
    )

    # ----------------------------------------------------------------------
    # Create batches
    # ----------------------------------------------------------------------

    batches: List[
        tuple[int, List[Dict[str, Any]]]
    ] = []

    for batch_start in range(
        0,
        total_segments,
        TRANSLATION_BATCH_SIZE,
    ):

        batch_end = min(
            batch_start + TRANSLATION_BATCH_SIZE,
            total_segments,
        )

        batches.append(
            (
                batch_start,
                segments[batch_start:batch_end],
            )
        )

    logger.info(
        f"Created {len(batches)} translation batches."
    )

    # ----------------------------------------------------------------------
    # Translate batches concurrently
    # ----------------------------------------------------------------------

    translated_results: Dict[
        int,
        List[Dict[str, Any]],
    ] = {}

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_PARALLEL_WORKERS
    ) as executor:

        future_to_index = {
            executor.submit(
                _translate_batch_direct,
                batch_segments,
                batch_start,
            ): batch_start
            for batch_start, batch_segments in batches
        }

        for future in concurrent.futures.as_completed(
            future_to_index
        ):

            batch_start = future_to_index[future]

            try:

                translated_batch = future.result()

                translated_results[
                    batch_start
                ] = translated_batch

                logger.info(
                    f"Translated batch starting at "
                    f"segment {batch_start + 1}/"
                    f"{total_segments}"
                )

            except Exception as exc:

                logger.error(
                    f"Unhandled error in batch "
                    f"starting at {batch_start}: {exc}"
                )

                # ----------------------------------------------------------
                # Final fallback
                # ----------------------------------------------------------

                batch_slice = next(
                    batch_segments
                    for start, batch_segments in batches
                    if start == batch_start
                )

                translated_results[
                    batch_start
                ] = [
                    {
                        "start": segment["start"],
                        "end": segment["end"],
                        "text": segment["text"],
                    }
                    for segment in batch_slice
                ]

    # ----------------------------------------------------------------------
    # Reassemble batches in original order
    # ----------------------------------------------------------------------

    translated_segments: List[
        Dict[str, Any]
    ] = []

    for batch_start, _ in batches:

        translated_segments.extend(
            translated_results[batch_start]
        )

    # ----------------------------------------------------------------------
    # Build English transcript
    # ----------------------------------------------------------------------

    english_transcript = " ".join(
        segment["text"]
        for segment in translated_segments
    ).strip()

    # ----------------------------------------------------------------------
    # Build timestamped transcript
    # ----------------------------------------------------------------------

    timestamped_transcript = "\n".join(
        f"{format_timestamp(segment['start'])} "
        f"{segment['text']}"
        for segment in translated_segments
    )

    logger.info(
        f"Translation complete: "
        f"{len(translated_segments)} segments translated."
    )

    # ----------------------------------------------------------------------
    # Update LangGraph state
    # ----------------------------------------------------------------------

    state["translated_segments"] = translated_segments

    state["transcript"] = english_transcript

    state["transcript_timestamps"] = timestamped_transcript

    return state


# ---------------------------------------------------------------------------
# LangGraph conditional router
# ---------------------------------------------------------------------------

def should_translate(
    state: PipelineState,
) -> str:
    """
    Determine whether transcript should be translated to English.
    """

    detected_language = state.get(
        "detected_language"
    )

    if detected_language:
        detected_language = (
            detected_language
            .lower()
            .strip()
        )

    # Already English
    if detected_language in {
        "en",
        "english",
    }:

        logger.info(
            "Audio is already in English. "
            "Skipping translation."
        )

        return "skip_translation"

    # User explicitly disabled translation
    translate_flag = state.get(
        "translate_to_english",
        True,
    )

    if translate_flag is False:

        logger.info(
            "Translation explicitly disabled "
            "by user. Skipping translation."
        )

        return "skip_translation"

    logger.info(
        f"Detected language '{detected_language}'. "
        "Proceeding with Gemini translation."
    )

    return "translate"