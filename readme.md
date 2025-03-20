# Audio Transcription Tool

A tool that transcribes audio files using OpenAI's Whisper API, designed to work as a Mac Automation menu item.

## Features

- Converts various audo audio formats to OGG format to optimise to 25Mb API limit
- Verifies audio file validity before transcription
- Saves both converted files and transcriptions in the same directory as the source audio file
- Creates a transcription text file

## Prerequisites

- macOS
- Python 
- FFmpeg installed on your system
- OpenAI API key

## Setup

1. Clone the repo
2. Create and activate a virtual environment:
   ```bash
   # Create the virtual environment
   python -m venv venv
   
   # Activate it
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```
5. Make sure you have FFmpeg installed on your system (use `brew install ffmpeg` if needed) but outside the venv
6. Make the wrapper script executable:
   ```bash
   chmod +x transcribe_wrapper.sh
   ```

## Usage as Mac Automation Menu Item

1. Setting up the Automator Service:
   - Open Automator and create a new "Quick Action"
   - Set "Workflow receives" to "audio files" in "Finder"
   - Add a "Run Shell Script" action
   - Set "Pass input" to "as arguments"
   - Enter the full path to your script:
     ```bash
     /path/to/your/transcribe_wrapper.sh "$@"
     ```
   - Save the workflow with a name like "Transcribe Audio"

2. After setup, you can right-click on any audio file in Finder, select "Quick Actions", and choose "Transcribe Audio"

3. Alternatively, you can use the shell script directly by providing audio file(s) as arguments:
   ```bash
   ./transcribe_wrapper.sh path/to/your/audio/file.mp3
   ```

## How It Works

The tool follows these steps:
1. Receives audio files via command line arguments
2. Converts each audio file to OGG format with optimized settings for speech recognition (saved alongside original file)
3. Verifies the file size is under the 25MB API limit
4. Transcribes the audio using OpenAI's Whisper API
5. Saves the transcript in the same directory as the original audio file with "Transcription" appended to the filename

I'm a new programmer so feeback appreciated.

