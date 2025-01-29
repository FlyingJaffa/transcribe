# Whisper API settings
WHISPER_MODEL = "whisper-1"
WHISPER_TEMPERATURE = 0
WHISPER_LANGUAGE = None  # Set to None for auto-detection, or use language code like 'fr', 'en', etc.

# Prompt for transcription
WHISPER_PROMPT = """
You are transcribing an audio file. Please:
1. Maintain all original text in its original language
2. Include speaker changes and pauses
3. Preserve any technical terms or proper nouns exactly as spoken
"""

# Response format
WHISPER_RESPONSE_FORMAT = "json" 