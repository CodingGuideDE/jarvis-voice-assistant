"""
Jarvis — AudioRecorder
Verwaltet Audioaufnahme, Hotkey-Listener, Whisper-Transkription
und delegiert KI-Verarbeitung an AIHandler.
"""
import atexit
import platform
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import resample_poly
from math import gcd
import sounddevice as sd

import config
from ai_handler import AIHandler

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("OpenAI Whisper nicht installiert. Installiere: pip install openai-whisper")

try:
    import importlib.util
    HOTKEY_METHOD = "pynput" if importlib.util.find_spec("pynput") else None
    if not HOTKEY_METHOD:
        print("pynput nicht installiert. Installiere: pip install pynput")
except Exception:
    HOTKEY_METHOD = None

# Wird als isolierter Subprocess gestartet — pynput-SIGTRAP trifft nur den Kindprozess.
_HOTKEY_SCRIPT = """\
import sys, signal, platform

if platform.system() == "Darwin":
    signal.signal(signal.SIGTRAP, signal.SIG_DFL)

try:
    from pynput import keyboard as kb
except Exception as e:
    sys.stdout.write(f"ERROR:{e}\\n")
    sys.stdout.flush()
    sys.exit(1)

cmd_pressed = False
opt_pressed = False
active = False

def on_press(key):
    global cmd_pressed, opt_pressed, active
    try:
        if key == kb.Key.cmd:   cmd_pressed = True
        elif key == kb.Key.alt: opt_pressed = True
        if cmd_pressed and opt_pressed and not active:
            active = True
            sys.stdout.write("START\\n")
            sys.stdout.flush()
    except Exception:
        pass

def on_release(key):
    global cmd_pressed, opt_pressed, active
    try:
        if key == kb.Key.cmd:   cmd_pressed = False
        elif key == kb.Key.alt: opt_pressed = False
        if active and not (cmd_pressed and opt_pressed):
            active = False
            sys.stdout.write("STOP\\n")
            sys.stdout.flush()
    except Exception:
        pass

try:
    with kb.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
except Exception as e:
    sys.stdout.write(f"ERROR:{e}\\n")
    sys.stdout.flush()
    sys.exit(1)
"""


def _get_input_samplerate() -> int:
    """Gibt die native Sample-Rate des Standard-Eingabegeräts zurück.

    macOS-Geräte laufen meist auf 44100 oder 48000 Hz — nicht auf den von
    Whisper erwarteten 16000 Hz. PortAudio befüllt den Buffer mit NaN wenn
    die angeforderte Rate nicht nativ unterstützt wird.
    """
    try:
        return int(sd.query_devices(kind='input')['default_samplerate'])
    except Exception:
        return 44100


def _trim_silence(audio: np.ndarray, threshold: float = 1e-4, chunk: int = 1600) -> np.ndarray:
    """Entfernt trailing Stille aus einem voralloziertem sd.rec()-Puffer.

    sd.rec() alloziert immer MAX_DURATION Sekunden. Nur der tatsächlich
    bespielte Teil wird zurückgegeben, damit Whisper keine überschüssige
    Stille verarbeiten muss.
    """
    flat = audio.flatten()
    for i in range(len(flat), 0, -chunk):
        if np.sqrt(np.mean(flat[max(0, i - chunk):i] ** 2)) > threshold:
            return flat[:i]
    return flat


def check_accessibility_permission() -> bool:
    """Prüft Accessibility-Berechtigung für globales Keyboard-Monitoring."""
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process'],
            capture_output=True, timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


