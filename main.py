import openai
import os
from dotenv import load_dotenv  # You'll need to: pip install python-dotenv
from pydub import AudioSegment
import math
import json
from datetime import datetime
from config import (
    WHISPER_MODEL, 
    WHISPER_TEMPERATURE, 
    WHISPER_LANGUAGE, 
    WHISPER_PROMPT,
    WHISPER_RESPONSE_FORMAT
)

# Load API key from environment variable
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

client = openai.OpenAI(api_key=api_key)

def get_audio_files_from_data():
    """
    Find all audio files in the data folder
    Returns a list of file paths or empty list if no audio files found
    """
    # Supported audio formats
    audio_extensions = ('.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm')
    
    # Check data directory
    data_dir = "data"
    if not os.path.exists(data_dir):
        print(f"Error: data directory not found")
        return []
    
    # Look for all audio files
    audio_files = []
    for file in os.listdir(data_dir):
        if file.lower().endswith(audio_extensions):
            audio_files.append(os.path.join(data_dir, file))
    
    if not audio_files:
        print("No audio files found in data directory")
    else:
        print(f"Found {len(audio_files)} audio file(s)")
        
    return audio_files

def transcribe_audio(audio_file_path):
    try:
        # Verify file exists and is readable
        if not os.path.exists(audio_file_path):
            print(f"File not found: {audio_file_path}")
            return None
            
        # Try to load the audio file with pydub to verify it's valid
        try:
            audio = AudioSegment.from_file(audio_file_path, format="mp3")
            print(f"Successfully loaded audio file: {os.path.basename(audio_file_path)}")
            print(f"Duration: {len(audio)/1000:.2f} seconds")
        except Exception as e:
            print(f"Error loading audio file with pydub: {str(e)}")
            return None

        # Open and transcribe the file
        with open(audio_file_path, "rb") as audio_file:
            # Call the Whisper API with new client format
            transcript = client.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=audio_file,
                prompt=WHISPER_PROMPT,
                response_format=WHISPER_RESPONSE_FORMAT,
                language=WHISPER_LANGUAGE,
                temperature=WHISPER_TEMPERATURE
            )
        
        return transcript
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def split_audio_file(file_path, target_size_mb=20, size_tolerance_mb=2):
    """
    Split an audio file into chunks of roughly target_size_mb, using silence detection
    to find natural break points. Allows for size_tolerance_mb variation.
    """
    # Get the file size in MB
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    
    # If file is smaller than target size + tolerance, return original file path
    if file_size <= target_size_mb + size_tolerance_mb:
        return [file_path]
    
    # Load the audio file
    audio = AudioSegment.from_file(file_path)
    
    # Calculate approximate chunk duration in milliseconds
    total_duration_ms = len(audio)
    target_chunk_duration = math.floor(total_duration_ms * (target_size_mb / file_size))
    
    # Detect silence periods (min_silence_len=500ms, silence_thresh=-40dBFS)
    silence_periods = detect_silence(
        audio,
        min_silence_len=500,
        silence_thresh=-40,
        seek_step=250
    )
    
    chunk_paths = []
    start_pos = 0
    current_chunk = 1
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join("data", "chunks")
    os.makedirs(output_dir, exist_ok=True)
    
    while start_pos < total_duration_ms:
        # Calculate the ideal end position for this chunk
        ideal_end_pos = start_pos + target_chunk_duration
        
        if ideal_end_pos >= total_duration_ms:
            # If this is the last chunk, just use the remaining audio
            end_pos = total_duration_ms
        else:
            # Find the closest silence period to our ideal end position
            closest_silence = None
            min_distance = float('inf')
            
            for silence_start, silence_end in silence_periods:
                if silence_start > start_pos:
                    distance = abs(silence_start - ideal_end_pos)
                    if distance < min_distance and abs(silence_start - start_pos) / 1000 * (file_size / total_duration_ms) <= target_size_mb + size_tolerance_mb:
                        min_distance = distance
                        closest_silence = (silence_start, silence_end)
            
            # If we found a suitable silence period, use it; otherwise use ideal_end_pos
            if closest_silence:
                end_pos = closest_silence[0]  # Use the start of the silence period
            else:
                end_pos = ideal_end_pos
        
        # Extract the chunk
        chunk = audio[start_pos:end_pos]
        
        # Generate output path for chunk
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        chunk_path = os.path.join(output_dir, f"{file_name}_chunk_{current_chunk}.mp3")
        
        # Export chunk
        chunk.export(chunk_path, format="mp3")
        chunk_paths.append(chunk_path)
        
        # Print chunk information
        chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
        print(f"Created chunk {current_chunk}: {chunk_size_mb:.2f}MB ({(end_pos-start_pos)/1000:.2f} seconds)")
        
        # Move to next chunk
        start_pos = end_pos
        current_chunk += 1
    
    return chunk_paths

