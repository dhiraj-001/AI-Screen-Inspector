#!/bin/bash
export LC_ALL="C.UTF-8"
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

# Set your Groq API Key here if it's not already in your environment
# export GROQ_API_KEY="your_api_key_here"

/usr/bin/python3 $HOME/.local/bin/ai_snipping_popup.py
