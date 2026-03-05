Dokumentation: 
REM-Karbid-Analysator Pro
Dieses Tool dient der automatisierten Analyse von Rasterelektronenmikroskop-Aufnahmen (REM), um Karbide (oder ähnliche Partikel) hinsichtlich ihrer Fläche, Verteilung und Geometrie auszuwerten.

🔬 Hauptfunktionen
Maßstabserkennung: Automatisches Scannen des unteren Bildbereichs nach einer Kalibrierungslinie zur Umrechnung von Pixeln in Mikrometer ($\mu m$).
Präzise Bildvorverarbeitung:
CLAHE: Adaptiver Kontrastverstärker zur Kompensation ungleichmäßiger Ausleuchtung.
Morphologisches Closing: Glättung von Partikelrändern und Schließen von Löchern innerhalb der erkannten Strukturen.
Manuelle Korrektur: Einstellbarer Bildbeschnitt (Crop), um Infoleisten am Bildrand vor der Messung zu entfernen.
Statistische Auswertung: Berechnung von Anzahl, mittlerer Fläche, kleinstem/größtem Partikel, Rundheit und Flächendichte pro $100 \mu m^2$.
Berichtswesen: Export der Einzeldaten als CSV und Erstellung eines PDF-Berichtes inklusive Statistik sowie Vorher-Nachher-Bildvergleich.

🛠 Technischer Stack
Programmiersprache: Python 3.10+
GUI-Framework: PyQt6 (für die interaktive Benutzeroberfläche)
Bildverarbeitung: OpenCV (Konturerkennung, Filter, Schwellwerte)
Datenanalyse: Pandas & NumPy
Visualisierung: Matplotlib
PDF-Generierung: FPDF2🚀 Installation für Entwickler
Um lokal am Code zu arbeiten, müssen folgende Abhängigkeiten installiert werden:
pip install PyQt6 PyQt6-Qt6 opencv-python numpy pandas matplotlib fpdf2

🏗 Kompilierung (Build-Prozess)
Das Programm wurde erfolgreich über GitHub Actions kompiliert, um DLL-Konflikte (insbesondere bei Conda-Umgebungen) zu vermeiden.
CI/CD: Der Workflow nutzt windows-latest und PyInstaller.
Wichtiger Hinweis: Beim Kompilieren muss das Matplotlib-Backend explizit auf QtAgg gesetzt und die Umgebungsvariable QT_API=pyqt6 definiert werden, um Laufzeitfehler zu verhindern.

📖 Bedienungsanleitung
Bild laden: Über den Button "Bild laden" ein REM-Foto auswählen.
1. Maßstab: "Maßstab erkennen" klicken. Die erkannte Linie wird cyanfarben markiert. Den Realwert (z. B. $10 \mu m$) im Feld eintragen.
2. Zuschneiden: Den Slider "Crop unten" so weit erhöhen, bis die Infoleiste des Mikroskops im Bild nicht mehr sichtbar ist.
3. Feineinstellung: Schwellwert und CLAHE anpassen, bis die grünen Live-Konturen die Karbide optimal umschließen.
4. Messung starten: Führt die statistische Analyse mit den eingestellten Parametern durch.
5. Export: Speichert die Ergebnisse im gewählten Zielordner.

📝 Lizenz & Kontakt
Erstellt von Johannes Werner. Dieses Tool wurde für metallografische Analysen optimiert.
