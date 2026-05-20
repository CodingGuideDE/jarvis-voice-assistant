#!/usr/bin/env python3
"""
Jarvis - Setup Diagnostic Tool
Überprüft ob alle Abhängigkeiten korrekt installiert sind
"""

import sys
import subprocess
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def check_package(package_name, import_name=None):
    """Überprüfe ob ein Paket installiert ist"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"{Colors.GREEN}✓{Colors.END} {package_name}")
        return True
    except ImportError:
        print(f"{Colors.RED}✗{Colors.END} {package_name} - NICHT INSTALLIERT")
        return False

def check_command(command):
    """Überprüfe ob ein Kommando verfügbar ist"""
    try:
        result = subprocess.run(
            ["which", command],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓{Colors.END} {command}")
            return True
        else:
            print(f"{Colors.RED}✗{Colors.END} {command}")
            return False
    except:
        print(f"{Colors.RED}✗{Colors.END} {command}")
        return False

def get_package_version(package_name, import_name=None):
    """Hole die Version eines Pakets"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = __import__(import_name)
        if hasattr(module, '__version__'):
            return module.__version__
        return "unbekannt"
    except:
        return "nicht installiert"

def main():
    print("=" * 60)
    print(f"{Colors.BLUE}🤖 Jarvis - Setup Diagnostic Tool{Colors.END}")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Überprüfe Python
    print(f"{Colors.BLUE}📌 Python-Umgebung:{Colors.END}")
    print(f"  Python Version: {sys.version.split()[0]}")
    print(f"  Python Exe: {sys.executable}")
    print()
    
    # Überprüfe benötigte Pakete
    print(f"{Colors.BLUE}📦 Erforderliche Pakete:{Colors.END}")
    
    packages = [
        ("sounddevice", "sounddevice"),
        ("scipy", "scipy"),
        ("numpy", "numpy"),
        ("pynput", "pynput"),
    ]
    
    for pkg, import_name in packages:
        if not check_package(pkg, import_name):
            all_ok = False
    
    print()
    
    # Überprüfe optionale Pakete
    print(f"{Colors.BLUE}📦 Optionale Pakete:{Colors.END}")
    
    optional = [
        ("openai-whisper", "whisper"),
    ]
    
    for pkg, import_name in optional:
        check_package(pkg, import_name)
    
    print()
    
    # Überprüfe Audiogeräte
    print(f"{Colors.BLUE}🎵 Audio-System:{Colors.END}")
    try:
        import sounddevice
        devices = sounddevice.query_devices()
        print(f"  Verfügbare Audiogeräte: {len(devices)}")
        
        # Finde Standardgeräte
        default_input = sounddevice.default.device[0]
        default_output = sounddevice.default.device[1]
        
        print(f"  Standard Input: {default_input}")
        print(f"  Standard Output: {default_output}")
        
        if default_input is not None:
            print(f"{Colors.GREEN}✓{Colors.END} Eingangsgerät konfiguriert")
        else:
            print(f"{Colors.YELLOW}⚠{Colors.END} Kein Eingangsgerät gefunden!")
            all_ok = False
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END} Fehler bei Audio-System Check: {e}")
        all_ok = False
    
    print()
    
    # Überprüfe Verzeichnisse
    print(f"{Colors.BLUE}📁 Verzeichnisse:{Colors.END}")
    audio_dir = Path("audio_recordings")
    if audio_dir.exists():
        print(f"{Colors.GREEN}✓{Colors.END} audio_recordings/ existiert")
    else:
        print(f"{Colors.YELLOW}ℹ{Colors.END} audio_recordings/ wird beim Start erstellt")
    
    print()
    
    # Zusammenfassung
    print("=" * 60)
    if all_ok:
        print(f"{Colors.GREEN}✅ Setup ist OK!{Colors.END}")
        print("Du kannst Jarvis jetzt starten mit: python3 Jarvis.py")
    else:
        print(f"{Colors.RED}❌ Es gibt noch Probleme!{Colors.END}")
        print("\nInstalliere fehlende Pakete mit:")
        print("  pip install -r requirements_jarvis.txt")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