class AudioRecorder:
    """Kernklasse: nimmt Audio auf, transkribiert es und delegiert die Antwort."""

    def __init__(self):
        self.is_recording: bool = False
        self.audio_data: np.ndarray | list = []
        self.audio_queue: queue.Queue = queue.Queue()
        self.hotkey_proc: Optional[subprocess.Popen] = None
        self.hotkey_active: bool = False
        self.whisper_model = None
        self.models_loading: bool = False
        self.models_ready: bool = False
        self.on_hotkey_dead_callback: Optional[Callable] = None
        self.on_transcription: Optional[Callable[[str], None]] = None
        self._recording_done = threading.Event()

        self._ai = AIHandler(get_mode=lambda: config.EXECUTION_MODE)

        self._load_models_async()

    # ── Model Loading ────────────────────────────────────────────────────────

    def _load_models_async(self) -> None:
        self.models_loading = True
        threading.Thread(target=self._load_models, daemon=True).start()

    def _load_models(self) -> None:
        try:
            print("\nLade Modelle im Hintergrund...")

            if WHISPER_AVAILABLE:
                try:
                    print(f"   Lade Whisper ({config.WHISPER_MODEL_SIZE})...")
                    # device="cpu": MPS-Gewichte werden beim Laden in fp16
                    # konvertiert — das produziert NaN-Logits unabhängig vom
                    # fp16-Flag im transcribe()-Aufruf. CPU läuft stabil in fp32.
                    self.whisper_model = whisper.load_model(
                        config.WHISPER_MODEL_SIZE, device="cpu"
                    )
                    print("   Whisper geladen (CPU, fp32)")
                except Exception as e:
                    print(f"   Fehler beim Laden von Whisper: {e}")
                    self.whisper_model = None

            self._ai.connect()

            self.models_ready = True
            print("Alle Modelle bereit\n")
        except Exception as e:
            print(f"Fehler beim Laden der Modelle: {e}")
        finally:
            self.models_loading = False

    # ── Hotkey Listener ──────────────────────────────────────────────────────

    def start_hotkey_listener(self) -> None:
        if not HOTKEY_METHOD:
            print("Hotkey-Bibliothek (pynput) nicht installiert!")
            return

        if platform.system() == "Darwin" and not check_accessibility_permission():
            print("Keine Accessibility-Berechtigung erkannt!")
            print("  Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen")
            subprocess.run(
                ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
                check=False,
            )
            return

        try:
            print("Starte Hotkey-Listener (CMD + OPTION)...")
            self.hotkey_proc = subprocess.Popen(
                [sys.executable, "-c", _HOTKEY_SCRIPT],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            atexit.register(self.stop_hotkey_listener)
            threading.Thread(target=self._read_hotkey_events, daemon=True).start()
            print("Hotkey-Listener gestartet")
        except Exception as e:
            print(f"Fehler beim Starten des Hotkey-Listeners: {e}")
            self.hotkey_proc = None

    def _read_hotkey_events(self) -> None:
        MAX_RESTARTS = 3
        restarts = 0
        while restarts <= MAX_RESTARTS:
            try:
                for line in self.hotkey_proc.stdout:
                    line = line.strip()
                    if line == "START":
                        self.start_recording()
                    elif line == "STOP":
                        self.stop_recording()
                    elif line.startswith("ERROR:"):
                        print(f"Hotkey-Subprocess Fehler: {line[6:]}")
            except Exception:
                pass

            if self.hotkey_proc is None:
                break
            exit_code = self.hotkey_proc.poll()
            if exit_code == 0:
                break

            restarts += 1
            if restarts > MAX_RESTARTS:
                print(f"Hotkey-Subprocess {MAX_RESTARTS}x abgestürzt — gebe auf.")
                self._notify_hotkey_dead()
                break

            print(f"Hotkey-Subprocess beendet (Code {exit_code}), Neustart {restarts}/{MAX_RESTARTS}...")
            time.sleep(1)
            try:
                self.hotkey_proc = subprocess.Popen(
                    [sys.executable, "-c", _HOTKEY_SCRIPT],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                )
            except Exception as e:
                print(f"Neustart fehlgeschlagen: {e}")
                self._notify_hotkey_dead()
                break

    def _notify_hotkey_dead(self) -> None:
        print("Hotkey-Listener permanent ausgefallen.")
        if self.on_hotkey_dead_callback:
            self.on_hotkey_dead_callback()

    def stop_hotkey_listener(self) -> None:
        proc, self.hotkey_proc = self.hotkey_proc, None
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                pass

    # ── Recording ────────────────────────────────────────────────────────────

    def start_recording(self) -> None:
        if self.is_recording:
            return
        self._recording_done.clear()
        self.is_recording = True
        self.hotkey_active = True
        self.audio_data = []
        print("\nAudioaufnahme gestartet...")
        threading.Thread(target=self._record_audio, daemon=True).start()

    def _record_audio(self) -> None:
        try:
            print("   Starte Audio-Recording...")
            native_sr = _get_input_samplerate()
            print(f"   Gerät-Sample-Rate: {native_sr} Hz")
            chunks: list[np.ndarray] = []

            def _cb(indata: np.ndarray, frames: int, time_info, status) -> None:
                chunk = indata[:, 0].copy()
                # NaN direkt im Callback bereinigen — kein globaler sd-Zustand nötig
                if not np.isfinite(chunk).all():
                    chunk = np.nan_to_num(chunk, nan=0.0)
                chunks.append(chunk)

            with sd.InputStream(samplerate=native_sr, channels=1,
                                dtype="float32", callback=_cb, blocksize=4096):
                while self.is_recording:
                    time.sleep(0.05)

            if chunks:
                self.audio_data = np.concatenate(chunks)
                self._native_sr = native_sr
                print("   Audio-Recording abgeschlossen")
            else:
                self.audio_data = np.array([])
        except Exception as e:
            print(f"   Fehler bei Audioaufnahme: {e}")
            self.audio_data = np.array([])
        finally:
            self._recording_done.set()

    def stop_recording(self) -> None:
        if not self.is_recording:
            return
        self.is_recording = False
        self.hotkey_active = False
        if not self._recording_done.wait(timeout=5.0):
            print("Warnung: Recording-Thread hat nicht rechtzeitig geantwortet")
        if len(self.audio_data) > 0:
            print("Audioaufnahme beendet")
            self.transcribe_audio(self.audio_data)
        else:
            print("Keine Audiodaten aufgezeichnet")

    # ── Transcription ────────────────────────────────────────────────────────

    def transcribe_audio(self, audio_data: np.ndarray) -> None:
        if not WHISPER_AVAILABLE or self.whisper_model is None:
            print("Whisper nicht verfügbar — Überspringe Transkription")
            return
        try:
            print("Transkribiere Audio...")
            audio_flat = audio_data.flatten().astype(np.float32)

            # NaN/Inf vor dem Resample bereinigen
            if not np.isfinite(audio_flat).all():
                print("   Warnung: Audio enthält NaN/Inf — bereinige...")
                audio_flat = np.nan_to_num(audio_flat, nan=0.0, posinf=0.0, neginf=0.0)

            # Auf Whisper-Rate resamplen wenn die Aufnahme auf nativer Geräterate war
            native_sr = getattr(self, '_native_sr', config.SAMPLERATE)
            if native_sr != config.SAMPLERATE:
                g = gcd(native_sr, config.SAMPLERATE)
                audio_flat = resample_poly(audio_flat, config.SAMPLERATE // g, native_sr // g)

            # Stille abfangen — softmax(all -inf) in Whispers Attention ergibt NaN
            rms = float(np.sqrt(np.mean(audio_flat ** 2)))
            if rms < 1e-4:
                print("Keine Sprache erkannt (Signal zu schwach)")
                return

            result = self.whisper_model.transcribe(audio_flat, fp16=False)
            text = result.get("text", "").strip()
            if text:
                print(f"\nTranskription:\n{text}\n")
                if self.on_transcription:
                    self.on_transcription(text)
                self._ai.process(text)
            else:
                print("Keine Sprache erkannt")
        except Exception as e:
            print(f"Fehler bei Transkription: {e}")

    # ── CLI-Modus ────────────────────────────────────────────────────────────

    def run(self) -> None:
        print("=" * 60)
        print("Jarvis — Voice Assistant")
        print(f"Modus: {config.EXECUTION_MODE.upper()}")
        print("CMD + OPTION halten zum Aufnehmen")
        print("=" * 60)
        self.start_hotkey_listener()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nJarvis wird beendet...")
            self.stop_hotkey_listener()
