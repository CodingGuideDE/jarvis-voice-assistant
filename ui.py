"""
Jarvis — GUI
Tkinter-Oberfläche zur Steuerung von Jarvis.
"""
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import config
from audio_recorder import AudioRecorder


_ICON_DIR = Path(__file__).parent / "icons"
# Höhere Auflösung zuerst — Tk skaliert für Titlebar/Cmd+Tab/Dock automatisch.
_ICON_CANDIDATES = ("jarvis-wave.png", "jarvis-wave-256.png", "jarvis-wave-128.png")


class JarvisGUI:
    """Hauptfenster des Jarvis Voice Assistant."""

    COLORS = {
        "bg_primary":        "#1e1e2e",
        "bg_secondary":      "#181825",
        "bg_card":           "#24243c",
        "bg_input":          "#2a2b40",
        "fg_primary":        "#cdd6f4",
        "fg_secondary":      "#7f849c",
        "fg_disabled":       "#45475a",
        "accent_blue":       "#89b4fa",
        "accent_blue_hover": "#a8c8ff",
        "accent_green":      "#a6e3a1",
        "accent_orange":     "#fab387",
        "accent_red":        "#f38ba8",
        "accent_red_hover":  "#f5a3b8",
        "border":            "#313244",
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jarvis")
        self.root.geometry("660x640")
        self.root.configure(bg=self.COLORS["bg_primary"])

        # Referenz auf das PhotoImage halten — sonst sammelt der GC es ein
        # und das Icon verschwindet aus der Titlebar / Dock.
        self._app_icon = self._load_app_icon()
        if self._app_icon is not None:
            self.root.iconphoto(True, self._app_icon)

        self._setup_styles()

        self.execution_mode = tk.StringVar(value=config.EXECUTION_MODE)
        initial_effort = (
            config.THINK_EFFORT_EXECUTE if config.EXECUTION_MODE == "execute"
            else config.THINK_EFFORT_SPEAK
        )
        self.think_effort = tk.StringVar(value=initial_effort or "")
        self.jarvis_instance: AudioRecorder | None = None
        self.is_running: bool = False

        self._create_ui()

    @staticmethod
    def _load_app_icon() -> tk.PhotoImage | None:
        """Lädt das Jarvis-Icon für Titlebar / Dock. None bei Fehlschlag."""
        for name in _ICON_CANDIDATES:
            path = _ICON_DIR / name
            if path.exists():
                try:
                    return tk.PhotoImage(file=str(path))
                except tk.TclError:
                    continue
        return None

    # ── Styles ───────────────────────────────────────────────────────────────

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        c = self.COLORS

        style.configure("Primary.TButton",
            background=c["accent_blue"], foreground=c["bg_secondary"],
            font=("Helvetica Neue", 10, "bold"),
            borderwidth=0, focuscolor="none", relief="flat", padding=(18, 10))
        style.map("Primary.TButton",
            background=[("disabled", c["border"]),    ("active", c["accent_blue_hover"])],
            foreground=[("disabled", c["fg_disabled"]), ("active", c["bg_secondary"])])

        style.configure("Danger.TButton",
            background=c["accent_red"], foreground=c["bg_secondary"],
            font=("Helvetica Neue", 10, "bold"),
            borderwidth=0, focuscolor="none", relief="flat", padding=(18, 10))
        style.map("Danger.TButton",
            background=[("disabled", c["border"]),    ("active", c["accent_red_hover"])],
            foreground=[("disabled", c["fg_disabled"]), ("active", c["bg_secondary"])])

        # Expliziter Hover-Foreground — sonst dreht clam den Text dunkel
        style.configure("Mode.TRadiobutton",
            background=c["bg_card"], foreground=c["fg_primary"],
            font=("Helvetica Neue", 10), focuscolor=c["bg_card"], padding=(0, 4))
        style.map("Mode.TRadiobutton",
            background=[("active", c["bg_card"])],
            foreground=[("active", c["accent_blue"]), ("!active", c["fg_primary"])])

        style.configure("Slim.Vertical.TScrollbar",
            background=c["fg_disabled"],
            troughcolor=c["bg_input"],
            borderwidth=0, relief="flat",
            arrowsize=0)
        style.map("Slim.Vertical.TScrollbar",
            background=[("active", c["fg_secondary"]), ("!active", c["fg_disabled"])])

    # ── Layout ───────────────────────────────────────────────────────────────

    def _create_ui(self) -> None:
        c = self.COLORS

        # Header
        header = tk.Frame(self.root, bg=c["bg_primary"])
        header.pack(fill="x", padx=28, pady=(28, 0))
        tk.Label(header, text="Jarvis",
                 bg=c["bg_primary"], fg=c["fg_primary"],
                 font=("Helvetica Neue", 26, "bold")).pack(anchor="w")
        tk.Label(header, text="Voice Assistant",
                 bg=c["bg_primary"], fg=c["fg_secondary"],
                 font=("Helvetica Neue", 11)).pack(anchor="w")
        tk.Frame(self.root, bg=c["border"], height=1).pack(fill="x", padx=28, pady=20)

        # Status-Karte
        status_card = tk.Frame(self.root, bg=c["bg_card"])
        status_card.pack(fill="x", padx=28)
        inner_s = tk.Frame(status_card, bg=c["bg_card"])
        inner_s.pack(fill="x", padx=16, pady=14)
        tk.Label(inner_s, text="STATUS",
                 bg=c["bg_card"], fg=c["fg_secondary"],
                 font=("Helvetica Neue", 8, "bold")).pack(anchor="w")
        row = tk.Frame(inner_s, bg=c["bg_card"])
        row.pack(fill="x", pady=(6, 2))
        self._status_dot = tk.Label(row, text="●",
                                     bg=c["bg_card"], fg=c["accent_green"],
                                     font=("Helvetica Neue", 9))
        self._status_dot.pack(side="left")
        self._status_label = tk.Label(row, text="Bereit",
                                       bg=c["bg_card"], fg=c["fg_primary"],
                                       font=("Helvetica Neue", 10))
        self._status_label.pack(side="left", padx=(8, 0))
        self._mode_label = tk.Label(inner_s, text=f"Modus: {config.EXECUTION_MODE.upper()}",
                                     bg=c["bg_card"], fg=c["fg_secondary"],
                                     font=("Helvetica Neue", 9))
        self._mode_label.pack(anchor="w")
        self.execution_mode.trace_add("write", self._on_mode_change)

        # Modus-Auswahl
        tk.Frame(self.root, bg=c["bg_primary"], height=10).pack()
        mode_card = tk.Frame(self.root, bg=c["bg_card"])
        mode_card.pack(fill="x", padx=28)
        inner_m = tk.Frame(mode_card, bg=c["bg_card"])
        inner_m.pack(fill="x", padx=16, pady=14)
        tk.Label(inner_m, text="MODUS",
                 bg=c["bg_card"], fg=c["fg_secondary"],
                 font=("Helvetica Neue", 8, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Radiobutton(inner_m,
                        text="Vorlesen  —  Antworten werden laut vorgelesen",
                        variable=self.execution_mode, value="speak",
                        style="Mode.TRadiobutton").pack(anchor="w", pady=(0, 6))
        ttk.Radiobutton(inner_m,
                        text="Script-Ausführung  —  Antworten als AppleScript",
                        variable=self.execution_mode, value="execute",
                        style="Mode.TRadiobutton").pack(anchor="w")

        # Thinking-Level
        tk.Frame(self.root, bg=c["bg_primary"], height=10).pack()
        think_card = tk.Frame(self.root, bg=c["bg_card"])
        think_card.pack(fill="x", padx=28)
        inner_t = tk.Frame(think_card, bg=c["bg_card"])
        inner_t.pack(fill="x", padx=16, pady=14)
        tk.Label(inner_t, text="THINKING",
                 bg=c["bg_card"], fg=c["fg_secondary"],
                 font=("Helvetica Neue", 8, "bold")).pack(anchor="w", pady=(0, 10))
        for label, value in (
            ("Aus      —  ohne Nachdenken, schnellste Antwort", ""),
            ("Niedrig  —  kurzer Vorlauf",                       "low"),
            ("Mittel   —  ausgewogen (Standard für Execute)",   "medium"),
            ("Hoch     —  ausführlich, zuverlässigste Scripts",  "high"),
        ):
            ttk.Radiobutton(inner_t, text=label,
                            variable=self.think_effort, value=value,
                            style="Mode.TRadiobutton").pack(anchor="w", pady=(0, 4))
        self.think_effort.trace_add("write", self._on_effort_change)

        # Buttons
        btn_frame = tk.Frame(self.root, bg=c["bg_primary"])
        btn_frame.pack(fill="x", padx=28, pady=14)
        self._start_btn = ttk.Button(btn_frame, text="Starte Jarvis",
                                      command=self._start, style="Primary.TButton")
        self._start_btn.pack(side="left", padx=(0, 8))
        self._stop_btn = ttk.Button(btn_frame, text="Beende Jarvis",
                                     command=self._stop, style="Danger.TButton", state="disabled")
        self._stop_btn.pack(side="left")

        # Live-Ausgabe
        output_card = tk.Frame(self.root, bg=c["bg_card"])
        output_card.pack(fill="both", expand=True, padx=28, pady=(0, 28))
        inner_o = tk.Frame(output_card, bg=c["bg_card"])
        inner_o.pack(fill="both", expand=True, padx=16, pady=14)
        tk.Label(inner_o, text="AUSGABE",
                 bg=c["bg_card"], fg=c["fg_secondary"],
                 font=("Helvetica Neue", 8, "bold")).pack(anchor="w", pady=(0, 10))
        text_frame = tk.Frame(inner_o, bg=c["bg_input"], bd=0)
        text_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame, style="Slim.Vertical.TScrollbar",
                                   orient="vertical")
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=2)

        self._output = tk.Text(
            text_frame, height=8,
            bg=c["bg_input"], fg=c["fg_primary"],
            insertbackground=c["accent_blue"],
            selectbackground=c["accent_blue"], selectforeground=c["bg_secondary"],
            font=("Menlo", 9), wrap="word", relief="flat",
            borderwidth=0, highlightthickness=0, state="disabled",
            yscrollcommand=scrollbar.set)
        self._output.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=2)
        scrollbar.config(command=self._output.yview)

        self._output.tag_configure("user", foreground=c["accent_orange"])
        self._output.tag_configure("meta", foreground=c["fg_secondary"])

    # ── Control ──────────────────────────────────────────────────────────────

    def _start(self) -> None:
        try:
            config.EXECUTION_MODE = self.execution_mode.get()
            self._set_status("Initialisiere...", self.COLORS["accent_orange"])
            self._start_btn.config(state="disabled")
            self._stop_btn.config(state="normal")
            self.is_running = True
            threading.Thread(target=self._run_jarvis, daemon=True).start()
        except Exception as e:
            print(f"Fehler beim Starten: {e}")
            self._set_status("Fehler beim Starten", self.COLORS["accent_red"])
            self._start_btn.config(state="normal")
            self._stop_btn.config(state="disabled")

    def _run_jarvis(self) -> None:
        c = self.COLORS
        try:
            self.jarvis_instance = AudioRecorder()

            max_wait, waited = 120, 0
            while self.jarvis_instance.models_loading and waited < max_wait:
                self._update_status("Modelle werden geladen...", c["accent_orange"])
                time.sleep(1)
                waited += 1

            if not self.jarvis_instance.models_ready:
                self._update_status("Fehler: Modelle nicht geladen", c["accent_red"])
                self.root.after(0, lambda: self._start_btn.config(state="normal"))
                self.root.after(0, lambda: self._stop_btn.config(state="disabled"))
                return

            self._update_status("Jarvis aktiv", c["accent_green"])

            self.jarvis_instance.on_transcription = lambda t: self._append_output(
                f"Du: {t}\n", tag="user", clear=True
            )
            self.jarvis_instance._ai.on_token = lambda t: self._append_output(t)
            self.jarvis_instance._ai.on_status = lambda s: self._update_status(s, self.COLORS["accent_blue"])

            self.jarvis_instance.on_hotkey_dead_callback = lambda: self._update_status(
                "Hotkey ausgefallen — Accessibility-Berechtigung prüfen", c["accent_orange"]
            )
            self.jarvis_instance.start_hotkey_listener()

            while self.is_running:
                time.sleep(0.5)

        except Exception as e:
            print(f"Fehler in _run_jarvis: {e}")
            import traceback
            traceback.print_exc()
            self._update_status("Fehler beim Starten", c["accent_red"])
            self.root.after(0, lambda: self._start_btn.config(state="normal"))
            self.root.after(0, lambda: self._stop_btn.config(state="disabled"))
        finally:
            self.is_running = False

    def _stop(self) -> None:
        self.is_running = False
        self._set_status("Beendet", self.COLORS["fg_disabled"])
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        try:
            if self.jarvis_instance:
                self.jarvis_instance.stop_hotkey_listener()
        except Exception:
            pass
        time.sleep(0.5)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _on_mode_change(self, var, index, op) -> None:  # noqa: ARG002
        config.EXECUTION_MODE = self.execution_mode.get()
        self._mode_label.config(text=f"Modus: {config.EXECUTION_MODE.upper()}")
        default = (
            config.THINK_EFFORT_EXECUTE if config.EXECUTION_MODE == "execute"
            else config.THINK_EFFORT_SPEAK
        )
        self.think_effort.set(default or "")

    def _on_effort_change(self, var, index, op) -> None:  # noqa: ARG002
        value = self.think_effort.get() or None
        if config.EXECUTION_MODE == "execute":
            config.THINK_EFFORT_EXECUTE = value
        else:
            config.THINK_EFFORT_SPEAK = value

    def _append_output(self, text: str, tag: str | None = None,
                       clear: bool = False) -> None:
        """Thread-sicher Text an das Ausgabe-Feld anhängen.

        clear=True leert das Feld vorher — z. B. zu Beginn einer neuen Anfrage,
        damit sich nicht alle vorherigen Antworten aneinanderreihen.
        """
        def _do():
            try:
                self._output.config(state="normal")
                if clear:
                    self._output.delete("1.0", "end")
                if tag:
                    self._output.insert("end", text, tag)
                else:
                    self._output.insert("end", text)
                self._output.see("end")
                self._output.config(state="disabled")
            except Exception as e:
                print(f"[_append_output Fehler] {e}", flush=True)
        try:
            self.root.after(0, _do)
        except Exception as e:
            print(f"[root.after Fehler] {e}", flush=True)

    def _set_status(self, text: str, dot_color: str | None = None) -> None:
        """Direkt aus dem GUI-Thread aufrufen."""
        self._status_label.config(text=text)
        self._status_dot.config(fg=dot_color or self.COLORS["accent_green"])

    def _update_status(self, text: str, dot_color: str | None = None) -> None:
        """Thread-sicher via root.after."""
        try:
            self.root.after(0, lambda: self._set_status(text, dot_color))
        except Exception:
            pass
