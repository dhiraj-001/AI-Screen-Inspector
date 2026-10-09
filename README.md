# AI Screen Inspector

AI Screen Inspector is a Linux desktop utility that allows you to quickly capture a region of your screen, extract the text using OCR, and send it to an AI model (via Groq Cloud API) with a custom prompt. It features a modern dark-mode GUI built with PyQt6.

## System Architecture Overview

```text
[ Global Shortcut / Hotkey ]
            │
            ▼
[ Bash Wrapper: run-ai-snipper.sh ]
            │
            ▼
[ Python Engine: ai_snipping_popup.py ]
   ├── 1. Screen Capture (Flameshot / Spectacle)
   ├── 2. Local Text Extraction (Tesseract OCR)
   ├── 3. Custom Prompt & Parameters UI (PyQt6)
   └── 4. Streaming Inference (Groq Cloud API)
```

## Dependencies Installation

Open your terminal and install the required OCR engine, screenshot tool, Qt libraries, and the Groq Python SDK:

```bash
# Update repositories
sudo apt update

# Install system utilities, Qt6, and OCR packages
sudo apt install tesseract-ocr tesseract-ocr-eng flameshot python3-pyqt6 python3-pip -y

# Install the Groq API client
python3 -m pip install groq --break-system-packages
```

## Installation

You can run the provided `install.sh` script, or manually link/copy the files to your `~/.local/bin` directory.

### Quick Setup

Make the installation script executable and run it:

```bash
chmod +x install.sh
./install.sh
```

### Manual Setup

1. Create the directory for your local user binaries:

```bash
mkdir -p ~/.local/bin
```

2. Copy the Python script and shell wrapper:

```bash
cp ai_snipping_popup.py ~/.local/bin/
cp run-ai-snipper.sh ~/.local/bin/
```

3. Make them executable:

```bash
chmod +x ~/.local/bin/ai_snipping_popup.py
chmod +x ~/.local/bin/run-ai-snipper.sh
```

## Setting Up the Global Hotkey in Kubuntu (KDE Plasma)

This is the **verified working method** on Kubuntu/KDE Plasma. Follow all 3 steps in order.

---

### Step 1 — Verify the Wrapper Script

Make sure the wrapper exists and is executable:

```bash
chmod +x ~/.local/bin/run-ai-snipper.sh
```

Confirm it works from your terminal first:

```bash
/home/dhiraj/.local/bin/run-ai-snipper.sh
```

Flameshot's selection overlay should appear. If it does, proceed to Step 2.

> [!TIP]
> If Flameshot doesn't appear, check that it's installed: `which flameshot`
> If the Python script errors, run it directly: `/usr/bin/python3 ~/.local/bin/ai_snipping_popup.py`

---

### Step 2 — Test via KRunner (Important)

Before binding to a hotkey, test that **KDE itself** can execute the script:

1. Press **`Alt + Space`** to open KRunner.
2. Type the full path:
   ```
   /home/dhiraj/.local/bin/run-ai-snipper.sh
   ```
3. Press **Enter**.

Flameshot should appear. If it does, KDE can run the script — proceed to Step 3.

> [!NOTE]
> This step confirms whether KDE's execution environment has the required `PATH` and permissions.
> If it fails here but works in terminal, check that `GROQ_API_KEY` is exported in `run-ai-snipper.sh` (not just `.bashrc`).

---

### Step 3 — Bind to a Global Shortcut

1. Open **System Settings** → search **"Custom Shortcuts"** → open it.
2. **Delete any previous AI Snip entries** to avoid conflicts.
3. Click **Add New → Global Shortcut → Command/URL**.
4. Configure the entry:
   - **Name**: `AI Snip & Inspect`
   - **Command/URL**: `/home/dhiraj/.local/bin/run-ai-snipper.sh`
5. Click the **Shortcut** button and assign a combo — recommended:
   - `Ctrl + Alt + A` or `Meta + Alt + S`
   - ⚠️ Avoid `Meta+Shift+S` and `Print` — they are bound to KDE Spectacle by default.
6. Click **Apply**.

> [!CAUTION]
> **Do NOT paste the path** — KDE's dialog can silently include a trailing newline, causing
> `Could not find the program '/home/...`. **Type the path manually** in the Command/URL field.

## How to Use & Workflow

1. **Trigger**: Press your shortcut (e.g., `Ctrl + Alt + A`).
2. **Select**: Drag a selection rectangle over any code, terminal trace, error message, or document.
3. **Prompt**: The dark-mode inspector popup opens immediately on top with the cursor focused in the prompt field.
4. **Tune & Query**:
   - Adjust the model, temperature, or max token limit if needed.
   - Type your task (e.g., "Explain this error", "Find bug", "Convert to Python") and hit Enter.
5. **Dismiss**: Click **Copy** to grab the response, or hit `Esc` to immediately close the popup.

## Configuration (API Key)

Get a free API key at: **https://console.groq.com/keys**

> [!WARNING]
> You must set the key in **two places**. The KDE hotkey daemon runs in a bare session
> that does **not** source `~/.bashrc` — so setting it only there will cause silent failures
> when triggered via the hotkey.

### 1. In `~/.bashrc` (for terminal sessions)

```bash
echo 'export GROQ_API_KEY="gsk_your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### 2. In `run-ai-snipper.sh` (required for KDE hotkey)

Open the wrapper:

```bash
nano ~/.local/bin/run-ai-snipper.sh
```

Add your key so the file looks like this:

```bash
#!/bin/bash
export LC_ALL="C.UTF-8"
export GROQ_API_KEY="gsk_your_key_here"
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin:$PATH"

/usr/bin/python3 /home/dhiraj/.local/bin/ai_snipping_popup.py
```

Save (`Ctrl+O`, Enter, `Ctrl+X`).

### Easiest way: run the installer

The `install.sh` script handles both locations automatically:

```bash
chmod +x install.sh && ./install.sh
```
