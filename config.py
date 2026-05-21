"""
Jarvis — Konfiguration
Alle anpassbaren Konstanten für AudioRecorder und AIHandler.
"""
from pathlib import Path

# ── Audio ────────────────────────────────────────────────────────────────────
SAMPLERATE: int = 16000
MAX_DURATION: int = 30          # Maximale Aufnahmedauer in Sekunden
AUDIO_DIR: Path = Path("audio_recordings")
AUDIO_DIR.mkdir(exist_ok=True)

# ── Whisper (Speech-to-Text) ─────────────────────────────────────────────────
WHISPER_MODEL_SIZE: str = "small"   # tiny | base | small | medium | large

# ── Ollama / LLM ─────────────────────────────────────────────────────────────
OLLAMA_HOST: str  = "http://localhost:11434"
OLLAMA_MODEL: str = "qwen3.5:4b"   # z.B. "gemma4:e2b" oder "qwen3.5:4b"

# Token-Limit pro Modus — verhindert überlange Antworten und spart Inferenzzeit
LLM_MAX_TOKENS_EXECUTE: int   = 800   # Thinking + Script (Thinking-Tokens zählen mit)
LLM_MAX_TOKENS_SPEAK:   int   = 180
LLM_TEMPERATURE:        float = 0.1   # niedrig → deterministischer, schneller

# ── Thinking-Budget pro Modus (in der UI änderbar) ───────────────────────────
# None/""=AUS, "low", "medium", "high". Hartes Gesamt-Token-Limit bleibt
# LLM_MAX_TOKENS_* (Thinking + Antwort zusammen).
THINK_EFFORT_EXECUTE: str | None = "medium"
THINK_EFFORT_SPEAK:   str | None = None

# ── Ausführungsmodus Default (Änderungen in der UI möglich) ─────────────────────────────────────────────────────────
# "speak"   → Antworten werden laut vorgelesen
# "execute" → Antworten als AppleScript ausgeführt
EXECUTION_MODE: str = "execute"

# ── TTS (macOS say) ───────────────────────────────────────────────────────────
# Kein -v Flag → System-Standardstimme aus Systemeinstellungen wird verwendet.
