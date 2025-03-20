import openai
import os
import subprocess
from dotenv import load_dotenv  # You'll need to: pip install python-dotenv
from pydub import AudioSegment
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

def convert_to_ogg(audio_file_path):
    """
    Convert an audio file to OGG format using FFmpeg with the specified parameters
    Returns the path to the converted file
    """
    # Generate output file path
    convert_dir = "data/convert"
    base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    
    # Add timestamp to filename to avoid conflicts
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    output_path = os.path.join(convert_dir, f"{base_name}_{timestamp}.ogg")
    
    # Construct FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg", 
        "-i", audio_file_path, 
        "-vn", 
        "-map_metadata", "-1", 
        "-ac", "1", 
        "-c:a", "libopus", 
        "-b:a", "12k", 
        "-application", "voip", 
        output_path
    ]
    
    try:
        print(f"Converting {os.path.basename(audio_file_path)} to OGG format...")
        # Run FFmpeg command
        process = subprocess.run(
            ffmpeg_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode == 0:
            print(f"Successfully converted to: {output_path}")
            return output_path
        else:
            print(f"Error converting file: {process.stderr}")
            return None
    except Exception as e:
        print(f"Exception during conversion: {str(e)}")
        return None

def check_file_size(file_path, max_size_mb=25):
    """
    Check if a file is under the specified size limit
    Returns True if file is under the limit, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
        
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        print(f"Error: File size ({file_size_mb:.2f}MB) exceeds {max_size_mb}MB limit.")
        return False
    
    print(f"File size: {file_size_mb:.2f}MB (Under {max_size_mb}MB limit)")
    return True

def get_audio_files_from_original():
    """
    Find all audio files in the data folder
    Returns a list of file paths or empty list if no audio files found
    """
    # Supported audio formats
    audio_extensions = ('.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.aac', '.flac', '.ogg', '.oga', '.opus', '.amr')
    
    # Check data directory
    data_dir = "data/original"
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
    """
    Transcribe an audio file using OpenAI's Whisper API
    """
    try:
        # Verify file exists and is readable
        if not os.path.exists(audio_file_path):
            print(f"File not found: {audio_file_path}")
            return None
            
        # Try to load the audio file with pydub to verify it's valid
        try:
            # Get file extension
            file_ext = os.path.splitext(audio_file_path)[1].lower()
            
            # Determine format to pass to pydub
            format_map = {
                '.mp3': 'mp3',
                '.mp4': 'mp4',
                '.m4a': 'm4a',
                '.wav': 'wav',
                '.aac': 'aac',
                '.webm': 'webm',
                '.mpeg': 'mpeg',
                '.mpga': 'mp3',
                '.flac': 'flac',
                '.ogg': 'ogg',
                '.oga': 'ogg',
                '.opus': 'opus',
                '.amr': 'amr'
            }
            
            format_name = format_map.get(file_ext, 'mp3')
            audio = AudioSegment.from_file(audio_file_path, format=format_name)
            
            # Convert duration from milliseconds to minutes and seconds
            duration_seconds = round(len(audio) / 1000)  # Round to nearest second
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            
            print(f"Successfully loaded audio file: {os.path.basename(audio_file_path)}")
            print(f"Duration: {minutes}m {seconds}s")
            
        except Exception as e:
            print(f"Error loading audio file with pydub: {str(e)}")
            print("If the error is related to FFmpeg, make sure FFmpeg is installed on your system.")
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

def save_processed_transcript(transcript, source_filename):
    """
    Save transcript text to file in output folder
    Handles both text string responses and JSON dictionary responses
    """
    # Create output directory if it doesn't exist
    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename based on source audio file and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(source_filename))[0]
    txt_file = os.path.join(output_dir, f"{base_name}_extract_{timestamp}.txt")
    
    # Handle different types of transcript responses
    with open(txt_file, 'w', encoding='utf-8') as f:
        if isinstance(transcript, str):
            # Direct string response (when WHISPER_RESPONSE_FORMAT = "txt")
            f.write(transcript)
        elif isinstance(transcript, dict):
            # JSON response (when WHISPER_RESPONSE_FORMAT = "json" or "verbose_json")
            f.write(transcript.get('text', ''))
        else:
            # Handle OpenAI response object
            if hasattr(transcript, 'text'):
                f.write(transcript.text)
            else:
                f.write(str(transcript))
    
    print(f"\nTranscript saved to: {os.path.basename(txt_file)}")
    return txt_file

# Update main execution
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("data/original", exist_ok=True)
    os.makedirs("data/convert", exist_ok=True)
    os.makedirs("data/output", exist_ok=True)
    
    # Find all audio files in data/original folder
    audio_paths = get_audio_files_from_original()
    
    if not audio_paths:
        print("Error: No audio files found in the data/original folder")
        print("Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm, aac")
        exit(1)
    
    # Process each audio file
    for audio_path in audio_paths:
        print(f"Processing audio file: {os.path.basename(audio_path)}")
        
        # Step 1: Convert the file to OGG format
        ogg_file_path = convert_to_ogg(audio_path)
        if not ogg_file_path:
            print(f"Skipping transcription for {os.path.basename(audio_path)} due to conversion error")
            continue
        
        # Step 2: Check if the converted file is under the 25MB size limit
        if not check_file_size(ogg_file_path, max_size_mb=25):
            print(f"Skipping transcription for {os.path.basename(ogg_file_path)}: File too large")
            continue
        
        # Step 3: Get the transcription using the transcribe_audio function
        print(f"Transcribing: {os.path.basename(ogg_file_path)}")
        result = transcribe_audio(ogg_file_path)
        
        if result:
            # Save transcript to output folder
            txt_file = save_processed_transcript(result, audio_path)
            print(f"Transcription complete: {txt_file}")
        else:
            print(f"Transcription failed for {os.path.basename(ogg_file_path)}")
