# 🤖 Jarvis - Sprachassistent mit Hotkey-Erkennung

## Funktionalität
- **Hotkey**: Drücke und halte **cmd + option** zum Aufnehmen
- **Aufnahme**: Audio wird mit 16kHz aufgezeichnet
- **Transkription**: Automatische Umwandlung zu Text mit OpenAI Whisper
- **Speicherung**: Audio-Dateien und Transkriptionen werden gespeichert

## 📦 Installation

### Schritt 1: Erforderliche Pakete installieren

```bash
cd /Users/florianhaglsperger/Desktop/Sync\ VScode

# Installiere fehlende Abhängigkeiten
pip install pynput openai-whisper
```

### Schritt 2: Einzelne Pakete überprüfen

```bash
# Überprüfe ob alle benötigten Pakete installiert sind
pip list | grep -E "pynput|whisper|sounddevice|scipy|numpy"
```

**Benötigte Pakete:**
- `pynput` >= 1.7.6 - Für globale Hotkey-Erkennung
- `openai-whisper` >= 20231117 - Für Speech-to-Text
- `sounddevice` >= 0.4.5 - Für Audioaufnahmen
- `scipy` >= 1.5.0 - Für Audio-Verarbeitung
- `numpy` >= 1.19.0 - Für numerische Operationen

## 🚀 Verwendung

### Starte Jarvis

```bash
cd /Users/florianhaglsperger/Desktop/Sync\ VScode/AI_Projekts
python3 Jarvis.py
```

### Bedienung

1. **Aufnahme starten**: Drücke und halte **cmd + option**
2. **Aufnahme beenden**: Lasse eine der Tasten los
3. **Transkription**: Startet automatisch nach der Aufnahme
4. **Ergebnis**: Wird in der Konsole angezeigt

### Beispiel-Output

```
============================================================
🤖 Jarvis - Voice Assistant
============================================================

🎙️  Starte Hotkey-Listener (cmd + option zum Aufnehmen)...
📦 Lade Whisper-Modell (small)...
✅ Whisper-Modell geladen

Bedienung:
  • Drücke und halte: CMD + OPTION zum Aufnehmen
  • Lasse los zum Beenden
  • Audio wird automatisch transkribiert

============================================================

🔴 Audioaufnahme gestartet...
⏹️  Audioaufnahme beendet
💾 Audio gespeichert: audio_recordings/recording_20240427_143022.wav
🔄 Transkribiere Audio...

✅ Transkription:
Hallo, das ist ein Test

📄 Transkription gespeichert: audio_recordings/recording_20240427_143022.json
```

## 📁 Dateistruktur

Aufnahmen werden im Verzeichnis `audio_recordings/` gespeichert:

```
audio_recordings/
├── recording_20240427_143022.wav       # Rohes Audio
└── recording_20240427_143022.json      # Transkription mit Metadaten
```

### JSON-Format der Transkription

```json
{
  "timestamp": "2024-04-27T14:30:22.123456",
  "audio_file": "audio_recordings/recording_20240427_143022.wav",
  "text": "Hallo, das ist ein Test",
  "language": "de",
  "confidence": {
    "de": 0.95,
    "en": 0.04,
    "fr": 0.01
  }
}
```

## ⚙️ Konfiguration

Die folgenden Parameter können in `Jarvis.py` angepasst werden:

```python
SAMPLERATE = 16000      # Abtastrate in Hz (16kHz für Whisper optimal)
MAX_DURATION = 30       # Maximale Aufnahmedauer in Sekunden
AUDIO_DIR = Path("audio_recordings")  # Speicherort
```

## 🔧 Troubleshooting

### Problem: "pynput ist nicht installiert"

**Lösung:**
```bash
pip install pynput
```

### Problem: "Whisper-Modell wird nicht geladen"

**Ursachen:**
1. Zu wenig Speicher (Whisper "small" benötigt ~461 MB)
2. Keine Internetverbindung beim ersten Start
3. Beschädigter Cache

**Lösungen:**
```bash
# Cache leeren
rm -rf ~/.cache/whisper

# Erneut versuchen (wird das Modell neu heruntergeladen)
python3 Jarvis.py
```

### Problem: Hotkey funktioniert nicht

**Mögliche Ursachen:**
- Bildschirm ist gesperrt
- Andere Anwendung nutzt den Hotkey
- Zugriffsrechte fehlen (bei macOS)

**Lösung (macOS):**
Gehe zu **Systemeinstellungen > Datenschutz & Sicherheit > Eingabehilfen** und aktiviere Zugriff für Terminal/VS Code.

### Problem: "No such device" bei Audioaufnahme

**Lösung:**
```bash
# Überprüfe verfügbare Audiogeräte
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Oder spezifisches Gerät in Jarvis.py setzen:
sd.default.device = [None, 0]  # input_device_index = 0
```

### Problem: Audio-Qualität ist schlecht

**Optimierungen:**
```python
# In Jarvis.py anpassen
SAMPLERATE = 16000      # Nicht erhöhen (Whisper optimal bei 16kHz)
MAX_DURATION = 60       # Erhöhen für längere Aufnahmen

# Oder microphone settings in sounddevice anpassen
sd.rec(..., latency='low')  # Für bessere Qualität
```

## 📊 Performance

- **Whisper Small Model**: ~461 MB RAM, ~8-10 Sekunden für 30 Sekunden Audio auf CPU
- **Audio Latency**: ~50-100ms (abhängig vom System)
- **CPU-Auslastung**: ~30-50% während Transkription

## 🔐 Datenschutz

- Alle Aufnahmen werden **lokal gespeichert**
- Keine Übertragung zu externen Servern (wenn Whisper lokal verwendet wird)
- Transkriptionen erfolgen mit OpenAI Whisper (Open Source)

## 📝 Nächste Schritte

Mögliche Erweiterungen:

1. **Intent-Erkennung**: Erkenne Absichten aus Transkription
2. **Text-to-Speech**: Gebe Antworten als Audio aus
3. **Kommando-Ausführung**: Steuere Anwendungen per Sprache
4. **Cloud-Speicherung**: Synchronisiere Aufnahmen
5. **Whisper Large Model**: Noch präzisere Transkriptionen

## 📚 Referenzen

- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [pynput Documentation](https://pynput.readthedocs.io/)
- [sounddevice Documentation](https://python-sounddevice.readthedocs.io/)

---

**Viel Spaß mit Jarvis! 🎙️**
