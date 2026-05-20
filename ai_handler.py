"""
Jarvis — AI-Handler
Verwaltet LLM-Anfragen (Ollama), AppleScript-Ausführung und TTS.
"""
import json
import re
import subprocess
import threading
from typing import Callable, Optional

import requests

import config


class AIHandler:
    """Verbindet Transkriptionen mit dem LLM und führt Antworten aus."""

    def __init__(self, get_mode: Callable[[], str]):
        self._get_mode = get_mode
        self._ready: bool = False
        self.on_token: Optional[Callable[[str], None]] = None
        self.on_status: Optional[Callable[[str], None]] = None

    def connect(self) -> None:
        """Prüft Ollama-Erreichbarkeit und wärmt das Modell vor."""
        try:
            print(f"   Verbinde mit Ollama ({config.OLLAMA_HOST})...")
            requests.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5).raise_for_status()
            self._ready = True
            print(f"   Ollama verbunden — Modell: {config.OLLAMA_MODEL}")
        except Exception as e:
            print(f"   Ollama nicht erreichbar: {e}")
            self._ready = False
            return

        try:
            print("   Modell vorwärmen...")
            warmup = requests.post(
                f"{config.OLLAMA_HOST}/api/generate",
                json={"model": config.OLLAMA_MODEL, "prompt": "Hi",
                      "stream": False, "options": {"num_predict": 1}},
                timeout=30,
            )
            warmup.raise_for_status()
            warmup.close()
            print("   Modell bereit")
        except Exception as e:
            print(f"   Warmup fehlgeschlagen (nicht kritisch): {e}")

    @property
    def available(self) -> bool:
        return self._ready

    # ── LLM ─────────────────────────────────────────────────────────────────

    def process(self, text: str) -> None:
        """Sendet transkribierten Text an das Modell und zeigt die Antwort an."""
        if not self._ready:
            print("Ollama nicht erreichbar — stelle sicher, dass 'ollama serve' läuft.")
            return

        mode = self._get_mode()
        if self.on_status:
            self.on_status("Verarbeite Anfrage...")

        prompt = self._build_prompt(text, mode)
        full_response = self._query_llm(prompt, mode)
        if not full_response:
            return

        if self.on_status:
            preview = full_response[:40].replace("\n", " ")
            self.on_status(f"Antwort: {preview}")
        if self.on_token:
            self.on_token(f"\nJarvis: {full_response}\n")

        if mode == "execute":
            script = self._extract_script(full_response)
            ok, err = self.execute_script(script)
            if not ok and not self._is_permission_error(err):
                print("\nSyntax-/Laufzeitfehler — bitte Modell um Korrektur...\n", flush=True)
                if self.on_status:
                    self.on_status("Korrigiere Script...")
                retry_prompt = self._build_retry_prompt(text, script, err)
                retry_response = self._query_llm(retry_prompt, mode)
                if retry_response:
                    retry_script = self._extract_script(retry_response)
                    if self.on_token:
                        self.on_token(f"\nJarvis (korrigiert): {retry_script}\n")
                    self.execute_script(retry_script)
        elif mode == "speak":
            threading.Thread(target=self._say, args=(full_response,), daemon=True).start()

    def _query_llm(self, prompt: str, mode: str) -> str:
        """Sendet einen Prompt an Ollama und gibt die gestreamte Antwort zurück."""
        max_tokens = (
            config.LLM_MAX_TOKENS_EXECUTE if mode == "execute"
            else config.LLM_MAX_TOKENS_SPEAK
        )
        effort = (
            config.THINK_EFFORT_EXECUTE if mode == "execute"
            else config.THINK_EFFORT_SPEAK
        )
        think_param = effort if effort else False  # None/"" → Thinking AUS
        try:
            print(f"\n{config.OLLAMA_MODEL} antwortet:")
            print("-" * 40)

            resp = requests.post(
                f"{config.OLLAMA_HOST}/api/generate",
                json={
                    "model": config.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": True,
                    "think": think_param,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": config.LLM_TEMPERATURE,
                    },
                },
                stream=True,
                timeout=180,
            )
            resp.raise_for_status()

            parts: list[str] = []
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("response", "")
                if chunk:
                    parts.append(chunk)
                    print(chunk, end="", flush=True)
                if data.get("done"):
                    break

            full_response = "".join(parts).strip()
            print()
            print(f"\n[JARVIS] Antwort ({len(full_response)} Zeichen): {full_response[:80]!r}", flush=True)
            print("-" * 40 + "\n")
            return full_response

        except Exception as e:
            print(f"\nFehler bei Modell-Verarbeitung: {e}\n", flush=True)
            if self.on_token:
                self.on_token(f"\n[Fehler: {e}]\n")
            if self.on_status:
                self.on_status(f"Fehler: {e}")
            return ""

    @staticmethod
    def _extract_script(raw: str) -> str:
        """Entfernt Markdown-Fences und Erklärtext um den eigentlichen Code."""
        s = raw.strip()
        m = re.search(
            r"```(?:applescript|apple|osascript)?\s*\n?(.*?)```",
            s, re.DOTALL | re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        # Ab erster Zeile, die mit AppleScript-Schlüsselwort beginnt
        keywords = r"(tell|on|set|activate|display|do\s+shell|say|return|launch|quit|repeat|if|use|property|global)\b"
        lines = s.splitlines()
        for i, line in enumerate(lines):
            if re.match(rf"\s*{keywords}", line, re.IGNORECASE):
                return "\n".join(lines[i:]).strip()
        return s

    @staticmethod
    def _is_permission_error(stderr: str) -> bool:
        s = stderr.lower()
        return any(k in s for k in (
            "1002", "-1743", "nicht berechtigt",
            "not authorized", "not allowed", "isn't allowed",
        ))

    @staticmethod
    def _build_prompt(text: str, mode: str) -> str:
        if mode == "execute":
            return (
                "Du bist AppleScript-Experte. Erzeuge ein gültiges AppleScript "
                "für die Anfrage.\n\n"
                "REGELN:\n"
                "- Antworte AUSSCHLIESSLICH mit reinem AppleScript-Code\n"
                "- KEINE Markdown-Code-Blöcke (kein ```), KEINE Erklärungen, "
                "kein Kommentar davor oder danach\n"
                "- Verwende korrekte AppleScript-Syntax\n"
                "- Für UI-Steuerung 'tell application \"System Events\"' verwenden\n\n"
                "BEISPIELE:\n"
                "Anfrage: Öffne den Finder\n"
                'tell application "Finder" to activate\n\n'
                "Anfrage: Stelle die Lautstärke auf 50%\n"
                "set volume output volume 50\n\n"
                "Anfrage: Zeige eine Benachrichtigung 'Hallo'\n"
                'display notification "Hallo" with title "Jarvis"\n\n'
                f"Anfrage: {text}\n"
            )
        return f"Gib mir eine kurze, prägnante Antwort auf folgende Frage oder Aussage:\n\n{text}"

    @staticmethod
    def _build_retry_prompt(text: str, broken_script: str, error: str) -> str:
        return (
            "Du hast für die folgende Anfrage ein AppleScript erzeugt, das "
            "fehlgeschlagen ist. Korrigiere es. Antworte AUSSCHLIESSLICH mit "
            "dem korrigierten AppleScript-Code — keine Markdown-Fences, keine "
            "Erklärung.\n\n"
            f"Anfrage: {text}\n\n"
            "Fehlerhaftes Script:\n"
            f"{broken_script}\n\n"
            "Fehlermeldung von osascript:\n"
            f"{error.strip()}\n\n"
            "Korrigiertes AppleScript:\n"
        )

    # ── AppleScript ──────────────────────────────────────────────────────────

    def execute_script(self, script: str) -> tuple[bool, str]:
        """Führt ein AppleScript via osascript aus. Gibt (Erfolg, stderr) zurück."""
        try:
            print("\nFühre Script aus...\n")
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                print(f"Output:\n{result.stdout}")
            if result.stderr.strip():
                print(f"Fehler-Output:\n{result.stderr}")
            if result.returncode == 0:
                print("Script erfolgreich ausgeführt\n")
                return True, ""
            print(f"Script Fehler (Return Code: {result.returncode})\n")
            return False, result.stderr
        except subprocess.TimeoutExpired:
            print("Script Timeout (über 10 Sekunden)\n")
            return False, "timeout"
        except Exception as e:
            print(f"Fehler beim Ausführen: {e}\n")
            import traceback
            traceback.print_exc()
            return False, str(e)

    # ── TTS ──────────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Liest vollständigen Text nicht-blockierend vor."""
        threading.Thread(target=self._say, args=(text,), daemon=True).start()

    def _say(self, text: str) -> None:
        cmd = ["say"]
        if config.TTS_VOICE:
            cmd += ["-v", config.TTS_VOICE]
        if config.TTS_RATE:
            cmd += ["-r", str(config.TTS_RATE)]
        cmd.append(text.strip())
        try:
            subprocess.run(cmd, check=False, timeout=120)
        except subprocess.TimeoutExpired:
            print("TTS Timeout\n")
        except Exception as e:
            print(f"Fehler beim Vorlesen: {e}\n")
