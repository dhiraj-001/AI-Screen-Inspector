#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║       AI Screen Inspector — Installer        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── Step 1: Local bin directory ────────────────────────────────────────────
echo "[1/4] Creating ~/.local/bin if it doesn't exist..."
mkdir -p ~/.local/bin

# ── Step 2: Copy files ─────────────────────────────────────────────────────
echo "[2/4] Installing scripts..."
cp script.py ~/.local/bin/ai_snipping_popup.py
cp run-ai-snipper.sh ~/.local/bin/run-ai-snipper.sh
chmod +x ~/.local/bin/ai_snipping_popup.py
chmod +x ~/.local/bin/run-ai-snipper.sh
echo "      ✓ Scripts installed to ~/.local/bin/"

# ── Step 3: Groq API Key setup ─────────────────────────────────────────────
echo ""
echo "[3/4] Groq API Key Setup"
echo "      You need a key from https://console.groq.com/keys"
echo ""

# Check if already set in the environment
if [ -n "$GROQ_API_KEY" ]; then
    echo "      ✓ GROQ_API_KEY is already set in the current session."
    USE_EXISTING="y"
    read -r -p "      Use the existing key (recommended)? [Y/n]: " USE_EXISTING
    USE_EXISTING="${USE_EXISTING:-y}"
else
    USE_EXISTING="n"
fi

if [[ "$USE_EXISTING" =~ ^[Yy]$ ]] && [ -n "$GROQ_API_KEY" ]; then
    API_KEY="$GROQ_API_KEY"
else
    read -r -p "      Paste your Groq API key: " API_KEY
    API_KEY="${API_KEY//[[:space:]]/}"  # strip accidental whitespace
fi

if [ -z "$API_KEY" ]; then
    echo ""
    echo "  ⚠  No API key provided. Skipping — you must set GROQ_API_KEY manually."
    echo "     Add the following line to your ~/.bashrc or ~/.profile:"
    echo "       export GROQ_API_KEY=\"your_key_here\""
else
    # Persist to ~/.bashrc (avoids duplicates)
    BASHRC="$HOME/.bashrc"
    if grep -q "GROQ_API_KEY" "$BASHRC" 2>/dev/null; then
        # Update the existing line in place
        sed -i "s|^export GROQ_API_KEY=.*|export GROQ_API_KEY=\"$API_KEY\"|" "$BASHRC"
        echo "      ✓ Updated GROQ_API_KEY in $BASHRC"
    else
        echo "" >> "$BASHRC"
        echo "# Groq API key — added by AI Screen Inspector installer" >> "$BASHRC"
        echo "export GROQ_API_KEY=\"$API_KEY\"" >> "$BASHRC"
        echo "      ✓ Added GROQ_API_KEY to $BASHRC"
    fi

    # Also inject into the wrapper script so KDE global shortcuts pick it up
    # (KDE's hotkey daemon doesn't inherit ~/.bashrc)
    WRAPPER="$HOME/.local/bin/run-ai-snipper.sh"
    if grep -q "GROQ_API_KEY" "$WRAPPER" 2>/dev/null; then
        sed -i "s|^export GROQ_API_KEY=.*|export GROQ_API_KEY=\"$API_KEY\"|" "$WRAPPER"
    else
        sed -i "2a export GROQ_API_KEY=\"$API_KEY\"" "$WRAPPER"
    fi
    echo "      ✓ Injected GROQ_API_KEY into run-ai-snipper.sh (for KDE hotkey daemon)"
fi

# ── Step 4: Done ───────────────────────────────────────────────────────────
echo ""
echo "[4/4] Installation complete!"
echo ""
echo "  Next step — set up your global hotkey in KDE:"
echo "    System Settings → Shortcuts → Add New → Command or URL"
echo "    Command : $HOME/.local/bin/run-ai-snipper.sh"
echo "    Shortcut: e.g. Ctrl+Alt+A"
echo ""
echo "  To apply the API key in your current terminal session now, run:"
echo "    source ~/.bashrc"
echo ""
