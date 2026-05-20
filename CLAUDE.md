# Jarvis — Voice Assistant für macOS

Lokaler Push-to-Talk Sprachassistent. Audio → Whisper → Ollama-LLM → entweder macOS `say` (Sprachausgabe) oder `osascript` (AppleScript-Ausführung).

## Architektur

```
Jarvis.py           Entry-Point. Setzt SIGTRAP-Handler, startet GUI (Tkinter) mit CLI-Fallback.
ui.py               JarvisGUI — Tkinter-Fenster, Status/Modus/Thinking/Ausgabe-Karten, Start/Stop.
audio_recorder.py   AudioRecorder — Whisper-Loading, Hotkey-Subprocess, Mikrofon-Recording, Transkription.
ai_handler.py       AIHandler — Ollama-HTTP, Prompt-Building, Script-Extraktion, TTS, Auto-Retry.
config.py           Alle Konstanten (Audio, Whisper, Ollama, Thinking, TTS, EXECUTION_MODE).
```

Datenfluss: `Hotkey-Subprocess → start_recording() → InputStream-Callback sammelt Chunks → stop_recording() → transcribe_audio() → AIHandler.process() → Ollama-Stream → execute_script() oder _say()`.

Sprache des Projekts: **Deutsch** (UI-Strings, Kommentare, LLM-Prompts). Bei Änderungen Stil beibehalten.

## Modi

- **execute** (Default): LLM erzeugt AppleScript, wird via `osascript -e` ausgeführt. Bei Syntax-/Laufzeitfehler **einmaliger Auto-Retry** mit Fehlermeldung im Prompt. Permission-Errors (1002, -1743, „nicht berechtigt") triggern **keinen** Retry.
- **speak**: Antwort wird via `say -v <TTS_VOICE> -r <TTS_RATE>` vorgelesen.

Modus + Thinking-Budget sind zur Laufzeit über die UI änderbar (`_on_mode_change`, `_on_effort_change` schreiben direkt in `config.*`).

## Kritische Eigenheiten — beim Editieren beachten

### Ollama-API
- **Immer** `stream=True` als `requests.post()`-Parameter **und** kein `"stream": False` im JSON-Body. Dann `iter_lines()` über NDJSON, akkumulieren bis `data["done"]`. `"stream": False` im Body liefert leeren Body nach ~2s.
- `"think"`-Parameter: `False` schaltet Reasoning AUS, `"low"|"medium"|"high"` ist das Budget. Für Thinking-Modelle (qwen3.5, gemma4) ohne `think=False` werden ~130 Tokens fürs Nachdenken verbraucht bevor sichtbarer Text in `"response"` landet — `num_predict` schneidet sonst die echte Antwort ab. `LLM_MAX_TOKENS_*` ist Gesamt-Budget (Thinking + Antwort).
- Warmup in `connect()` mit `"stream": False` ist OK (1-Token-Antwort, nur Ping).

### Whisper
- **Muss** mit `device="cpu"` geladen werden. MPS konvertiert Gewichte beim Laden in fp16 → NaN-Logits unabhängig vom `fp16=False`-Flag im `transcribe()`-Call.
- Transkription mit `fp16=False`.
- Vor `transcribe()`: NaN/Inf via `np.nan_to_num` bereinigen, RMS-Stille-Check (`< 1e-4` → skip). Sonst NaN-Attention.

### Audio
- **Nicht** mit `samplerate=16000` aufnehmen — macOS-Geräte unterstützen das oft nicht nativ, PortAudio liefert dann NaN-Frames. Stattdessen `_get_input_samplerate()` (44100/48000) verwenden und in `transcribe_audio()` via `resample_poly` auf `config.SAMPLERATE` (16000) resamplen.
- Aufnahme läuft per `sd.InputStream` mit Callback in einen `chunks`-List (kein `sd.rec()` mit Voralloc mehr).

### Best Practice:
- Nur bei wirklich komplexen Passagen Kommentare verwenden

### Hotkey (pynput)
- Läuft in **isoliertem Subprocess** (`_HOTKEY_SCRIPT`-Skript via `sys.executable -c`). Grund: pynput triggert auf macOS ohne Accessibility-Berechtigung SIGTRAP — das soll nur den Kindprozess killen, nicht Jarvis.
- Parent fängt SIGTRAP in [Jarvis.py](Jarvis.py#L13) als Allererstes ab (vor allen Imports nahe pynput) und exited mit Hinweis-Message via `os._exit(5)` (kein `sys.exit` — würde `atexit` triggern und kaskadieren).
- Bis zu 3 Auto-Restarts wenn Subprocess crasht. Danach `on_hotkey_dead_callback` → UI-Status orange.
- Trigger: CMD+OPTION halten → `START`-Zeile auf stdout. Loslassen → `STOP`.

### Threading
- `_recording_done = threading.Event()` synchronisiert `stop_recording()` mit dem Recording-Thread (kein blindes `sleep`).
- UI-Updates aus Background-Threads: **immer** über `root.after(0, ...)` — siehe `_append_output()` und `_update_status()`.
- `_append_output(text, tag=None, clear=False)`: `clear=True` leert das Feld (wird bei neuer Transkription gesetzt, damit sich Anfragen nicht aneinanderreihen).

### macOS-Berechtigungen
- **Accessibility**: Bedingung für pynput. Wird via `check_accessibility_permission()` (osascript-Probe) geprüft, sonst öffnet `start_hotkey_listener` Systemeinstellungen.
- **Mikrofon**: erstmaliger `sd.InputStream`-Aufruf triggert macOS-Prompt.
- **Automation** (für AppleScript-Targets): macOS fragt beim ersten Zugriff pro Ziel-App.

## Ausführen

```bash
python3 Jarvis.py                  # GUI (Default), Fallback auf CLI
# CLI: CMD+OPTION halten zum Aufnehmen, CTRL+C zum Beenden
```

Voraussetzungen: Ollama läuft (`ollama serve`), Modell aus `config.OLLAMA_MODEL` ist gepullt, Accessibility-Permission gesetzt.

## Stil / Konventionen

- Keine Emojis in UI-Strings, Logs oder Code.
- Kommentare nur wenn das *Warum* nicht aus dem Code hervorgeht (Fix-Begründungen, Plattform-Eigenheiten). Nicht erklären *was* der Code tut.
- Print-Logs für Lifecycle-Events sind Deutsch und ohne Emoji — Stil bei neuen Logs übernehmen.
- Keine Tests im Projekt — Verifikation erfolgt manuell durch Starten und Sprechen.
