#!/bin/bash
export LC_ALL="C.UTF-8"
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

# Load secure API key config if it exists
CONFIG_FILE="$HOME/.config/ai-screen-inspector/env"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

/usr/bin/python3 $HOME/.local/bin/ai_snipping_popup.py
