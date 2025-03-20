# Whisper API settings
WHISPER_MODEL = "whisper-1"
WHISPER_TEMPERATURE = 0
WHISPER_LANGUAGE = 'EN'  # Set to None for auto-detection, or use language code like 'fr', 'en', etc.

# Prompt for transcription
WHISPER_PROMPT = """
You are transcribing an audio file. Please:
1. Format in accodance with the speaker's pauses, breaks and other non-speech sounds.
2. Do not add any additional text or commentary.
"""

# Response format
WHISPER_RESPONSE_FORMAT = "text" 