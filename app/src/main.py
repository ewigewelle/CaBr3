import sys
import os
import json
import base64
import re
import logging
import time

# Core PySide6 imports needed for basic structure
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QFrame, QStackedWidget, QFileDialog,
    QHeaderView, QListWidget, QListWidgetItem, QAbstractItemView, 
    QGraphicsDropShadowEffect, QScrollArea, QCheckBox, QMessageBox,
    QSplashScreen, QDialog, QFormLayout
)
from PySide6.QtGui import QPixmap, QIcon, QColor
from PySide6.QtCore import Qt, QSize, QPoint, Signal, QTimer

# Local imports
# Removed GestisClient from here to speed up startup (now lazy-loaded)

def get_hp_library():
    try:
        from hp_library import HP_LIBRARY_DE
        return HP_LIBRARY_DE
    except ImportError:
        return {}

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.join(os.path.dirname(__file__), "..")
    return os.path.abspath(os.path.join(base_path, relative_path))

STYLES = """
QMainWindow, QDialog { background-color: #f0f2f5; }
QWidget#Sidebar { background-color: #1a252f; min-width: 80px; max-width: 80px; }
QPushButton#SidebarBtn { background-color: transparent; border: none; color: #95a5a6; padding: 20px; font-size: 24px; }
QPushButton#SidebarBtn:hover { background-color: #2c3e50; color: white; }
QPushButton#SidebarBtn[active="true"] { background-color: #3498db; color: white; }
QFrame#Card { background-color: white; border-radius: 8px; border: 1px solid #dcdfe6; margin-bottom: 10px; }
QLabel#SectionTitle { font-size: 15px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }
QLineEdit, QTextEdit { border: 1px solid #dcdfe6; border-radius: 4px; padding: 10px; background-color: #ffffff; color: #303133; font-size: 13px; }
QLineEdit:focus { border: 1px solid #409eff; }
QPushButton#ActionBtn { background-color: #3498db; color: white; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; }
QPushButton#DangerBtn { background-color: #f56c6c; color: white; border: none; border-radius: 4px; padding: 8px 15px; font-weight: bold; }
QPushButton#ExportBtn { background-color: #e67e22; color: white; border: none; border-radius: 4px; padding: 12px 25px; font-weight: bold; }
QTableWidget { background-color: white; alternate-background-color: #f9fafc; border: 1px solid #ebeef5; gridline-color: #ebeef5; color: #303133; }
QHeaderView::section { background-color: #f5f7fa; color: #606266; padding: 10px; border: none; border-bottom: 1px solid #ebeef5; font-weight: bold; }
QListWidget#SearchResults { background-color: white; border: 1px solid #dcdfe6; border-radius: 4px; color: black; }
QListWidget#SearchResults::item { padding: 10px; border-bottom: 1px solid #f0f2f5; color: black; }
QListWidget#SearchResults::item:hover { background-color: #f5f7fa; color: black; }
QListWidget#SearchResults::item:selected { background-color: #ecf5ff; color: #409eff; }

QCheckBox { color: #606266; font-size: 13px; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #dcdfe6; border-radius: 4px; background: white; }
QCheckBox::indicator:checked { background-color: #3498db; border-color: #3498db; }
QCheckBox::indicator:hover { border-color: #3498db; }
QPushButton#SecondaryBtn { background-color: #67c23a; color: white; border: none; border-radius: 4px; padding: 10px 20px; font-weight: bold; }
QMessageBox { background-color: white; }
QMessageBox QLabel { color: #303133; font-size: 14px; }
QMessageBox QPushButton { background-color: #f0f2f5; border: 1px solid #dcdfe6; border-radius: 4px; padding: 6px 15px; color: #303133; min-width: 80px; }
QMessageBox QPushButton:hover { background-color: #e4e7ed; }
"""

class CustomSubstanceDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Eigenen Stoff hinzufügen" if not data else "Stoff bearbeiten")
        
        # Dynamic sizing based on screen resolution
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(800, int(screen.width() * 0.8))
        h = min(900, int(screen.height() * 0.9))
        self.resize(w, h)
        
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: white;")
        self.scroll_layout = QVBoxLayout(scroll_content)
        
        self.in_name = DynamicListWidget("Stoff / CAS / Formel")
        self.in_mg = QLineEdit()
        self.in_sdp = DynamicListWidget("Sdp. / Smp.")
        
        # GHS Selector
        self.ghs_selectors = {}
        ghs_container = QWidget()
        ghs_vbox = QVBoxLayout(ghs_container)
        ghs_vbox.addWidget(QLabel("GHS-Symbole auswählen:", objectName="SectionTitle"))
        ghs_grid = QHBoxLayout()
        for i in range(1, 10):
            code = f"ghs0{i}"
            item_vbox = QVBoxLayout()
            img_lbl = QLabel()
            img_path = get_resource_path(f"assets/ghs_symbols/{code}.png")
            if os.path.exists(img_path):
                pix = QPixmap(img_path).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl.setPixmap(pix)
            img_lbl.setAlignment(Qt.AlignCenter)
            cb = QCheckBox()
            cb.setStyleSheet("margin-left: 20px;") # Center checkbox roughly
            item_vbox.addWidget(img_lbl)
            item_vbox.addWidget(cb)
            ghs_grid.addLayout(item_vbox)
            self.ghs_selectors[code] = cb
        ghs_vbox.addLayout(ghs_grid)
        
        self.in_hp = DynamicListWidget("H/P-Sätze (Nummern)")
        self.in_info = DynamicListWidget("Zusatzinfos (MAK, LD50, WGK)")
        
        if data:
            for x in data.get("name", "").split("\n"):
                self.in_name.add_row(x)
            self.in_mg.setText(data.get("mg", ""))
            for x in data.get("sdp", "").split("\n"):
                self.in_sdp.add_row(x)
            for g in data.get("ghs", "").split(","):
                g = g.strip().lower()
                if g in self.ghs_selectors:
                    self.ghs_selectors[g].setChecked(True)
            for x in data.get("hp", "").split("\n"):
                self.in_hp.add_row(x)
            for x in data.get("info", "").split("\n"):
                self.in_info.add_row(x)
        else:
            # Add initial rows only if new
            self.in_name.add_row("")
            self.in_sdp.add_row("")
            self.in_hp.add_row("")
            self.in_info.add_row("")

        self.scroll_layout.addWidget(self.in_name)
        
        mg_box = QWidget()
        mgl = QVBoxLayout(mg_box)
        mgl.addWidget(QLabel("MG [g/mol]:", objectName="SectionTitle"))
        mgl.addWidget(self.in_mg)
        
        self.scroll_layout.addWidget(mg_box)
        self.scroll_layout.addWidget(self.in_sdp)
        self.scroll_layout.addWidget(ghs_container)
        self.scroll_layout.addWidget(self.in_hp)
        self.scroll_layout.addWidget(self.in_info)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        btns = QHBoxLayout()
        btn_ok = QPushButton("Speichern" if data else "Hinzufügen")
        btn_ok.setObjectName("ActionBtn")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        layout.addLayout(btns)
        self.setStyleSheet(STYLES + " QDialog { background-color: white; }")

class DynamicListRow(QWidget):
    changed = Signal()
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        # Ensure text is string and not the boolean from 'clicked' signal
        if not isinstance(text, str): text = ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.dot = QLabel("•")
        self.dot.setFixedWidth(15)
        self.edit = QLineEdit(text)
        self.edit.setFrame(False)
        self.edit.setStyleSheet("border-bottom: 1px solid #dcdfe6; background: transparent; color: #303133;")
        self.btn_del = QPushButton("⊖")
        self.btn_del.setFixedWidth(30)
        self.btn_del.setStyleSheet("color: #f56c6c; border: none; font-size: 18px;")
        layout.addWidget(self.dot)
        layout.addWidget(self.edit)
        layout.addWidget(self.btn_del)
        self.edit.textChanged.connect(lambda: self.changed.emit())

class DynamicListWidget(QWidget):
    changed = Signal()
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title, objectName="SectionTitle")
        self.layout.addWidget(self.title_label)
        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.layout.addWidget(self.rows_container)
        self.btn_add = QPushButton("⊕")
        self.btn_add.setFixedWidth(30)
        self.btn_add.setStyleSheet("color: #67c23a; border: none; font-size: 20px;")
        self.btn_add.clicked.connect(lambda: self.add_row(""))
        self.layout.addWidget(self.btn_add)
        self.rows = []

    def add_row(self, text=""):
        if not isinstance(text, str): text = ""
        row = DynamicListRow(text)
        row.btn_del.clicked.connect(lambda: self.remove_row(row))
        row.changed.connect(lambda: self.changed.emit())
        self.rows_layout.addWidget(row)
        self.rows.append(row)
        self.changed.emit()
        return row

    def remove_row(self, row):
        self.rows_layout.removeWidget(row)
        self.rows.remove(row)
        row.deleteLater()
        self.changed.emit()

    def get_text_list(self):
        return [r.edit.text() for r in self.rows if r.edit.text().strip()]

