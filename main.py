#!/usr/bin/env python3
"""
Audio Transcription Tool
------------------------
This script transcribes audio files using OpenAI's Whisper API.
It processes files provided as command-line arguments.

Author: flyingjaffacake
License: MIT
"""

import openai
import os
import subprocess
import sys
from dotenv import load_dotenv
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

# Initialize OpenAI client
client = openai.OpenAI(api_key=api_key)

def convert_to_ogg(audio_file_path):
    """
    Convert an audio file to OGG format using FFmpeg.
    
    Args:
        audio_file_path (str): Path to the source audio file
        
    Returns:
        str or None: Path to the converted file, or None if conversion failed
    """
    # Get the directory of the source file
    source_dir = os.path.dirname(audio_file_path)
    
    # Generate output file path
    base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    
    # Add timestamp to filename to avoid conflicts
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    output_path = os.path.join(source_dir, f"{base_name}_converted_{timestamp}.ogg")
    
    # Construct FFmpeg command with optimized settings for speech recognition
    ffmpeg_cmd = [
        "ffmpeg", 
        "-i", audio_file_path,   # Input file
        "-vn",                   # Disable video (audio only)
        "-map_metadata", "-1",   # Remove metadata
        "-ac", "1",              # Convert to mono
        "-c:a", "libopus",       # Use Opus codec (good for speech)
        "-b:a", "12k",           # Set bitrate (12kbps is suitable for speech)
        "-application", "voip",  # Optimize for voice
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
    Check if a file is under the specified size limit.
    
    Args:
        file_path (str): Path to the file to check
        max_size_mb (int): Maximum allowed size in MB
        
    Returns:
        bool: True if file is under the limit, False otherwise
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

def transcribe_audio(audio_file_path):
    """
    Transcribe an audio file using OpenAI's Whisper API.
    
    Args:
        audio_file_path (str): Path to the audio file to transcribe
        
    Returns:
        object or None: Transcription result or None if failed
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
    Save transcript text to file in the same directory as the source audio file.
    If a file with the same name already exists, append a sequential number.
    
    Args:
        transcript (str, dict, or object): The transcription result
        source_filename (str): Original audio filename
        
    Returns:
        str: Path to the saved transcript file
    """
    # Get the directory of the source file
    source_dir = os.path.dirname(source_filename)
    
    # Create base filename
    base_name = os.path.splitext(os.path.basename(source_filename))[0]
    base_txt_file = os.path.join(source_dir, f"{base_name} Transcription.txt")
    
    # Check if file already exists, if so, append a sequential number
    txt_file = base_txt_file
    counter = 2
    
    while os.path.exists(txt_file):
        txt_file = os.path.join(source_dir, f"{base_name} Transcription {counter}.txt")
        counter += 1
    
    # Handle different types of transcript responses
    with open(txt_file, 'w', encoding='utf-8') as f:
        if isinstance(transcript, str):
            # Direct string response (when WHISPER_RESPONSE_FORMAT = "text")
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
    
    print(f"\nTranscript saved to: {txt_file}")
    return txt_file

def process_single_file(audio_path):
    """
    Process a single audio file and generate transcript.
    
    Args:
        audio_path (str): Path to the audio file to process
        
    Returns:
        str or None: Path to the transcript file or None if failed
    """
    print(f"Processing audio file: {os.path.basename(audio_path)}")
    
    # Step 1: Convert the file to OGG format
    ogg_file_path = convert_to_ogg(audio_path)
    if not ogg_file_path:
        print(f"Skipping transcription for {os.path.basename(audio_path)} due to conversion error")
        return None
    
    # Step 2: Check if the converted file is under the 25MB size limit
    if not check_file_size(ogg_file_path, max_size_mb=25):
        print(f"Skipping transcription for {os.path.basename(ogg_file_path)}: File too large")
        return None
    
    # Step 3: Get the transcription using the transcribe_audio function
    print(f"Transcribing: {os.path.basename(ogg_file_path)}")
    result = transcribe_audio(ogg_file_path)
    
    if result:
        # Save transcript alongside the original file
        txt_file = save_processed_transcript(result, audio_path)
        print(f"Transcription complete: {txt_file}")
        return txt_file
    else:
        print(f"Transcription failed for {os.path.basename(ogg_file_path)}")
        return None

def main():
    """Main function to process files provided as command-line arguments"""
    # Check if files were provided via command line arguments
    if len(sys.argv) <= 1:
        print("Error: No files provided. Please specify one or more audio files to transcribe.")
        print("Usage: python main.py audio_file1.mp3 [audio_file2.mp3 ...]")
        exit(1)
    
    # Process files provided as command-line arguments
    for file_path in sys.argv[1:]:
        if os.path.isfile(file_path):
            process_single_file(file_path)
        else:
            print(f"Error: File not found: {file_path}")

if __name__ == "__main__":
    main()
