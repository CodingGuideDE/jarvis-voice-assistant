#!/bin/bash

# Quick Start Script für Jarvis Voice Assistant
# Dieses Skript installiert alle Abhängigkeiten und startet Jarvis

set -e

echo "════════════════════════════════════════════════════════════"
echo "🤖 Jarvis - Voice Assistant - Quick Start Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Schritt 1: Python-Version überprüfen
echo -e "${BLUE}📋 Überprüfe Python-Version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version gefunden"
echo ""

# Schritt 2: Überprüfe ob pip installiert ist
echo -e "${BLUE}📦 Überprüfe pip...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 nicht gefunden! Bitte installiere Python mit pip.${NC}"
    exit 1
fi
echo "✓ pip3 gefunden"
echo ""

# Schritt 3: Installiere Abhängigkeiten
echo -e "${BLUE}📥 Installiere Abhängigkeiten...${NC}"
echo "Dies kann einige Minuten dauern..."
echo ""

# Installiere die Pakete
pip3 install -q pynput || {
    echo -e "${RED}❌ Fehler bei pynput Installation${NC}"
    exit 1
}
echo "✓ pynput installiert"

# Whisper Installation - kann länger dauern
echo ""
echo -e "${YELLOW}⏳ Installiere OpenAI Whisper (kann 5-10 Minuten dauern)...${NC}"
pip3 install -q openai-whisper || {
    echo -e "${YELLOW}⚠️  Whisper konnte nicht installiert werden.${NC}"
    echo "   Audio wird aufgezeichnet, aber nicht transkribiert."
    echo ""
}
echo "✓ Whisper (teilweise) vorbereitet"

echo ""
echo -e "${BLUE}✅ Installation abgeschlossen!${NC}"
echo ""

# Schritt 4: Starte Jarvis
echo "════════════════════════════════════════════════════════════"
echo -e "${GREEN}🚀 Starte Jarvis...${NC}"
echo "════════════════════════════════════════════════════════════"
echo ""

# Navigiere zum Jarvis-Verzeichnis und starte
cd "$(dirname "$0")"
python3 Jarvis.py