def detect_silence(audio_segment, min_silence_len=500, silence_thresh=-40, seek_step=250):
    """
    Detect silence in an audio segment
    Returns list of [start_ms, end_ms] ranges of silence
    """
    from pydub.silence import detect_nonsilent
    
    # Get non-silent ranges
    non_silent_ranges = detect_nonsilent(
        audio_segment,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        seek_step=seek_step
    )
    
    # Convert non-silent ranges to silent ranges
    silent_ranges = []
    
    if not non_silent_ranges:
        return [(0, len(audio_segment))]
    
    # Add any silence at the beginning
    if non_silent_ranges[0][0] > 0:
        silent_ranges.append((0, non_silent_ranges[0][0]))
    
    # Add silence between non-silent ranges
    for i in range(len(non_silent_ranges)-1):
        silent_ranges.append((non_silent_ranges[i][1], non_silent_ranges[i+1][0]))
    
    # Add any silence at the end
    if non_silent_ranges[-1][1] < len(audio_segment):
        silent_ranges.append((non_silent_ranges[-1][1], len(audio_segment)))
    
    return silent_ranges

def save_chunk_transcription(transcript, source_filename, chunk_number, total_chunks):
    """
    Save individual chunk transcription to a JSON file in the output/chunks folder
    """
    # Create output/chunks directory if it doesn't exist
    chunks_dir = os.path.join("output", "chunks")
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Create filename based on source audio file, chunk number, and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(source_filename))[0]
    chunk_file = os.path.join(chunks_dir, f"{base_name}_chunk{chunk_number}of{total_chunks}_{timestamp}.json")
    
    # Save the transcript
    with open(chunk_file, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    
    return chunk_file

def merge_transcripts(transcripts):
    """
    Merge multiple transcript dictionaries while maintaining structure
    """
    if not transcripts:
        return None
    
    # Initialize merged transcript with full JSON structure
    merged = {
        "text": [],
        "language": transcripts[0].get("language", "mixed"),
        "task": transcripts[0].get("task", "transcribe"),
        "duration": 0.0,
        "segments": []
    }
    
    # Track time offset for segments
    time_offset = 0.0
    
    # Merge each transcript
    for transcript in transcripts:
        if isinstance(transcript, str):
            merged["text"].append(transcript)
            continue
            
        # Add text
        merged["text"].append(transcript.get("text", ""))
        
        # Add duration
        chunk_duration = float(transcript.get("duration", 0.0))
        merged["duration"] += chunk_duration
        
        # Adjust and merge segments
        segments = transcript.get("segments", [])
        for segment in segments:
            # Adjust segment timestamps with current offset
            adjusted_segment = segment.copy()
            adjusted_segment["start"] = float(segment.get("start", 0.0)) + time_offset
            adjusted_segment["end"] = float(segment.get("end", 0.0)) + time_offset
            merged["segments"].append(adjusted_segment)
        
        # Update time offset for next chunk
        time_offset += chunk_duration
    
    # Join all text pieces
    merged["text"] = " ".join(merged["text"])
    
    # Convert duration to string format
    merged["duration"] = str(merged["duration"])
    
    return merged

def find_existing_chunks(audio_filename):
    """
    Check if chunks already exist for this audio file
    Returns a list of chunk files if found, None otherwise
    """
    # Only check in data/chunks directory
    chunks_dir = os.path.join("data", "chunks")
    if not os.path.exists(chunks_dir):
        print("\nAudio Chunk Check")
        print("No data/chunks directory found")
        return None
        
    base_name = os.path.splitext(os.path.basename(audio_filename))[0]
    chunk_files = []
    
    # Look for files matching the pattern base_name_chunk{N}of{M}*.mp3
    for file in sorted(os.listdir(chunks_dir)):
        if file.startswith(f"{base_name}_chunk") and file.endswith(".mp3"):
            chunk_files.append(os.path.join(chunks_dir, file))
    
    # Debug output with clear formatting
    print("\nAudio Chunk Check")
    if chunk_files:
        print(f"Found {len(chunk_files)} existing MP3 chunks in data/chunks folder:")
        for chunk in chunk_files:
            print(f"   - {os.path.basename(chunk)}")
    else:
        print("No existing MP3 chunks found in data/chunks folder")
    
    return chunk_files if chunk_files else None

def find_existing_json_chunks(audio_filename):
    """
    Check if JSON chunks already exist for this audio file
    Returns a list of JSON chunk files if found, None otherwise
    """
    chunks_dir = os.path.join("output", "chunks")
    if not os.path.exists(chunks_dir):
        return None
        
    base_name = os.path.splitext(os.path.basename(audio_filename))[0]
    json_chunks = []
    
    # Look for files matching the pattern base_name_chunk{N}of{M}*.json
    for file in sorted(os.listdir(chunks_dir)):
        if file.startswith(f"{base_name}_chunk") and file.endswith(".json"):
            json_chunks.append(os.path.join(chunks_dir, file))
    
    # Debug output with clear formatting
    print("\nJSON Chunk Check")
    if json_chunks:
        print(f"Found {len(json_chunks)} existing JSON chunks in output/chunks folder:")
        for chunk in json_chunks:
            print(f"   - {os.path.basename(chunk)}")
        return json_chunks
    else:
        print("No existing JSON chunks found in output/chunks folder")
        return None

def transcribe_large_audio(file_path):
    """
    Transcribe an audio file of any size by splitting if necessary
    """
    # First check for existing JSON chunks
    existing_json_chunks = find_existing_json_chunks(file_path)
    if existing_json_chunks:
        print(f"Found {len(existing_json_chunks)} existing JSON chunks, loading them...")
        transcripts = []
        for json_file in existing_json_chunks:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    transcript_dict = json.load(f)
                    transcripts.append(transcript_dict)
                print(f"Loaded JSON chunk: {os.path.basename(json_file)}")
            except Exception as e:
                print(f"Error loading JSON chunk {json_file}: {str(e)}")
                continue
        
        print("\nCombining existing JSON chunks into final output...")
        if transcripts:
            return merge_transcripts(transcripts)
        return None
    
    # If no JSON chunks exist, check for MP3 chunks
    existing_chunks = find_existing_chunks(file_path)
    if existing_chunks:
        print(f"Found {len(existing_chunks)} existing MP3 chunks, transcribing them...")
        # Transcribe existing chunks
        transcripts = []
        for i, chunk_file in enumerate(existing_chunks, 1):
            try:
                print(f"Transcribing existing chunk: {os.path.basename(chunk_file)}")
                transcript = transcribe_audio(chunk_file)
                if transcript:
                    if hasattr(transcript, 'model_dump'):
                        transcript_dict = transcript.model_dump()
                    else:
                        transcript_dict = transcript
                        
                    # Save individual chunk transcription
                    chunk_file = save_chunk_transcription(transcript_dict, file_path, i, len(existing_chunks))
                    print(f"Chunk {i} transcription saved to: {chunk_file}")
                    
                    transcripts.append(transcript_dict)
            except Exception as e:
                print(f"Error transcribing chunk {chunk_file}: {str(e)}")
                continue
        
        print("\nCombining all transcripts into final output...")
        if transcripts:
            return merge_transcripts(transcripts)
        return None
    
    # If no existing chunks found, proceed with splitting and transcription
    print("\nNo existing chunks found. Splitting audio file into chunks...")
    chunk_paths = split_audio_file(file_path)
    
    # If only one chunk, transcribe normally
    if len(chunk_paths) == 1:
        transcript = transcribe_audio(chunk_paths[0])
        if transcript:
            if hasattr(transcript, 'model_dump'):
                transcript_dict = transcript.model_dump()
            else:
                transcript_dict = transcript
            return transcript_dict
        return None
    
    # Transcribe each chunk
    transcripts = []
    total_chunks = len(chunk_paths)
    
    for i, chunk_path in enumerate(chunk_paths, 1):
        print(f"Transcribing chunk {i} of {total_chunks}...")
        transcript = transcribe_audio(chunk_path)
        if transcript:
            try:
                # Convert to dictionary if needed
                if hasattr(transcript, 'model_dump'):
                    transcript_dict = transcript.model_dump()
                else:
                    transcript_dict = transcript
                    
                # Save individual chunk transcription
                chunk_file = save_chunk_transcription(transcript_dict, file_path, i, total_chunks)
                print(f"Chunk {i} JSON saved to: {chunk_file}")
                
                transcripts.append(transcript_dict)
            except Exception as e:
                print(f"Warning: Error processing chunk {i}: {str(e)}")
                continue
    
    print("\nCombining all transcripts into final output...")
    if transcripts:
        return merge_transcripts(transcripts)
    return None

def save_final_extract(transcripts, source_filename):
    """
    Save final combined transcription to JSON file in output folder
    """
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename based on source audio file and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(source_filename))[0]
    output_file = os.path.join(output_dir, f"{base_name}_extract_{timestamp}.json")
    
    # Save the combined transcript
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transcripts, f, ensure_ascii=False, indent=2)
    
    print(f"\nFinal extract saved to: {os.path.basename(output_file)}")
    return output_file

