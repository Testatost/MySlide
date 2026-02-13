# MySlide

**MySlide** ist eine moderne Diashow-App (PySide6/Qt) für Linux, die **Bilder und Videos** aus einem Ordner abspielt.  
Sie unterstützt **Drag & Drop**, **Zufall**, **Dauerschleife**, **Filter**, **Hell-/Dunkelmodus**, **Vollbild nur für Medien** und eine **Video-Zeitleiste (Seekbar)** mit **Click-to-seek** und **Drag**.

---

## Features

- ✅ Unterstützt gängige Formate:
  - **Bilder:** JPG, JPEG, PNG, BMP, GIF, WEBP, TIF, TIFF
  - **Videos:** MP4, MKV, AVI, MOV, WEBM, MPEG, MPG, M4V
- ✅ Ordner auswählen (Menü oder Shortcut)
- ✅ **Reihenfolge** oder **Zufallsmodus**
- ✅ **Filter:**
  - Alles
  - Nur ausgewähltes
  - Nur Bilder
  - Nur Videos
- ✅ **Auswahlmodus:** Dateien in der Liste an-/abhaken („Nur ausgewähltes“)
- ✅ **Bild-Timer** einstellbar (0 = Standard 10 Sekunden)
  - Hinweis: Timer gilt **nur für Bilder**, Videos laufen in voller Länge
- ✅ **Dauerschleife** (standardmäßig aktiviert)
- ✅ **Vollbild-Modus** zeigt **nur Bilder/Videos**, nicht das Programm
- ✅ **Video-Seekbar** unten im Bild:
  - erscheint bei Mausbewegung
  - verschwindet nach **2 Sekunden** ohne Mausbewegung
  - bleibt sichtbar, solange die Maus auf der Seekbar ist
  - **Click-to-seek** + **Drag** (roter Regler)
- ✅ **Hilfe** als Hover-Popup im Menü (kein neues Fenster)
- ✅ Drag & Drop in:
  - Warteliste (linke Liste)
  - Vorschau-/Anzeige-Bereich (rechts)
- ✅ Vollbild-Wechsel bei Video ohne Neustart (Position bleibt erhalten)

---

## Screenshots

*(Optional: hier kannst du später Screenshots einfügen)*

```text
📌 Tipp: Einfach ein Screenshot in GitHub hochladen und hier einfügen.

Installation
Voraussetzungen

    Linux (z. B. Linux Mint, Fedora, Ubuntu, KDE Plasma etc.)

    Python 3

    FFmpeg wird empfohlen (für bestmögliche Video-Kompatibilität)

1) Projekt klonen

git clone https://github.com/DEIN-USERNAME/MintSlide.git
cd MintSlide

2) Virtuelle Umgebung erstellen und aktivieren

python3 -m venv .venv
source .venv/bin/activate

3) Abhängigkeiten installieren

python -m pip install --upgrade pip
python -m pip install PySide6

    Optional (empfohlen), falls dein System FFmpeg nicht installiert hat:

Debian/Ubuntu/Mint:

sudo apt update
sudo apt install -y ffmpeg

Fedora:

sudo dnf install -y ffmpeg

Starten

source .venv/bin/activate
python main.py

Bedienung
Ordner laden

    Menü: Datei → Ordner öffnen…

    Shortcut: Strg+O

    Oder: Ordner/Dateien per Drag & Drop in die Liste oder den Vorschau-Bereich ziehen

Abspielen

    Leertaste: Start / Pause / Weiter

    Stopp: Stoppt die komplette Diashow

Navigation

    Pfeil links/rechts: Vor/Zurück (auch im Vollbild)

Vollbild (nur Medium)

    Strg+V oder F12: Vollbild an/aus

    Esc: Vollbild verlassen

Video-Seekbar

    Seekbar erscheint bei Mausbewegung im Video

    verschwindet nach 2 Sekunden ohne Mausbewegung

    Klick auf Leiste springt zur Position

    Roter Regler ist per Drag verschiebbar

Tastenkürzel (Shortcut-Übersicht)
Aktion	Shortcut
Ordner öffnen	Strg+O
Start / Pause / Weiter	Leertaste
Stopp	Strg+S
Zurück	Pfeil links
Weiter	Pfeil rechts
Dauerschleife an/aus	Strg+R
Zufall an/aus	Strg+Z
Vollbild an/aus (nur Medium)	Strg+V oder F12
Vollbild verlassen	Esc
