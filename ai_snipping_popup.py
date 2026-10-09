#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile

# Prevent locale/xkbcommon parsing warnings in KDE Plasma
os.environ.setdefault("LC_ALL", "C.UTF-8")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
    QDoubleSpinBox, QSpinBox
)
from PyQt6.QtGui import QKeySequence, QTextCursor, QShortcut
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from groq import Groq

# Fallback API key if not loaded from terminal session
DEFAULT_GROQ_KEY = os.getenv("GROQ_API_KEY", "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")

# Modern dark-mode styling for KDE Plasma
POPUP_STYLESHEET = """
QWidget {
    background-color: #1e1e24;
    color: #eff0f1;
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
}
QLabel {
    color: #a0a6ac;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #2b2d35;
    border: 1px solid #3d414d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
    selection-background-color: #3daee9;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #3daee9;
    background-color: #31343e;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QTextEdit {
    background-color: #24262e;
    border: 1px solid #363945;
    border-radius: 8px;
    padding: 12px;
    line-height: 1.5;
    selection-background-color: #3daee9;
}
QPushButton {
    background-color: #2b2d35;
    border: 1px solid #3d414d;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    color: #eff0f1;
}
QPushButton:hover {
    background-color: #383b46;
    border: 1px solid #4e5362;
}
QPushButton#queryBtn {
    background-color: #287299;
    border: 1px solid #3daee9;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#queryBtn:hover {
    background-color: #3188b6;
}
QPushButton#queryBtn:disabled {
    background-color: #2b3b44;
    border-color: #384b55;
    color: #728490;
}
"""

class GroqStreamWorker(QThread):
    chunk_received = pyqtSignal(str)
    stream_done = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt_instruction, captured_text, model, temperature, max_tokens):
        super().__init__()
        self.instruction = prompt_instruction
        self.text = captured_text
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def run(self):
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY
        if not api_key:
            self.error_occurred.emit("Error: GROQ_API_KEY is not configured.")
            return

        try:
            client = Groq(api_key=api_key)
            user_content = f"{self.instruction}\n\n```\n{self.text}\n```" if self.instruction else f"```\n{self.text}\n```"

            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a concise, helpful assistant. Directly answer, solve, or explain according to the user's prompt without unnecessary conversational fluff."
                    },
                    {
                        "role": "user",
                        "content": user_content
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )

            for chunk in completion:
                delta = chunk.choices[0].delta.content
                if delta:
                    self.chunk_received.emit(delta)

            self.stream_done.emit()

        except Exception as e:
            self.error_occurred.emit(f"Groq API Error: {str(e)}")


class ScreenAIPopup(QWidget):
    def __init__(self, captured_text):
        super().__init__()
        self.captured_text = captured_text
        self.full_response_text = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AI Screen Inspector")
        self.resize(740, 560)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setStyleSheet(POPUP_STYLESHEET)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 1. Parameter Toolbar
        param_layout = QHBoxLayout()
        param_layout.setSpacing(8)

        param_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ])
        param_layout.addWidget(self.model_combo, stretch=2)

        param_layout.addWidget(QLabel("Temp:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.5)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.3)
        param_layout.addWidget(self.temp_spin, stretch=1)

        param_layout.addWidget(QLabel("Tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(64, 8192)
        self.tokens_spin.setSingleStep(128)
        self.tokens_spin.setValue(1024)
        param_layout.addWidget(self.tokens_spin, stretch=1)

        layout.addLayout(param_layout)

        # 2. Prompt Input (Blank by default, ready for custom query)
        layout.addWidget(QLabel("Task / Prompt:"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setText("")
        self.prompt_input.setPlaceholderText("Enter prompt instructions here and press Enter...")
        self.prompt_input.returnPressed.connect(self.ask_groq)
        layout.addWidget(self.prompt_input)

        # 3. Response Display Area
        layout.addWidget(QLabel("Response:"))
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setPlaceholderText("Ready. Enter instructions above and press Enter or Query...")
        layout.addWidget(self.result_area)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.ask_btn = QPushButton("Query (Enter)")
        self.ask_btn.setObjectName("queryBtn")
        self.ask_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ask_btn.clicked.connect(self.ask_groq)

        copy_btn = QPushButton("Copy (Ctrl+C)")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self.copy_result)

        close_btn = QPushButton("Close (Esc)")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self.ask_btn)
        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Close on Escape
        QShortcut(QKeySequence("Escape"), self, self.close)

        # Focus directly on the input box
        self.prompt_input.setFocus()

    def ask_groq(self):
        instruction = self.prompt_input.text().strip()
        selected_model = self.model_combo.currentText()
        temperature = float(self.temp_spin.value())
        max_tokens = int(self.tokens_spin.value())

        self.ask_btn.setEnabled(False)
        self.ask_btn.setText("Streaming...")
        self.result_area.clear()
        self.full_response_text = ""
        
        self.worker = GroqStreamWorker(
            instruction,
            self.captured_text,
            selected_model,
            temperature,
            max_tokens
        )
        self.worker.chunk_received.connect(self.append_chunk)
        self.worker.stream_done.connect(self.on_done)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def append_chunk(self, chunk):
        self.full_response_text += chunk
        self.result_area.setMarkdown(self.full_response_text)
        sb = self.result_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_done(self):
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Query (Enter)")

    def on_error(self, err):
        self.result_area.setPlainText(err)
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Query (Enter)")

    def copy_result(self):
        QApplication.clipboard().setText(self.result_area.toPlainText())


def main():
    # 1. Screen capture using Flameshot
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_f:
        img_path = img_f.name

    res = subprocess.run(["flameshot", "gui", "-r"], stdout=open(img_path, "wb"))
    if res.returncode != 0 or os.path.getsize(img_path) == 0:
        if os.path.exists(img_path):
            os.remove(img_path)
        return

    # 2. Extract text via Tesseract OCR
    txt_prefix = tempfile.mktemp()
    subprocess.run(
        ["tesseract", img_path, txt_prefix, "-l", "eng", "--psm", "6"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    if os.path.exists(img_path):
        os.remove(img_path)

    txt_file = txt_prefix + ".txt"
    if not os.path.exists(txt_file):
        return

    with open(txt_file, "r") as f:
        extracted = f.read().strip()
    os.remove(txt_file)

    if not extracted:
        subprocess.run(["notify-send", "OCR", "No readable text detected in the selected area."])
        return

    # 3. Launch the Qt UI
    app = QApplication(sys.argv)
    window = ScreenAIPopup(extracted)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