def save_processed_transcript(transcript, source_filename):
    """
    Save transcript text to file in output folder
    """
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename based on source audio file and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(source_filename))[0]
    txt_file = os.path.join(output_dir, f"{base_name}_extract_{timestamp}.txt")
    
    # Extract text from transcript and save as text
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(transcript.get('text', ''))
    
    print(f"\nTranscript saved to: {os.path.basename(txt_file)}")
    return txt_file

def cleanup_chunk_folders():
    """
    Clean up the chunks folders at startup, but preserve the original data and output files
    """
    # Folders to clean
    chunk_folders = [
        os.path.join("data", "chunks"),
        os.path.join("output", "chunks")
    ]
    
    for folder in chunk_folders:
        if os.path.exists(folder):
            print(f"Cleaning {folder} directory...")
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error: {e}")
        else:
            print(f"Creating {folder} directory...")
            os.makedirs(folder, exist_ok=True)

# Update main execution
if __name__ == "__main__":
    # Clean up chunk folders at startup
    cleanup_chunk_folders()
    
    # Find all audio files in data folder
    audio_paths = get_audio_files_from_data()
    
    if not audio_paths:
        print("Error: No audio files found in the data folder")
        print("Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm")
        exit(1)
    
    # Process each audio file
    for audio_path in audio_paths:
        print(f"\nProcessing audio file: {os.path.basename(audio_path)}")
        
        # Get the transcription using the new function
        result = transcribe_large_audio(audio_path)
        
        if result:
            # Save transcript to output folder
            txt_file = save_processed_transcript(result, audio_path)
