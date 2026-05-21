# Jarvis — Voice Assistant für macOS

Lokaler Push-to-Talk Sprachassistent. Audio wird per Hotkey aufgenommen, von OpenAI Whisper transkribiert und an ein lokales Ollama-LLM gesendet. Die Antwort wird entweder als AppleScript ausgeführt oder über die macOS-Stimme vorgelesen.

Alles läuft lokal — kein Cloud-Service, keine Datenübertragung.

## Features

- **Push-to-Talk** per `CMD + OPTION` (global, auch wenn das Fenster im Hintergrund ist)
- **Speech-to-Text** mit OpenAI Whisper (lokal, CPU)
- **Lokales LLM** über Ollama (z. B. `qwen3.5:4b`, `gemma4:e2b`)
- **Zwei Modi**, zur Laufzeit per UI umschaltbar:
  - **Vorlesen** — Antwort wird mit `say` ausgesprochen
  - **Script-Ausführung** — Antwort wird als AppleScript via `osascript` ausgeführt; bei Syntaxfehlern automatischer Korrektur-Retry
- **Thinking-Budget** für Reasoning-Modelle (Aus / Niedrig / Mittel / Hoch) über die UI — **nur für schnelle Modelle empfohlen** (siehe Hinweis unten)
- **Tkinter-GUI** im Catppuccin-Mocha-Theme mit Live-Statusanzeige und Ausgabefeld
- **CLI-Fallback** falls die GUI nicht startet

## Voraussetzungen

