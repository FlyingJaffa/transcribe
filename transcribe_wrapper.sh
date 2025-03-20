#!/bin/bash

# =========================================================================
# transcribe_wrapper.sh - Wrapper script for audio transcription using OpenAI
# =========================================================================

# This script provides a convenient way to run the Python transcription script
# from Automator or the command line by handling environment setup and dependencies

echo "==== Starting Audio Transcription Process ===="

# Get the directory of this script to find related files
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory: $SCRIPT_DIR"

# ---- Find and configure FFmpeg ----
FFMPEG_PATH=$(which ffmpeg)
if [ -z "$FFMPEG_PATH" ]; then
    # Try common installation locations if 'which' doesn't find it
    if [ -f "/usr/local/bin/ffmpeg" ]; then
        FFMPEG_PATH="/usr/local/bin/ffmpeg"
    elif [ -f "/opt/homebrew/bin/ffmpeg" ]; then
        FFMPEG_PATH="/opt/homebrew/bin/ffmpeg"
    else
        echo "ERROR: Cannot find ffmpeg. Please install it using 'brew install ffmpeg' or specify its path."
        exit 1
    fi
fi

echo "Found ffmpeg at: $FFMPEG_PATH"
export PATH="$(dirname $FFMPEG_PATH):$PATH"
echo "Updated PATH: $PATH"

# ---- Load API key from .env file ----
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "Loading API key from .env file..."
    # Extract OPENAI_API_KEY from .env file and export it
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
    
    # Verify API key was loaded (without showing the actual key)
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "API key loaded successfully"
    else
        echo "ERROR: OPENAI_API_KEY not found in .env file"
        exit 1
    fi
else
    echo "ERROR: .env file not found at $SCRIPT_DIR/.env"
    echo "Please create this file with your OpenAI API key: OPENAI_API_KEY=your_key_here"
    exit 1
fi

# ---- Activate Python virtual environment ----
VENV_PATH="$SCRIPT_DIR/venv/bin/activate"
ABSOLUTE_VENV_PATH="/Users/flyingjaffaake/cursorfiles/Transcribe/venv/bin/activate"

if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH"
    echo "Virtual environment activated successfully"
else
    echo "Warning: Virtual environment not found at $VENV_PATH"
    # Fall back to using the full path if the relative path doesn't work
    if [ -f "$ABSOLUTE_VENV_PATH" ]; then
        echo "Found virtual environment at absolute path, activating..."
        source "$ABSOLUTE_VENV_PATH"
        echo "Virtual environment activated successfully"
    else
        echo "ERROR: Could not find virtual environment. Transcription may fail."
        echo "Try creating a virtual environment with: python -m venv venv"
        echo "Then install dependencies with: venv/bin/pip install -r requirements.txt"
    fi
fi

# ---- Set the working directory ----
cd "$SCRIPT_DIR"
echo "Working directory set to: $SCRIPT_DIR"

# ---- Run the Python script with the provided arguments ----
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"
SCRIPT_PATH="$SCRIPT_DIR/main.py"

echo "Running Python script with arguments: $@"
if [ -f "$PYTHON_PATH" ]; then
    "$PYTHON_PATH" "$SCRIPT_PATH" "$@"
    RESULT=$?
else
    echo "Warning: Could not find Python executable at $PYTHON_PATH"
    echo "Trying to use system Python instead..."
    python3 "$SCRIPT_PATH" "$@"
    RESULT=$?
fi

# ---- Report completion ----
if [ $RESULT -eq 0 ]; then
    echo "==== Audio Transcription Process Completed Successfully ===="
else
    echo "==== Audio Transcription Process Completed With Errors (Code: $RESULT) ===="
fi

exit $RESULT