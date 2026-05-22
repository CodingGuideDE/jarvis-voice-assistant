"""
Jarvis — TTS
Satzweise Sprachausgabe über macOS 'say'. Sätze werden in eine Queue
gelegt und sequenziell abgespielt, sodass die Wiedergabe schon beginnt,
während das LLM noch weitere Sätze generiert.
"""
import queue
import subprocess
import threading
from typing import Callable, Optional


class SayStreamer:
    """Spielt Sätze sequenziell über macOS 'say' ab."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def speak_sentence(self, text: str) -> None:
        """Reiht einen Satz in die Wiedergabe-Queue ein."""
        text = text.strip()
        if not text:
            return
        self._ensure_worker()
        self._queue.put(text)

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._worker and self._worker.is_alive():
                return
            self._worker = threading.Thread(target=self._run, daemon=True)
            self._worker.start()

    def _run(self) -> None:
        while True:
            text = self._queue.get()
            try:
                # Blockierender Aufruf — garantiert Reihenfolge und keine
                # Überlappung. Die Wiedergabe startet trotzdem sofort, weil
                # der Worker parallel zum LLM-Stream läuft.
                subprocess.run(["say", text], check=False, timeout=120)
            except Exception as e:
                print(f"say fehlgeschlagen: {e}")


# ── Sentence-Emitter (puffert Token-Chunks, gibt komplette Sätze raus) ─────

_SENTENCE_END = ".!?…"


class SentenceEmitter:
    """Puffert eingehende Token-Stücke und ruft `on_sentence(satz)` auf,
    sobald eine Satz-Endinterpunktion gefolgt von Whitespace gesehen wird.

    Ein Mindestlängen-Filter verhindert, dass Abkürzungen wie 'z. B.' oder
    'Dr.' bereits als Satz gewertet werden.
    """

    MIN_LEN = 25  # Mindestzeichen, bevor ein Punkt als Satzende zählt

    def __init__(self, on_sentence: Callable[[str], None]) -> None:
        self._on_sentence = on_sentence
        self._buf: list[str] = []

    def feed(self, chunk: str) -> None:
        if not chunk:
            return
        self._buf.append(chunk)
        self._try_emit()

    def flush(self) -> None:
        """Restpuffer am Stream-Ende als (Teil-)Satz ausgeben."""
        rest = "".join(self._buf).strip()
        self._buf.clear()
        if rest:
            self._on_sentence(rest)

    def _try_emit(self) -> None:
        text = "".join(self._buf)
        start = 0
        for i, ch in enumerate(text):
            if ch in _SENTENCE_END and i + 1 < len(text) and text[i + 1].isspace():
                if (i + 1) - start >= self.MIN_LEN:
                    sentence = text[start:i + 1].strip()
                    if sentence:
                        self._on_sentence(sentence)
                    start = i + 2  # nach Punkt + Whitespace
        if start > 0:
            self._buf = [text[start:]]
