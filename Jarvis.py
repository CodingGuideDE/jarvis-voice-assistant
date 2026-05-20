#!/usr/bin/env python3
"""
Jarvis — Voice Assistant
Entry-Point: setzt SIGTRAP-Handler, startet GUI oder fällt auf CLI zurück.
"""
# SIGTRAP-Handler muss als erstes gesetzt werden, bevor pynput-nahe Imports laufen.
# sys.exit() würde atexit-Callbacks triggern, die selbst SIGTRAP auslösen → Kaskadencrash.
import os
import platform
import signal


def _handle_sigtrap(_signum, _frame) -> None:
    msg = (
        "\n" + "=" * 60 +
        "\nSIGTRAP: macOS Accessibility-Berechtigung fehlt!" +
        "\n" + "=" * 60 +
        "\n\nLösung:" +
        "\n  1. Systemeinstellungen > Datenschutz & Sicherheit > Bedienungshilfen" +
        "\n  2. Füge Terminal ODER deine IDE (VS Code, PyCharm) hinzu" +
        "\n  3. Programm neu starten\n"
    )
    os.write(2, msg.encode())
    os._exit(5)


if platform.system() == "Darwin":
    signal.signal(signal.SIGTRAP, _handle_sigtrap)

# Ab hier sicher: SIGTRAP ist abgefangen
import time
import tkinter as tk

import config
from audio_recorder import AudioRecorder
from ui import JarvisGUI


def main() -> None:
    print("=" * 70)
    print("Jarvis — Voice Assistant")
    print("=" * 70 + "\n")

    try:
        print("Starte GUI...\n")
        root = tk.Tk()
        JarvisGUI(root)
        root.mainloop()
    except Exception as gui_error:
        print(f"\nGUI-Fehler: {gui_error}")
        print("Starte CLI-Modus...\n")
        _run_cli()


def _run_cli() -> None:
    try:
        jarvis = AudioRecorder()

        print("=" * 70)
        print(f"Modus: {config.EXECUTION_MODE.upper()}")
        print("CMD + OPTION halten zum Aufnehmen — CTRL+C zum Beenden")
        print("=" * 70 + "\n")

        print("Warte auf Modellladung...")
        max_wait, waited = 120, 0
        while jarvis.models_loading and waited < max_wait:
            print(".", end="", flush=True)
            time.sleep(1)
            waited += 1

        if not jarvis.models_ready:
            print("\nModelle konnten nicht geladen werden")
            return

        print("\nJarvis läuft\n")
        jarvis.start_hotkey_listener()

        jarvis.run()

    except KeyboardInterrupt:
        print("\nJarvis wird beendet...")
    except Exception as e:
        print(f"\nKritischer Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