class CaBr3App(QMainWindow):
    def __init__(self, splash=None, start_time=None):
        super().__init__()
        self.splash = splash
        self.start_time = start_time
        self._update_splash("Initialisiere...", 10)
        self.setWindowTitle("CaBr3 - Betriebsanweisungsgenerator")
        
        # Load logo for window icon lazily or early? Early is fine.
        self.setWindowIcon(QIcon(get_resource_path("assets/logo.png")))
        
        self._update_splash("Lade UI...", 20)
        # Dynamic sizing
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(1600, int(screen.width() * 0.9))
        h = min(950, int(screen.height() * 0.9))
        self.resize(w, h)
        self.setStyleSheet(STYLES)
        
        # Lazy client initialization
        self._client = None
        self.hp_library = {}
        self.data = {
            "header": "Betriebsanweisungen nach EG Nr. 1272/2008 für chemische Laboratorien der Universität Regensburg",
            "praktikum": "Praktikum Anorganische Chemie",
            "assistent": "Frau Max", "name": "Max Mustermann", "platz": "1",
            "praeparat": "Musterpräparat", "stoffe": [],
            "gefahren": [
                "Haut- und Augenkontakt vermeiden.",
                "Einatmen von Dämpfen/Aerosolen vermeiden.",
                "Zündquellen fernhalten - Nicht rauchen.",
                "Gefahr durch Hautabsorption.",
                "Stoffe können krebserzeugend oder fruchtschädigend sein.",
                "Entwickelt bei Kontakt mit Wasser entzündbare Gase.",
                "Wirkt ätzend auf Haut und Schleimhäute.",
                "Umweltgefährlich: Nicht in die Kanalisation gelangen lassen.",
                "Gefahr durch Staubbildung.",
                "Explosionsgefahr bei Erwärmung."
            ],
            "schutzmassnahmen": [
                "Schutzbrille und Chemikalienschutzhandschuhe tragen.",
                "Im Abzug arbeiten.",
                "Hände nach Gebrauch gründlich waschen.",
                "Verschüttete Substanz sofort aufnehmen.",
                "Laborkittel geschlossen tragen.",
                "Essen, Trinken und Rauchen am Arbeitsplatz verboten.",
                "Persönliche Schutzausrüstung vor Verlassen des Labors ablegen.",
                "Bei Staubbildung Atemschutz tragen.",
                "Augendusche und Notdusche bereithalten.",
                "Hände desinfizieren und Hautschutzcreme verwenden."
            ],
            "verhalten": [
                "Nach Augenkontakt: Mit reichlich Wasser bei geöffnetem Lidspalt spülen. Arzt zuziehen.",
                "Nach Einatmen: An die frische Luft bringen. Bei Beschwerden Arzt zuziehen.",
                "Nach Hautkontakt: Mit viel Wasser abwaschen. Kontaminierte Kleidung entfernen.",
                "Nach Verschlucken: Mund ausspülen. Kein Erbrechen herbeiführen. Arzt zuziehen.",
                "Bei Brand: CO2-Löscher oder Pulverlöscher verwenden. Kein Wasser bei Metallbränden.",
                "Notruf absetzen (Tel. 112). Unfallmeldung an Vorgesetzte.",
                "Evakuierung des Bereichs bei größeren Leckagen.",
                "Feuerlöscher und Not-Aus-Schalter betätigen."
            ],
            "entsorgung": [
                "Abfälle in die entsprechenden Sammelbehälter geben.",
                "Sammelbehälter für organische Lösungsmittel nutzen (halogenfrei/halogenhaltig).",
                "Feststoffe getrennt in Feststoffbehälter entsorgen.",
                "Wässrige Lösungen neutralisiert in den Ausguss geben (sofern zulässig).",
                "Verunreinigte Verpackungen wie das Produkt entsorgen.",
                "Schwermetallabfälle gesondert sammeln.",
                "Lösungsmittelabfälle in Kunststoffbehälter füllen.",
                "Besondere Entsorgungsvorschriften für radioaktive Stoffe beachten."
            ]
        }
        self._update_splash("Erstelle Benutzeroberfläche... 50%", 50)
        self.init_ui()
        self._update_splash("Bereite Vorschau vor... 70%", 70)
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._do_update_preview)
        
        # Defer data loading to show UI faster
        QTimer.singleShot(10, self._deferred_startup)
        
        # Initial splitter ratio 1:1 based on current width
        half_w = self.width() // 2
        self.splitter.setSizes([half_w, half_w])

    @property
    def client(self):
        if self._client is None:
            try:
                from gestis_client import GestisClient
                self._client = GestisClient()
            except ImportError:
                class GestisClient:
                    def search(self, *args, **kwargs): return []
                    def get_article(self, *args, **kwargs): return None
                self._client = GestisClient()
        return self._client

    def _deferred_startup(self):
        self._update_splash("Lade Standardwerte... 85%", 85)
        self.load_defaults()
        self._update_splash("Finalisiere... 95%", 95)
        
        # Ensure splash is visible for at least 3 seconds
        if self.splash and self.start_time:
            elapsed = time.time() - self.start_time
            remaining = max(0, 3.0 - elapsed)
            
            # Show 100% just before finishing
            def complete():
                self._update_splash("Bereit... 100%", 100)
                QTimer.singleShot(200, self._finish_splash)

            if remaining > 0:
                QTimer.singleShot(int(remaining * 1000), complete)
            else:
                complete()
        else:
            self._finish_splash()

    def _finish_splash(self):
        self.show()
        if self.splash:
            self.splash.finish(self)
            self.splash = None

    def _update_splash(self, msg, progress=None):
        if self.splash:
            self.splash.showMessage(msg, Qt.AlignBottom | Qt.AlignLeft, Qt.white)
            QApplication.instance().processEvents()

    def load_defaults(self):
        # Explicitly load defaults for each category to ensure nothing is missed
        categories = ["gefahren", "schutzmassnahmen", "verhalten", "entsorgung"]
        for attr in categories:
            if attr in self.dyn_widgets and attr in self.data:
                dw = self.dyn_widgets[attr]
                dw.blockSignals(True)
                for text in self.data[attr]:
                    dw.add_row(text)
                dw.blockSignals(False)
        self.sync_text() # Sync initial state to data and preview

    def create_shadow(self):
        # Disabled for better performance on weak PCs
        return None

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 10, 0, 10)

        self.btn_home = QPushButton("🏠")
        self.btn_home.setObjectName("SidebarBtn")
        self.btn_home.setProperty("active", True)

        self.btn_chem = QPushButton("🧪")
        self.btn_chem.setObjectName("SidebarBtn")

        self.btn_text = QPushButton("📝")
        self.btn_text.setObjectName("SidebarBtn")

        self.btn_save = QPushButton("💾")
        self.btn_save.setObjectName("SidebarBtn")
        self.btn_save.setToolTip("Projekt speichern")

        self.btn_load = QPushButton("📂")
        self.btn_load.setObjectName("SidebarBtn")
        self.btn_load.setToolTip("Projekt laden")

        side_layout.addWidget(self.btn_home)
        side_layout.addWidget(self.btn_chem)
        side_layout.addWidget(self.btn_text)
        side_layout.addSpacing(20)
        side_layout.addWidget(self.btn_save)
        side_layout.addWidget(self.btn_load)
        side_layout.addStretch()
        layout.addWidget(sidebar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(15, 15, 15, 15)
        self.init_pages()
        self.splitter.addWidget(self.stack)
        
        # Lazy load QWebEngineView
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(15, 15, 15, 15)
        self.btn_load_preview = QPushButton("Vorschau generieren")
        self.btn_load_preview.setObjectName("ExportBtn")
        self.btn_load_preview.setMinimumHeight(60)
        self.btn_load_preview.clicked.connect(self.lazy_init_preview)
        self.preview_layout.addStretch()
        self.preview_layout.addWidget(self.btn_load_preview, 0, Qt.AlignCenter)
        self.preview_layout.addStretch()
        self.preview = None
        
        self.splitter.addWidget(self.preview_container)
        layout.addWidget(self.splitter)

        self.results = QListWidget(self)
        self.results.setObjectName("SearchResults")
        self.results.setGraphicsEffect(self.create_shadow())
        self.results.hide()
        self.results.itemDoubleClicked.connect(self.add_from_search)
        
        self.btn_home.clicked.connect(lambda: self.switch_page(0))
        self.btn_chem.clicked.connect(lambda: self.switch_page(1))
        self.btn_text.clicked.connect(lambda: self.switch_page(2))
        self.btn_save.clicked.connect(self.save_project)
        self.btn_load.clicked.connect(self.load_project)

    def lazy_init_preview(self):
        self.btn_load_preview.setEnabled(False)
        self.btn_load_preview.setText("Vorschau wird generiert...")
        QApplication.processEvents()
        
        # Use a timer to allow the UI to update the button text before starting the heavy load
        QTimer.singleShot(50, self._do_lazy_init_preview)

    def _do_lazy_init_preview(self):
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.preview = QWebEngineView()
            self.preview.setStyleSheet("border-radius: 8px; background-color: white;")
            
            # Clear layout
            while self.preview_layout.count():
                item = self.preview_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            self.preview_layout.addWidget(self.preview)
            self.update_preview()
        except Exception as e:
            import logging
            logging.error(f"Failed to lazy init preview: {e}")
            QMessageBox.critical(self, "Fehler", f"Vorschau konnte nicht geladen werden: {e}")
            self.btn_load_preview.setEnabled(True)
            self.btn_load_preview.setText("Vorschau generieren")

    def init_pages(self):
        # Page 0: Kopfdaten
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        sl = QVBoxLayout(scroll_content)
        card = QFrame()
        card.setObjectName("Card")
        card.setGraphicsEffect(self.create_shadow())
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 20, 20, 20)
        cl.addWidget(QLabel("Kopfdaten", objectName="SectionTitle"))
        
        self.in_header = QLineEdit(self.data["header"])
        self.in_header.setPlaceholderText("Titel des Dokuments")
        self.in_praktikum = QLineEdit(self.data["praktikum"])
        self.in_assistent = QLineEdit(self.data["assistent"])
        self.in_name = QLineEdit(self.data["name"])
        self.in_platz = QLineEdit(self.data["platz"])
        self.in_praeparat = QLineEdit(self.data["praeparat"])
        
        fields = [
            ("Dokument-Titel:", self.in_header),
            ("Praktikum:", self.in_praktikum),
            ("Assistent:", self.in_assistent),
            ("Name:", self.in_name),
            ("Platz:", self.in_platz),
            ("Präparat:", self.in_praeparat)
        ]
        for lbl, w in fields:
            cl.addWidget(QLabel(lbl))
            cl.addWidget(w)
            w.textChanged.connect(self.sync_data)
        
        sl.addWidget(card)
        sl.addStretch()
        scroll.setWidget(scroll_content)
        l1.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        btn_export = QPushButton("ALS PDF EXPORTIEREN")
        btn_export.setObjectName("ExportBtn")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_export)
        l1.addLayout(btn_layout)
        btn_export.clicked.connect(self.export_pdf)
        self.stack.addWidget(p1)

        # Page 1: GESTIS Suche & Stoffliste
        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        scard = QFrame()
        scard.setObjectName("Card")
        scard.setGraphicsEffect(self.create_shadow())
        sl = QVBoxLayout(scard)
        sl.setContentsMargins(20, 20, 20, 20)
        sl.addWidget(QLabel("GESTIS Suche", objectName="SectionTitle"))
        
        hl = QHBoxLayout()
        self.search_in = QLineEdit()
        self.search_in.setPlaceholderText("Nach Stoff oder CAS suchen...")
        btn_s = QPushButton("Suchen")
        btn_s.setObjectName("ActionBtn")
        hl.addWidget(self.search_in)
        hl.addWidget(btn_s)
        sl.addLayout(hl)
        
        self.cb_exact = QCheckBox("Exakte Suche (nur voller Name / CAS)")
        sl.addWidget(self.cb_exact)
        l2.addWidget(scard)
        
        # Dropdown closure listener
        self.search_in.textChanged.connect(lambda t: self.results.hide() if not t else None)
        
        tcard = QFrame()
        tcard.setObjectName("Card")
        tcard.setGraphicsEffect(self.create_shadow())
        tl = QVBoxLayout(tcard)
        tl.setContentsMargins(15, 15, 15, 15)
        tl.addWidget(QLabel("Stoffliste", objectName="SectionTitle"))
        
        self.table = QTableWidget(0, 7)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header_labels = [
            "Stoff / CAS / Formel", "MG [g/mol]", "Sdp. Smp.", 
            "GHS-Symbole", "H/P-Sätze (Nummern)", "MAK LD50 WGK", 
            "für Ansatz benötigt"
        ]
        self.table.setHorizontalHeaderLabels(header_labels)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tl.addWidget(self.table)
        
        btn_row = QHBoxLayout()
        self.btn_del_sub = QPushButton("Stoff entfernen")
        self.btn_del_sub.setObjectName("DangerBtn")
        self.btn_del_sub.clicked.connect(self.remove_selected_substance)
        
        self.btn_edit_sub = QPushButton("Stoff bearbeiten")
        self.btn_edit_sub.setObjectName("ActionBtn")
        self.btn_edit_sub.clicked.connect(self.edit_selected_substance)
        
        self.btn_add_custom = QPushButton("Eigener Stoff")
        self.btn_add_custom.setObjectName("SecondaryBtn")
        self.btn_add_custom.clicked.connect(self.add_custom_substance)
        
        btn_row.addWidget(self.btn_del_sub)
        btn_row.addWidget(self.btn_edit_sub)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_add_custom)
        tl.addLayout(btn_row)
        
        l2.addWidget(tcard)
        btn_s.clicked.connect(self.do_search)
        self.search_in.returnPressed.connect(self.do_search)
        self.table.itemChanged.connect(self.sync_table)
        self.stack.addWidget(p2)

        # Page 2: Dynamische Texte
        p3 = QWidget()
        scroll_text = QScrollArea()
        scroll_text.setWidgetResizable(True)
        scroll_text.setFrameShape(QFrame.NoFrame)
        p3_content = QWidget()
        l3 = QVBoxLayout(p3_content)
        
        self.dyn_widgets = {}
        text_pages = [
            ("Gefahren für Mensch und Umwelt", "gefahren"),
            ("Schutzmaßnahmen und Verhaltensregeln", "schutzmassnahmen"),
            ("Verhalten im Gefahrenfall / Erste Hilfe", "verhalten"),
            ("Entsorgung", "entsorgung")
        ]
        for title, attr in text_pages:
            c = QFrame()
            c.setObjectName("Card")
            c.setGraphicsEffect(self.create_shadow())
            cl = QVBoxLayout(c)
            cl.setContentsMargins(15, 15, 15, 15)
            dw = DynamicListWidget(title)
            dw.changed.connect(self.sync_text)
            self.dyn_widgets[attr] = dw
            cl.addWidget(dw)
            l3.addWidget(c)
            
        scroll_text.setWidget(p3_content)
        main_p3_layout = QVBoxLayout(p3)
        main_p3_layout.setContentsMargins(0, 0, 0, 0)
        main_p3_layout.addWidget(scroll_text)
        self.stack.addWidget(p3)

    def switch_page(self, i):
        self.stack.setCurrentIndex(i)
        buttons = [self.btn_home, self.btn_chem, self.btn_text]
        for j, btn in enumerate(buttons):
            btn.setProperty("active", i == j)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.results.hide()

    def do_search(self):
        q = self.search_in.text()
        if not q: return
        res = self.client.search(q, exact=self.cb_exact.isChecked()); self.results.clear()
        if res:
            for it in res:
                li = QListWidgetItem(f"{it['name']} (CAS: {it.get('cas', 'N/A')})")
                li.setData(Qt.UserRole, it['id']); li.setForeground(QColor("#303133")); self.results.addItem(li)
            pos = self.search_in.mapTo(self, QPoint(0, self.search_in.height()))
            self.results.setGeometry(pos.x(), pos.y(), self.search_in.width(), 200)
            self.results.show(); self.results.raise_()

    def remove_selected_substance(self):
        it = self.table.currentRow()
        if it >= 0:
            self.table.removeRow(it)
            self.sync_table()
        else:
            QMessageBox.information(self, "Info", "Bitte wählen Sie zuerst einen Stoff in der Tabelle aus.")

    def edit_selected_substance(self):
        r = self.table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Info", "Bitte wählen Sie zuerst einen Stoff in der Tabelle aus.")
            return
        
        data = {
            "name": self.table.item(r, 0).text(),
            "mg": self.table.item(r, 1).text(),
            "sdp": self.table.item(r, 2).text(),
            "ghs": self.table.item(r, 3).text(),
            "hp": self.table.item(r, 4).text(),
            "info": self.table.item(r, 5).text()
        }
        
        dlg = CustomSubstanceDialog(self, data=data)
        if dlg.exec():
            self.table.blockSignals(True)
            self.table.setItem(r, 0, QTableWidgetItem("\n".join(dlg.in_name.get_text_list())))
            self.table.setItem(r, 1, QTableWidgetItem(dlg.in_mg.text() if dlg.in_mg.text() else "-"))
            self.table.setItem(r, 2, QTableWidgetItem("\n".join(dlg.in_sdp.get_text_list())))
            
            selected_ghs = [code for code, cb in dlg.ghs_selectors.items() if cb.isChecked()]
            self.table.setItem(r, 3, QTableWidgetItem(", ".join(selected_ghs)))
            
            self.table.setItem(r, 4, QTableWidgetItem("\n".join(dlg.in_hp.get_text_list())))
            self.table.setItem(r, 5, QTableWidgetItem("\n".join(dlg.in_info.get_text_list())))
            self.table.blockSignals(False)
            self.sync_table()

    def add_custom_substance(self):
        dlg = CustomSubstanceDialog(self)
        if dlg.exec():
            self.table.blockSignals(True)
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem("\n".join(dlg.in_name.get_text_list())))
            self.table.setItem(r, 1, QTableWidgetItem(dlg.in_mg.text() if dlg.in_mg.text() else "-"))
            self.table.setItem(r, 2, QTableWidgetItem("\n".join(dlg.in_sdp.get_text_list())))
            
            selected_ghs = [code for code, cb in dlg.ghs_selectors.items() if cb.isChecked()]
            self.table.setItem(r, 3, QTableWidgetItem(", ".join(selected_ghs)))
            
            self.table.setItem(r, 4, QTableWidgetItem("\n".join(dlg.in_hp.get_text_list())))
            self.table.setItem(r, 5, QTableWidgetItem("\n".join(dlg.in_info.get_text_list())))
            self.table.setItem(r, 6, QTableWidgetItem(""))
            self.table.blockSignals(False)
            self.sync_table()

    def add_from_search(self, it):
        art = self.client.get_article(it.data(Qt.UserRole))
        if art:
            from gestis_parser import GestisParser
            p = GestisParser.parse_article(art)
            if not p:
                return
            self.table.blockSignals(True)
            r = self.table.rowCount()
            self.table.insertRow(r)
            name_cas_formula = f"{p['name']}\n{p['cas']}\n{p['formula']}".strip()
            self.table.setItem(r, 0, QTableWidgetItem(name_cas_formula))
            mg_val = str(p['molar_mass']) if p['molar_mass'] else "-"
            self.table.setItem(r, 1, QTableWidgetItem(mg_val))
            sdp_smp = f"Sdp: {p['boiling_point']}\nSmp: {p['melting_point']}".strip()
            self.table.setItem(r, 2, QTableWidgetItem(sdp_smp))
            self.table.setItem(r, 3, QTableWidgetItem(", ".join(p['ghs_symbols'])))
            hp = ", ".join([x['id'] for x in p['h_phrases'] + p['p_phrases']])
            self.table.setItem(r, 4, QTableWidgetItem(hp))
            
            mak = f"MAK: {p['mak']}" if p['mak'] else "MAK: -"
            ld50 = f"LD50: {p['ld50']}" if p['ld50'] else "LD50: -"
            info = f"{mak}\n{ld50}\n{p['wgk']}".strip()
            self.table.setItem(r, 5, QTableWidgetItem(info))
            self.table.setItem(r, 6, QTableWidgetItem(""))
            for x in p['h_phrases'] + p['p_phrases']:
                self.hp_library[x['id']] = x['text']
            
            self.table.blockSignals(False)
            self.results.hide()
            self.search_in.clear()
            self.sync_table()

    def sync_data(self):
        self.data.update({
            "header": self.in_header.text(),
            "praktikum": self.in_praktikum.text(),
            "assistent": self.in_assistent.text(),
            "name": self.in_name.text(),
            "platz": self.in_platz.text(),
            "praeparat": self.in_praeparat.text()
        })
        self.update_preview()

    def sync_table(self):
        self.data["stoffe"] = []
        for r in range(self.table.rowCount()):
            row_data = {}
            for i, col in enumerate(["name", "mg", "sdp", "ghs", "hp", "info", "menge"]):
                item = self.table.item(r, i)
                row_data[col] = item.text() if item else ""
            self.data["stoffe"].append(row_data)
        self.update_preview()

    def sync_text(self):
        new_data = {}
        for a, dw in self.dyn_widgets.items():
            new_data[a] = dw.get_text_list()
        self.data.update(new_data)
        self.update_preview()

    def update_preview(self):
        self.preview_timer.start(100)

    def _do_update_preview(self):
        if not self.preview:
            return
        try:
            self.preview.setHtml(self.generate_html())
        except Exception as e:
            logging.error(f"Preview update failed: {e}")

    def clean_hp_text(self, text):
        if not text:
            return ""
        # Remove text in parentheses (like "Expositionsweg angeben...")
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[:\s\.]+$', '', text)
        if text and not text.endswith('.'):
            text += "."
        return text

    def get_hp_text(self, is_h):
        codes = set()
        for s in self.data.get("stoffe", []):
            hp_val = s.get("hp", "")
            if not hp_val: continue
            for c in hp_val.replace(";", ",").replace("\n", ",").split(","):
                c = c.strip()
                if c and (c.startswith("H") if is_h else c.startswith("P")):
                    codes.add(c)
        
        result = []
        for c in sorted(list(codes)):
            text = self.hp_library.get(c) or get_hp_library().get(c, "Text nicht gefunden")
            text = self.clean_hp_text(text)
            result.append(f"<b>{c}:</b> {text}<br>")
        return "".join(result)

    def generate_html(self):
        _img_cache = {}
        def get_b64(n):
            if not n: return ""
            n_clean = n.lower().strip().replace(" ", "")
            if n_clean in _img_cache: return _img_cache[n_clean]
            
            p = get_resource_path(f"assets/ghs_symbols/{n_clean}.png")
            if os.path.exists(p):
                try:
                    with open(p, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                        res = f"data:image/png;base64,{b64}"
                        _img_cache[n_clean] = res
                        return res
                except: pass
            return ""
        
        rows_list = []
        for s in self.data.get("stoffe", []):
            ghs_imgs = []
            for g in s.get("ghs", "").split(","):
                g_code = g.strip()
                if g_code:
                    b64_src = get_b64(g_code)
                    if b64_src:
                        ghs_imgs.append(f'<img src="{b64_src}" width="35" style="margin:2px;">')
            
            name_br = s.get('name', '').replace('\n','<br>')
            sdp_br = s.get('sdp', '').replace('\n','<br>')
            hp_br = s.get('hp', '').replace(',','<br>').replace('\n','<br>')
            info_br = s.get('info', '').replace('\n','<br>')
            
            row = f"""
            <tr>
                <td style='font-size:8pt;'>{name_br}</td>
                <td align='center'>{s.get('mg', '-')}</td>
                <td align='center' style='font-size:8pt;'>{sdp_br}</td>
                <td align='center'>{''.join(ghs_imgs)}</td>
                <td style='font-size:8pt;'>{hp_br}</td>
                <td style='font-size:8pt;'>{info_br}</td>
                <td align='center'>{s.get('menge', '')}</td>
            </tr>
            """
            rows_list.append(row)
        
        rows = "".join(rows_list)
        def list_to_html(lst): return "".join([f"<li>{x}</li>" for x in lst]) if lst else "&nbsp;"

        return f"""
        <html><head><style>
            @page {{ size: A4; margin: 0; }}
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 0; 
                background-color: #f0f2f5; 
            }}
            .container {{ 
                background-color: #ffffff; 
                width: 210mm; 
                min-height: 297mm; 
                padding: 15mm; 
                margin: 20px auto;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                box-sizing: border-box;
                border: 1px solid #ddd;
                position: relative;
            }}
            @media print {{
                body {{ background-color: white; margin: 0; padding: 0; }}
                .container {{ margin: 0; border: none; box-shadow: none; width: 210mm; padding: 15mm; page-break-after: always; }}
                .content-wrapper {{ 
                    border: 2px solid black !important;
                }}
            }}
            .content-wrapper {{ 
                border: 2px solid black; 
                padding: 0; 
                box-sizing: border-box;
            }}
            table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
            thead {{ display: table-header-group; }}
            tfoot {{ display: table-footer-group; }}
            tr {{ page-break-inside: avoid; break-inside: avoid; }}
            td, th {{ border: 1px solid black; padding: 5px; vertical-align: top; overflow-wrap: break-word; }}
            .header-info td {{ font-size: 9pt; height: 40px; }}
            th {{ background: #f0f0f0; font-size: 8pt; }}
            .hp-box {{ border: 1px solid black; border-top: none; display: flex; font-size: 7.5pt; padding: 5px; min-height: 50px; }}
            .sect-box {{ border: 1px solid black; border-top: none; padding: 10px; margin-top: -1px; }}
            .sect-title {{ font-weight: bold; text-decoration: underline; font-size: 10pt; margin-bottom: 5px; }}
            .footer {{ border: 1px solid black; border-top: none; margin-top: -1px; width: 100%; }}
            .footer td {{ height: 80px; font-size: 9pt; vertical-align: bottom; padding: 10px; border: none; }}
            .sig {{ border-top: 1px solid black; width: 90%; margin-top: 50px; font-size: 8pt; text-align: left; }}
            ul {{ margin: 5px 0; padding-left: 20px; font-size: 9pt; }}
            
            /* Ensure top border on new pages */
            .sect-box, .hp-box, .footer {{ break-inside: avoid; }}
        </style></head><body>
            <div class="container">
                <div class="content-wrapper">
                    <div style="border-bottom:1px solid black; text-align:center; font-weight:bold; padding:10px; font-size:11pt;">{self.data['header']}</div>
                    <div style="border-bottom:1px solid black; text-align:center; font-weight:bold; padding:10px; font-size:14pt; background:#f9f9f9;">{self.data['praktikum']}</div>
                    <table class="header-info">
                        <tbody>
                        <tr><td width="35%">Name(n):<br><b>{self.data['name']}</b></td><td width="15%">Platz:<br><b>{self.data['platz']}</b></td><td width="50%">Assistent/in:<br><b>{self.data['assistent']}</b></td></tr>
                        <tr><td colspan="3">Herzustellendes Präparat:<br><b>{self.data['praeparat']}</b></td></tr>
                        </tbody>
                    </table>
                    <table>
                        <thead><tr><th width="20%">Stoffe / CAS / Formel</th><th width="8%">MG [g/mol]</th><th width="12%">Sdp. Smp.</th><th width="15%">GHS-Symbole</th><th width="15%">H/P-Sätze (Nummern)</th><th width="20%">MAK LD50 WGK</th><th width="10%">für Ansatz benötigt</th></tr></thead>
                        <tbody>{rows if rows else '<tr><td colspan=7 height=100 align="center">Keine Stoffe hinzugefügt</td></tr>'}</tbody>
                    </table>
                    <div style="text-align:center; font-weight:bold; border:1px solid black; border-top:none; padding:5px; font-size:10pt; background:#eee;">Wortlaut der wesentlichen oben genannten H- und P-Sätze:</div>
                    <div class="hp-box"><div style="width:50%; border-right:1px solid black; padding-right:5px;">{self.get_hp_text(True)}</div><div style="width:50%; padding-left:5px;">{self.get_hp_text(False)}</div></div>
                    <div class="sect-box"><div class="sect-title">Gefahren für Mensch und Umwelt:</div><ul>{list_to_html(self.data['gefahren'])}</ul></div>
                    <div class="sect-box"><div class="sect-title">Schutzmaßnahmen und Verhaltensregeln:</div><ul>{list_to_html(self.data['schutzmassnahmen'])}</ul></div>
                    <div class="sect-box"><div class="sect-title">Verhalten im Gefahrenfall / Erste Hilfe:</div><ul>{list_to_html(self.data['verhalten'])}</ul></div>
                    <div class="sect-box"><div class="sect-title">Entsorgung:</div><ul>{list_to_html(self.data['entsorgung'])}</ul></div>
                    <table class="footer"><tr><td width="50%" style="border-right:1px solid black !important;">Hiermit verpflichte ich mich, den Versuch gemäß den in dieser Betriebsanweisung aufgeführten Sicherheitsvorschriften durchzuführen.<div class="sig">Unterschrift</div></td><td>Präparat zur Synthese mit den auf der Vorderseite berechneten Chemikalienmengen freigegeben.<div class="sig">Unterschrift</div></td></tr></table>
                </div>
                <div style="font-size:8pt; margin-top:10px; text-align:right;">Quellen: GESTIS</div>
            </div>
        </body></html>
        """

    def export_pdf(self):
        p, _ = QFileDialog.getSaveFileName(self, "PDF Export", "", "PDF (*.pdf)")
        if p:
            if not p.endswith(".pdf"): p += ".pdf"
            try:
                # Use built-in PDF printing which is much more reliable
                self.preview.page().printToPdf(p)
                QMessageBox.information(self, "Export", "PDF wurde erfolgreich exportiert.")
            except Exception as e:
                logging.error(f"PDF export failed: {e}")
                # Fallback to HTML
                with open(p.replace(".pdf",".html"), "w", encoding="utf-8") as f: 
                    f.write(self.generate_html())
                QMessageBox.warning(self, "Export", f"PDF Export fehlgeschlagen. HTML-Datei wurde stattdessen erstellt.\nFehler: {e}")

    def save_project(self):
        p, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", "", "CaBr3 Projekt (*.cabr3)")
        if p:
            if not p.endswith(".cabr3"): p += ".cabr3"
            try:
                # Ensure data is fully synced
                self.sync_data()
                self.sync_table()
                self.sync_text()
                
                project_data = {
                    "data": self.data,
                    "hp_library": self.hp_library
                }
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(project_data, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Speichern", "Projekt wurde erfolgreich gespeichert.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Projekt konnte nicht gespeichert werden:\n{e}")

    def load_project(self):
        p, _ = QFileDialog.getOpenFileName(self, "Projekt laden", "", "CaBr3 Projekt (*.cabr3)")
        if p:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                self.data = project_data.get("data", {})
                self.hp_library = project_data.get("hp_library", {})
                
                # Update UI elements
                self.in_header.setText(self.data.get("header", ""))
                self.in_praktikum.setText(self.data.get("praktikum", ""))
                self.in_assistent.setText(self.data.get("assistent", ""))
                self.in_name.setText(self.data.get("name", ""))
                self.in_platz.setText(self.data.get("platz", ""))
                self.in_praeparat.setText(self.data.get("praeparat", ""))
                
                # Update Table
                self.table.blockSignals(True)
                self.table.setRowCount(0)
                for s in self.data.get("stoffe", []):
                    r = self.table.rowCount()
                    self.table.insertRow(r)
                    self.table.setItem(r, 0, QTableWidgetItem(s.get("name", "")))
                    self.table.setItem(r, 1, QTableWidgetItem(s.get("mg", "-")))
                    self.table.setItem(r, 2, QTableWidgetItem(s.get("sdp", "")))
                    self.table.setItem(r, 3, QTableWidgetItem(s.get("ghs", "")))
                    self.table.setItem(r, 4, QTableWidgetItem(s.get("hp", "")))
                    self.table.setItem(r, 5, QTableWidgetItem(s.get("info", "")))
                    self.table.setItem(r, 6, QTableWidgetItem(s.get("menge", "")))
                self.table.blockSignals(False)
                
                # Update Dynamic Lists
                for attr, dw in self.dyn_widgets.items():
                    dw.blockSignals(True)
                    # Clear existing rows
                    while dw.rows:
                        dw.remove_row(dw.rows[0])
                    # Add new rows
                    for text in self.data.get(attr, []):
                        dw.add_row(text)
                    dw.blockSignals(False)
                
                self.update_preview()
                QMessageBox.information(self, "Laden", "Projekt wurde erfolgreich geladen.")
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Projekt konnte nicht geladen werden:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Show splash screen IMMEDIATELY
    splash_path = get_resource_path("assets/splash.png")
    if not os.path.exists(splash_path):
        splash_path = get_resource_path("assets/logo.png")
    
    splash = None
    if os.path.exists(splash_path):
        pixmap = QPixmap(splash_path)
        if not pixmap.isNull():
            # For weak PCs, avoid complex flags if not needed, but StayOnTop is usually fine
            splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
            splash.show()
            splash.showMessage("Starte CaBr3...", Qt.AlignBottom | Qt.AlignLeft, Qt.white)
            # Force processing to ensure splash is painted
            for _ in range(10):
                app.processEvents()
    
    # Delay main window creation slightly to allow splash to show
    start_time = time.time()
    w = CaBr3App(splash, start_time)
    
    sys.exit(app.exec())
