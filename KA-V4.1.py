# -*- coding: utf-8 -*-
import os
import sys

# Falls wir in einer EXE sind, erzwinge den Pfad zum aktuellen Ordner für DLLs
if getattr(sys, 'frozen', False):
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'platforms')

# Matplotlib-Absicherung
os.environ["QT_API"] = "pyqt6"
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSpinBox, 
                             QDoubleSpinBox, QFileDialog, QTextEdit, QGroupBox)

import cv2
import numpy as np
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class REMAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("REM-Karbid-Analysator Pro v4.2")
        self.resize(1400, 900)

        # Globale Daten-Speicher
        self.img_full = None       # Das geladene Originalbild
        self.img_display = None    # Aktuelles Vorschaubild (für PDF)
        self.file_path = ""
        self.scale_coords = None   # Koordinaten der Skala
        self.results_df = None
        self.analysis_stats = {}

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- LINKE SEITE ---
        controls_layout = QVBoxLayout()
        
        file_group = QGroupBox("Aktionen")
        file_vbox = QVBoxLayout()
        self.btn_load = QPushButton("1. Bild laden ⬆️")
        self.btn_load.clicked.connect(self.load_image)
        self.btn_detect_scale = QPushButton("2. Maßstab erkennen 🔍")
        self.btn_detect_scale.clicked.connect(self.action_detect_scale)
        self.btn_apply_crop = QPushButton("3. Unteren Rand abschneiden  ✂️")
        self.btn_apply_crop.clicked.connect(self.update_preview)
        self.btn_measure = QPushButton("4. Messung starten ▶️")
        self.btn_measure.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold; height: 40px;")
        self.btn_measure.clicked.connect(self.run_measurement)
        self.btn_export = QPushButton("5. Bericht (PDF) & CSV")
        self.btn_export.setStyleSheet("background-color: #1565c0; color: white;")
        self.btn_export.clicked.connect(self.export_all)
        
        for btn in [self.btn_load, self.btn_detect_scale, self.btn_apply_crop, self.btn_measure, self.btn_export]:
            file_vbox.addWidget(btn)
        file_group.setLayout(file_vbox)

        param_group = QGroupBox("Parameter")
        param_grid = QVBoxLayout()
        self.spin_crop = QSpinBox(); self.spin_crop.setRange(0, 2000); self.spin_crop.setValue(100)
        self.spin_threshold = QSpinBox(); self.spin_threshold.setRange(0, 255); self.spin_threshold.setValue(190)
        self.spin_min_area = QSpinBox(); self.spin_min_area.setRange(1, 10000); self.spin_min_area.setValue(10)
        self.spin_scale_px = QDoubleSpinBox(); self.spin_scale_px.setRange(1, 10000); self.spin_scale_px.setValue(200)
        self.spin_scale_um = QDoubleSpinBox(); self.spin_scale_um.setRange(0.1, 10000); self.spin_scale_um.setValue(10.0)
        self.spin_clahe = QDoubleSpinBox(); self.spin_clahe.setRange(0.0, 10.0); self.spin_clahe.setValue(2.0)
        self.spin_morph = QSpinBox(); self.spin_morph.setRange(1, 31); self.spin_morph.setSingleStep(2); self.spin_morph.setValue(3)
        
        for widget in [QLabel("Pixel am unteren Rand entfernen:"), self.spin_crop, QLabel("Schwellwert:"), self.spin_threshold, QLabel("Min. Fläche (px²):"), 
                       self.spin_min_area, QLabel("Kontrast (CLAHE):"), self.spin_clahe, QLabel("Glättung (MorphKernel px):"), self.spin_morph,
                       QLabel("Maßstab (px):"), self.spin_scale_px, QLabel("Realwert (µm):"), self.spin_scale_um]:
            param_grid.addWidget(widget)
        param_group.setLayout(param_grid)

        self.result_log = QTextEdit(); self.result_log.setReadOnly(True)
        controls_layout.addWidget(file_group); controls_layout.addWidget(param_group)
        controls_layout.addWidget(QLabel("Ergebnisse:")); controls_layout.addWidget(self.result_log)
        main_layout.addLayout(controls_layout, 1)

        # --- RECHTE SEITE ---
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas, 3)

    # --- LOGIK ---

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Bild laden", "", "Bilder (*.png *.jpg *.tif *.bmp)")
        if path:
            self.file_path = path
            # 1. Bild absolut roh einlesen
            self.img_full = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            
            # 2. Alle Zwischenspeicher zurücksetzen
            self.scale_coords = None
            self.results_df = None
            
            # 3. Protokoll aktualisieren
            h, w = self.img_full.shape
            self.result_log.setText(f"Datei geladen: {os.path.basename(path)}\nAuflösung: {w} x {h} px")
            
            # 4. Anzeige auf das volle Bild setzen (ohne Crop-Logik)
            self.show_full_image()

    def show_full_image(self):
        """Zeigt das Bild ohne jeglichen Beschnitt oder Filter an."""
        if self.img_full is None: return
        
        self.ax.clear()
        # Wir zeigen das Originalbild in Graustufen an
        self.ax.imshow(self.img_full, cmap='gray')
        self.ax.axis('off')
        self.canvas.draw()

    def action_detect_scale(self):
        if self.img_full is None: return
        h, w = self.img_full.shape
        # Suche im unteren Bereich des Bildes
        search_height = int(h * 0.2)
        search_area = self.img_full[h-search_height:, :]
        max_len = 0
        best_line = None # (sx, sy, ex, ey)
        
        min_brightness = np.max(search_area) * 0.8 
        _, thresh_area = cv2.threshold(search_area, min_brightness, 255, cv2.THRESH_BINARY)

        # Konturen im binären Suchbereich finden
        contours, _ = cv2.findContours(thresh_area, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for c in contours:
            x, y_rel, w_c, h_c = cv2.boundingRect(c)
            # Eine Skalenlinie ist breit (mind. 5% Bildbreite) aber sehr flach (max 10px hoch)
            if w_c > (w * 0.05) and h_c < 15:
                if w_c > max_len:
                    max_len = w_c
                    # Umrechnung der relativen y-Koordinate zurück aufs Vollbild
                    abs_y = y_rel + (h - search_height) + (h_c // 2)
                    best_line = (x, abs_y, x + w_c, abs_y)

        if best_line:
            self.scale_coords = best_line
            self.spin_scale_px.setValue(float(max_len))
            self.result_log.append(f"✅ Skala gefunden: {max_len} px bei y={best_line[1]}")
            self.draw_scale_on_full_image()
        else:
            self.result_log.append("❌ Maßstab nicht gefunden. (Tipp: Ist der Bereich zu dunkel?)")

    def draw_scale_on_full_image(self):
        """Zeigt das Vollbild mit der markierten Skala in Cyan."""
        if self.img_full is None or self.scale_coords is None: return
        
        sx, sy, ex, ey = self.scale_coords
        
        # Kopie für die Anzeige erstellen
        display_img = cv2.cvtColor(self.img_full, cv2.COLOR_GRAY2RGB)
        # Dicke Linie einzeichnen
        cv2.line(display_img, (sx, sy), (ex, ey), (255, 0, 0), 6)
        # Text hinzufügen
        cv2.putText(display_img, f"DETECTED: {ex-sx}px", (sx, sy-20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3)

        self.ax.clear()
        self.ax.imshow(display_img)
        self.ax.axis('off')
        self.canvas.draw()

    def update_preview(self, draw_scale=False):
        if self.img_full is None: return
        
        # Crop anwenden
        h, w = self.img_full.shape
        crop_val = self.spin_crop.value()
        img_cropped = self.img_full[:h-crop_val, :] if crop_val < h else self.img_full
        
        # Kontrast für Anzeige
        clahe = cv2.createCLAHE(clipLimit=self.spin_clahe.value(), tileGridSize=(8, 8))
        enhanced = clahe.apply(img_cropped)
        
        # 3. Schwellwert (Threshold) und Morphologie für die Live-Vorschau
        _, binary = cv2.threshold(enhanced, self.spin_threshold.value(), 255, cv2.THRESH_BINARY)
        k_size = self.spin_morph.value()
        if k_size % 2 == 0: k_size += 1 
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
        binary_closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 4. Anzeige vorbereiten
        self.ax.clear()
        display_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        
        # 5. Live-Konturen einzeichnen (Grün)
        contours, _ = cv2.findContours(binary_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = self.spin_min_area.value()
        for cnt in contours:
            if cv2.contourArea(cnt) >= min_area:
                cv2.drawContours(display_rgb, [cnt], -1, (0, 255, 0), 1)

        # 6. Skala einzeichnen, falls gewünscht
        if draw_scale and self.scale_coords:
            sx, sy, ex, ey = self.scale_coords
            # Nur zeichnen, wenn die Skala nicht weggecroppt wurde
            if sy < (h - crop_val):
                cv2.line(display_rgb, (sx, sy), (ex, ey), (255, 0, 0), 5) # rot
        
        # 7. Finales Bild im GUI-Canvas anzeigen
        self.ax.imshow(display_rgb)
        self.ax.axis('off')
        self.canvas.draw()
        self.img_display = display_rgb

    def run_measurement(self):
        if self.img_full is None: return
        
        # 1. Bild vorbereiten (Crop & Filter)
        h_orig, w_orig = self.img_full.shape
        crop_v = self.spin_crop.value()
        img_work = self.img_full[:h_orig-crop_v, :]
        h_w, w_w = img_work.shape
        
        clahe = cv2.createCLAHE(clipLimit=self.spin_clahe.value(), tileGridSize=(8, 8))
        enhanced = clahe.apply(img_work)
        _, binary = cv2.threshold(enhanced, self.spin_threshold.value(), 255, cv2.THRESH_BINARY)
        k_size = self.spin_morph.value()
        if k_size % 2 == 0: k_size += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary_closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # 2. Skalierung
        scale_px = self.spin_scale_px.value()
        scale_um = self.spin_scale_um.value()
        um_per_px = scale_um / scale_px
        um2_per_px2 = um_per_px ** 2
        
        # 3. Konturanalyse
        contours, _ = cv2.findContours(binary_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        res = []
        min_a = self.spin_min_area.value()
        vis_img = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        
        for cnt in contours:
            a_px = cv2.contourArea(cnt)
            if a_px >= min_a:
                peri = cv2.arcLength(cnt, True)
                roundness = (4 * np.pi * a_px) / (peri**2) if peri > 0 else 0
                res.append({'area_px': a_px, 'area_um2': a_px * um2_per_px2, 'roundness': roundness})
                cv2.drawContours(vis_img, [cnt], -1, (0, 255, 0), -1)

        self.results_df = pd.DataFrame(res)
        
        # 4. Statistik für den Bericht
        total_a_um2 = (h_w * w_w) * um2_per_px2
        carb_a_um2 = self.results_df['area_um2'].sum() if not self.results_df.empty else 0
        
        self.analysis_stats = {
            "Bild": os.path.basename(self.file_path),
            "Gecropptes Bild": f"{w_w} x {h_w} px",
            "Schwellwert": self.spin_threshold.value(),
            "Min. Fläche": f"{min_a}px²",
            "MorphKernel": f"{k_size}px",
            "CLAHE": self.spin_clahe.value(),
            "Skalierung": f"{scale_px} px = {scale_um} µm -> {um_per_px:.6f} µm/px",
            "Anzahl Karbide": len(self.results_df),
            "Gesamtfläche Karbide": f"{carb_a_um2:.4f} µm² ({int(self.results_df['area_px'].sum() if not self.results_df.empty else 0)} px²)",
            "Analysierte Fläche": f"{total_a_um2:.4f} µm² ({h_w*w_w} px²)",
            "Karbide pro 100 µm²": f"{(len(self.results_df)/total_a_um2*100):.4f}" if total_a_um2 > 0 else "0",
            "Flächenanteil Karbide": f"{(carb_a_um2/total_a_um2*100):.4f}%" if total_a_um2 > 0 else "0",
            "Mittlere Karbidfläche": f"{self.results_df['area_um2'].mean():.4f} µm²" if not self.results_df.empty else "0",
            "Kleinste Fläche": f"{self.results_df['area_um2'].min():.4f} µm²" if not self.results_df.empty else "0",
            "Größte Fläche": f"{self.results_df['area_um2'].max():.4f} µm²" if not self.results_df.empty else "0",
            "Mittlere Rundheit": f"{self.results_df['roundness'].mean():.4f}" if not self.results_df.empty else "0"
        }
        
        # Log-Ausgabe
        self.result_log.clear()
        for k, v in self.analysis_stats.items():
            self.result_log.append(f"{k}: {v}")
        
        # Anzeige aktualisieren
        self.ax.clear(); self.ax.imshow(vis_img); self.ax.axis('off'); self.canvas.draw()
        self.img_display = vis_img

    def export_all(self):
        if self.results_df is None: self.result_log.append("❌ Bitte zuerst eine Messung durchführen!"); return
        folder = QFileDialog.getExistingDirectory(self, "Speicherort wählen")
        if not folder: return
        
        base = os.path.splitext(os.path.basename(self.file_path))[0]
        
        # 1. CSV Export
        self.results_df.to_csv(os.path.join(folder, f"{base}_daten.csv"), sep=";", index=False)
        
        # 2. PDF Bericht
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(0, 10, "REM Karbid-Analysebericht", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        
        pdf.set_font("helvetica", size=10)
        for k, v in self.analysis_stats.items():
            pdf.cell(50, 6, f"{k}:"); pdf.cell(0, 6, f"{v}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        tmp_analysiert = os.path.join(folder, "temp_analysiert.jpg")
        tmp_original = os.path.join(folder, "temp_original.jpg")
        
        # Analysiertes Bild speichern (aus self.img_display)
        plt.imsave(tmp_analysiert, self.img_display)
        # Originalbild speichern (das gecroppte Original ohne Markierungen)
        h, w = self.img_full.shape
        crop_v = self.spin_crop.value()
        img_work = self.img_full[:max(1, h-crop_v), :]
        cv2.imwrite(tmp_original, img_work)
        
        # Seite 1: Analysiertes Bild
        pdf.ln(5)
        pdf.set_font("helvetica", 'B', 10)
        pdf.cell(0, 10, "Analysiertes Bild (Karbide markiert):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.image(tmp_analysiert, x=10, w=185)
        
        # Seite 2: Originalbild
        pdf.add_page()
        pdf.cell(0, 10, "Originalbild (Referenz):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.image(tmp_original, x=10, w=185)
        
        pdf.output(os.path.join(folder, f"{base}_Bericht.pdf"))
        
        # Aufräumen
        os.remove(tmp_analysiert)
        os.remove(tmp_original)
        
        self.result_log.append("\n--- Export abgeschlossen! ---")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = REMAnalyzer(); win.show(); sys.exit(app.exec())