from contentAutomation.workflow.structure import PipelineState
from pydub import AudioSegment
import os
import math
from contentAutomation.models.model import groq_client

def transcribe_audio_node(state: PipelineState) -> PipelineState:
	print("Node 2: Transcribing audio (with auto-chunking)...")
	audio_path = state["audio_path"]
	

	MAX_BYTES = 18 * 1024 * 1024 
	file_size = os.path.getsize(audio_path)
	
	full_transcript = ""
	
	if file_size <= MAX_BYTES:

		print("File size okay. Transcribing directly...")
		with open(audio_path, "rb") as f:
			response = groq_client.audio.translations.create(
			model="whisper-large-v3",
			temperature=0.0,
			response_format="json",
			timeout=600.0
			)
		full_transcript = response.text
	else:

		print(f"File size ({file_size / (1024*1024):.2f}MB) exceeds limit. Splitting into chunks...")
		audio = AudioSegment.from_file(audio_path)
		
		total_duration_ms = len(audio)
		num_chunks = math.ceil(file_size / MAX_BYTES)
		chunk_duration_ms = math.floor(total_duration_ms / num_chunks) 
		for i in range(num_chunks):
			start_time = i * chunk_duration_ms
			
			end_time = min((i + 1) * chunk_duration_ms, total_duration_ms)
			
			print(f"Processing chunk...")
			chunk = audio[start_time:end_time]
			
			chunk_filename = f"temp_chunk_{i}.mp3"
			chunk.export(chunk_filename, format="mp3")
			
			with open(chunk_filename, "rb") as f:
				response = groq_client.audio.translations.create(
					file=(os.path.basename(chunk_filename), f.read()),
					model="whisper-large-v3",
					temperature=0.0,
					response_format="json",
					timeout=600.0
				)

			full_transcript += " " + response.text
			os.remove(chunk_filename) 
			
	state["transcript"] = full_transcript.strip()
	return state