- **macOS** (getestet auf Apple Silicon, Darwin 25.x)
- **Python 3.10+**
- **Ollama** lokal installiert und gestartet — [ollama.com](https://ollama.com)
- **Homebrew** (für ffmpeg, optional)
- Mindestens **8 GB RAM** (Whisper `small` ~500 MB, LLM je nach Modell 3–8 GB)

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/CodingGuideDE/jarvis-voice-assistant.git
cd jarvis-voice-assistant
```

### 2. Virtuelle Umgebung anlegen und Abhängigkeiten installieren

```bash
python3 -m venv jarvis_env
source jarvis_env/bin/activate
pip install -r requirements_jarvis.txt
```

Zusätzlich benötigt: `requests` (für Ollama-HTTP).

```bash
pip install requests
```

### 3. ffmpeg installieren (von Whisper benötigt)

```bash
brew install ffmpeg
```

### 4. Ollama-Modell laden

```bash
ollama serve            # in eigenem Terminal laufen lassen
ollama pull qwen3.5:4b  # oder gemma4:e2b, o. Ä.
```

Der Modellname muss in [config.py](config.py) unter `OLLAMA_MODEL` eingetragen sein.

### 5. macOS-Berechtigungen freigeben

Beim ersten Start fragt macOS nach mehreren Berechtigungen — alle erlauben:

- **Bedienungshilfen** (Accessibility) — für globalen Hotkey-Listener
  *Systemeinstellungen → Datenschutz & Sicherheit → Bedienungshilfen* → Terminal oder die IDE hinzufügen
- **Mikrofon** — für die Audioaufnahme
- **Automation** — für AppleScript-Ausführung pro Ziel-App

Fehlende Accessibility-Berechtigung führt zu einem SIGTRAP. Jarvis fängt das ab und zeigt eine Hinweismeldung.

## Verwendung

### GUI starten (Standard)

```bash
python3 Jarvis.py
```

1. Modus wählen (Vorlesen / Script-Ausführung)
2. Optional: Thinking-Budget setzen
3. **„Starte Jarvis"** klicken — Modelle werden im Hintergrund geladen
4. Sobald der Status auf **„Jarvis aktiv"** wechselt: `CMD + OPTION` halten und sprechen
5. Tasten loslassen — Transkription und Antwort erscheinen im Ausgabefeld

### CLI

Wenn die GUI scheitert, fällt Jarvis automatisch auf CLI zurück. Manuell:

```bash
python3 Jarvis.py    # GUI-Fehler → CLI
```

CLI-Bedienung: `CMD + OPTION` halten zum Aufnehmen, `CTRL+C` zum Beenden.

## Konfiguration

Alle Parameter in [config.py](config.py):

| Konstante | Default | Bedeutung |
|---|---|---|
| `SAMPLERATE` | `16000` | Whisper-Eingabe-Sample-Rate (Aufnahme läuft auf nativer Geräterate und wird resampelt) |
| `MAX_DURATION` | `30` | maximale Aufnahmedauer in Sekunden |
| `WHISPER_MODEL_SIZE` | `"small"` | `tiny` / `base` / `small` / `medium` / `large` |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama-API-URL |
| `OLLAMA_MODEL` | `"qwen3.5:4b"` | geladenes Ollama-Modell |
| `LLM_MAX_TOKENS_EXECUTE` | `800` | Token-Budget Execute-Modus (Thinking + Script) |
| `LLM_MAX_TOKENS_SPEAK` | `180` | Token-Budget Speak-Modus |
| `LLM_TEMPERATURE` | `0.1` | niedriger = deterministischer |
| `THINK_EFFORT_EXECUTE` | `"medium"` | Reasoning-Budget Execute (`None`/`"low"`/`"medium"`/`"high"`) |
| `THINK_EFFORT_SPEAK` | `None` | Reasoning AUS für Vorlesen |
| `EXECUTION_MODE` | `"execute"` | Startmodus (`"execute"` oder `"speak"`) |

> **Hinweis zum Thinking-Prozess:** Bei aktivem Reasoning wird das Token-Limit
> der Anfrage aufgehoben (`num_predict = -1`), damit die Antwort nicht mitten
> im Nachdenken abgeschnitten wird. Das bedeutet aber auch: die gesamte
> Antwortzeit hängt direkt an der Inferenzgeschwindigkeit des Modells.
> **Thinking ist daher nur für schnelle Modelle geeignet** (kleine 3B–4B-Modelle
> auf Apple Silicon, MoE-Modelle wie `qwen3.5:4b`). Bei größeren oder
> langsameren Modellen wird die Wartezeit unzumutbar lang —
> dann `THINK_EFFORT_*` auf `None` setzen.

Für die Sprachausgabe wird `say` ohne `-v`-Flag verwendet — Jarvis nutzt
die in den Systemeinstellungen konfigurierte Standardstimme
(*Bedienungshilfen → Gesprochene Inhalte → Systemstimme*).

## Architektur

```
Jarvis.py            Entry-Point. Setzt SIGTRAP-Handler, startet GUI mit CLI-Fallback.
ui.py                JarvisGUI — Tkinter-Fenster (Status / Modus / Thinking / Ausgabe).
audio_recorder.py    AudioRecorder — Whisper-Loading, Hotkey-Subprocess, Mikrofon, Transkription.
ai_handler.py        AIHandler — Ollama-HTTP, Prompt-Building, Script-Extraktion, TTS, Auto-Retry.
config.py            Alle Konstanten.
CLAUDE.md            Architektur-Notizen und Fallstricke (für KI-Assistenten).
```

Datenfluss:

```
Hotkey-Subprocess (pynput)
        ↓ START / STOP über stdout
AudioRecorder.start/stop_recording
        ↓ sd.InputStream → chunks
transcribe_audio (Whisper, CPU, fp32)
        ↓ Text
AIHandler.process → _query_llm (Ollama, NDJSON-Stream)
        ↓ Antwort
execute_script (osascript)  ODER  _say (macOS 'say')
```

## Troubleshooting

### Programm crasht sofort mit SIGTRAP-Meldung
Accessibility-Berechtigung fehlt. *Systemeinstellungen → Datenschutz & Sicherheit → Bedienungshilfen* → Terminal/IDE hinzufügen, neu starten.

### Hotkey reagiert nicht
1. Accessibility-Berechtigung prüfen (siehe oben)
2. UI-Status zeigt „Hotkey ausgefallen" → Subprocess gibt nach 3 Crashes auf, Jarvis neu starten
3. Sicherstellen dass nicht eine andere App `CMD + OPTION` fängt

### „Ollama nicht erreichbar"
`ollama serve` läuft? In neuem Terminal:

```bash
curl http://localhost:11434/api/tags
```

Sollte die Modell-Liste zurückgeben. Falls nicht: `ollama serve` starten.

### Modell liefert leere Antworten
Bei Reasoning-Modellen (qwen3.5, gemma4 etc.) ohne aktiviertes Thinking
verbraucht das Modell ggf. trotzdem Tokens für unsichtbares Reasoning und
schneidet die eigentliche Antwort ab. Lösungen:
- In der UI „Thinking" auf **Niedrig/Mittel/Hoch** stellen (dann ist das
  Token-Limit aufgehoben — empfohlen nur für schnelle Modelle)
- Oder `LLM_MAX_TOKENS_EXECUTE`/`_SPEAK` deutlich erhöhen
- Oder ein nicht-thinking Modell verwenden (z. B. `qwen2.5:3b`, `llama3.2:3b`)

### Whisper transkribiert nichts / liefert NaN
- Whisper läuft bewusst auf **CPU/fp32** — MPS produziert NaN-Logits
- Aufnahme läuft auf der **nativen** Sample-Rate des Geräts (44100/48000 Hz). Das Erzwingen von 16000 Hz führt unter macOS zu NaN-Frames

### AppleScript-Fehler beim Ausführen
Manche Ziel-Apps brauchen eine separate Automation-Erlaubnis (macOS fragt beim ersten Versuch). Bei Syntaxfehlern korrigiert das Modell automatisch einmal nach.

## Datenschutz

- Audio, Transkription und LLM-Antworten verlassen das Gerät nicht
- Whisper und Ollama laufen ausschließlich lokal
- Keine Telemetrie, keine API-Keys

## Lizenz

MIT — siehe [LICENSE](LICENSE) (falls vorhanden, sonst frei nach Belieben anpassen).
