#!/usr/bin/env python3
"""
AI Screen Inspector
-------------------
Capture a screen region → OCR → Groq LLM inference in a dark-mode popup.
"""

import sys
import os
import subprocess
import tempfile

# Must be set before any Qt import to suppress locale/xkbcommon warnings
os.environ.setdefault("LC_ALL", "C.UTF-8")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox,
    QDoubleSpinBox, QSpinBox
)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from groq import Groq

# ---------------------------------------------------------------------------
# API Key — prefer environment variable; never hard-code real keys in source.
# Set GROQ_API_KEY in ~/.bashrc, ~/.profile, or the wrapper script.
# ---------------------------------------------------------------------------
DEFAULT_GROQ_KEY = os.getenv("GROQ_API_KEY", "")

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
    stream_done    = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, instruction: str, text: str, model: str,
                 temperature: float, max_tokens: int):
        super().__init__()
        self.instruction = instruction
        self.text        = text
        self.model       = model
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self._cancelled  = False

    def cancel(self):
        """Signal the worker to stop consuming chunks."""
        self._cancelled = True

    def run(self):
        api_key = os.getenv("GROQ_API_KEY") or DEFAULT_GROQ_KEY
        if not api_key:
            self.error_occurred.emit(
                "Error: GROQ_API_KEY is not set.\n"
                "Add it to ~/.bashrc or export it in run-ai-snipper.sh"
            )
            return

        try:
            client = Groq(api_key=api_key)
            user_content = (
                f"{self.instruction}\n\n```\n{self.text}\n```"
                if self.instruction
                else f"```\n{self.text}\n```"
            )
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise, helpful assistant. "
                            "Directly answer, solve, or explain according to the "
                            "user's prompt without unnecessary conversational fluff."
                        ),
                    },
                    {"role": "user", "content": user_content},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            for chunk in completion:
                if self._cancelled:
                    break
                delta = chunk.choices[0].delta.content
                if delta:
                    self.chunk_received.emit(delta)
            self.stream_done.emit()
        except Exception as exc:
            self.error_occurred.emit(f"Groq API Error: {exc}")


class ScreenAIPopup(QWidget):
    def __init__(self, captured_text: str):
        super().__init__()
        self.captured_text      = captured_text
        self.full_response_text = ""
        self.worker: GroqStreamWorker | None = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("AI Screen Inspector")
        self.resize(740, 560)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog
        )
        self.setStyleSheet(POPUP_STYLESHEET)

        root = QVBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Parameter toolbar ──────────────────────────────────────────────
        param_row = QHBoxLayout()
        param_row.setSpacing(8)
        param_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ])
        param_row.addWidget(self.model_combo, stretch=2)

        param_row.addWidget(QLabel("Temp:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.5)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.3)
        param_row.addWidget(self.temp_spin, stretch=1)

        param_row.addWidget(QLabel("Tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(64, 8192)
        self.tokens_spin.setSingleStep(128)
        self.tokens_spin.setValue(1024)
        param_row.addWidget(self.tokens_spin, stretch=1)
        root.addLayout(param_row)

        # ── Prompt input ───────────────────────────────────────────────────
        root.addWidget(QLabel("Task / Prompt:"))
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(
            "Enter instructions and press Enter (e.g. 'Explain this error')..."
        )
        self.prompt_input.returnPressed.connect(self.ask_groq)
        root.addWidget(self.prompt_input)

        # ── Response area ──────────────────────────────────────────────────
        root.addWidget(QLabel("Response:"))
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setPlaceholderText(
            "Ready. Enter a prompt above and press Enter or click Query..."
        )
        root.addWidget(self.result_area)

        # ── Action buttons ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.ask_btn = QPushButton("Query (Enter)")
        self.ask_btn.setObjectName("queryBtn")
        self.ask_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ask_btn.clicked.connect(self.ask_groq)

        copy_btn = QPushButton("Copy (Ctrl+C)")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_result)

        close_btn = QPushButton("Close (Esc)")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)

        btn_row.addWidget(self.ask_btn)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        self.setLayout(root)
        QShortcut(QKeySequence("Escape"), self, self.close)
        self.prompt_input.setFocus()

    # ── Slots ──────────────────────────────────────────────────────────────

    def ask_groq(self):
        instruction = self.prompt_input.text().strip()

        # Guard: don't send if there's nothing to analyse
        if not self.captured_text:
            self.result_area.setPlainText("No captured text to analyse.")
            return

        # Cancel and clean up any in-flight worker before starting a new one
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait()

        self.ask_btn.setEnabled(False)
        self.ask_btn.setText("Streaming…")
        self.result_area.clear()
        self.full_response_text = ""

        self.worker = GroqStreamWorker(
            instruction,
            self.captured_text,
            self.model_combo.currentText(),
            float(self.temp_spin.value()),
            int(self.tokens_spin.value()),
        )
        self.worker.chunk_received.connect(self._append_chunk)
        self.worker.stream_done.connect(self._on_done)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _append_chunk(self, chunk: str):
        """Accumulate chunks; use plain insert for flicker-free live streaming."""
        self.full_response_text += chunk
        cursor = self.result_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.result_area.setTextCursor(cursor)
        sb = self.result_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_done(self):
        """Render final response as rich markdown once streaming completes."""
        self.result_area.setMarkdown(self.full_response_text)
        sb = self.result_area.verticalScrollBar()
        sb.setValue(sb.maximum())
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Query (Enter)")

    def _on_error(self, err: str):
        self.result_area.setPlainText(err)
        self.ask_btn.setEnabled(True)
        self.ask_btn.setText("Query (Enter)")

    def _copy_result(self):
        QApplication.clipboard().setText(self.result_area.toPlainText())

    def closeEvent(self, event):
        """Ensure background thread is stopped cleanly before closing."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait()
        super().closeEvent(event)


def main():
    # 1. Screen capture — keep the file handle properly closed before flameshot writes to it
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_f:
        img_path = img_f.name

    try:
        with open(img_path, "wb") as out_fh:
            res = subprocess.run(["flameshot", "gui", "-r"], stdout=out_fh)

        if res.returncode != 0 or os.path.getsize(img_path) == 0:
            return  # User cancelled or capture failed

        # 2. OCR — TemporaryDirectory avoids the deprecated/unsafe mktemp() race condition
        with tempfile.TemporaryDirectory() as tmp_dir:
            txt_prefix = os.path.join(tmp_dir, "ocr_out")
            subprocess.run(
                ["tesseract", img_path, txt_prefix, "-l", "eng", "--psm", "6"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            txt_file = txt_prefix + ".txt"
            if not os.path.exists(txt_file):
                subprocess.run(
                    ["notify-send", "AI Screen Inspector", "Tesseract produced no output."]
                )
                return

            with open(txt_file, "r", encoding="utf-8") as f:
                extracted = f.read().strip()
            # txt_file cleaned up automatically when TemporaryDirectory context exits

    finally:
        # Always remove the screenshot temp file, even if an exception occurred
        if os.path.exists(img_path):
            os.remove(img_path)

    if not extracted:
        subprocess.run(
            ["notify-send", "AI Screen Inspector",
             "No readable text detected in the selected area."]
        )
        return

    # 3. Launch UI
    app = QApplication(sys.argv)
    window = ScreenAIPopup(extracted)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()