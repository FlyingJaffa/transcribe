# Audio Transcription Tool

A simple tool to transcribe audio files using OpenAI's Whisper API and save the transcriptions in the `output` folder.

## Setup and usage

1. Install dependencies.
2. Create a `.env` file with the following variable: OPENAI_API_KEY=
3. Place your audio files in the `data` folder
4. Run the script `main.py`
5. Look in the `output` folder for the transcriptions
6. Upon running the script, the data/chunks and output/chunks folders will be wiped, however the original audio in /data and the transcriptions in /output will be kept.

The tool will:
1. Find the audio files in the `data` folder
2. Chunk them into 20mb pieces (API limit is around 25mb) and save in the `data/chunks` folder
3. Transcribe it using Whisper API and save the transcriptions in the `output/chunks` folder
4. Reassemble the transcriptions into their original file and save in the `output` folder

