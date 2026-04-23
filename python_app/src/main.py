import sys
import os
import json
import logging
import base64
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QFrame, QStackedWidget, QFileDialog,
    QHeaderView, QCompleter, QListWidget, QListWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QStringListModel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QFont, QColor

from gestis_client import GestisClient
from gestis_parser import GestisParser

# Define styles locally to avoid extra file for now
STYLES = """
QMainWindow {
    background-color: #f8f9fa;
}
QWidget#Sidebar {
    background-color: #2c3e50;
    min-width: 70px;
    max-width: 70px;
}
QPushButton#SidebarBtn {
    background-color: transparent;
    border: none;
    color: #bdc3c7;
    padding: 15px;
    font-size: 20px;
}
QPushButton#SidebarBtn:hover {
    background-color: #34495e;
    color: white;
}
QPushButton#SidebarBtn[active="true"] {
    background-color: #3498db;
    color: white;
}
QFrame#Card {
    background-color: white;
    border-radius: 4px;
    border: 1px solid #dee2e6;
}
QLabel#SectionTitle {
    font-size: 16px;
    font-weight: bold;
    color: #495057;
    margin-bottom: 5px;
}
QLineEdit, QTextEdit {
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 8px;
    background-color: #ffffff;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #80bdff;
}
QPushButton#ActionBtn {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 15px;
    font-weight: bold;
}
QPushButton#ActionBtn:hover {
    background-color: #2980b9;
}
QPushButton#ExportBtn {
    background-color: #f39c12;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 14px;
}
QPushButton#ExportBtn:hover {
    background-color: #e67e22;
}
QTableWidget {
    border: 1px solid #dee2e6;
    background-color: white;
}
QHeaderView::section {
    background-color: #f1f3f5;
    padding: 8px;
    border: 1px solid #dee2e6;
    font-weight: bold;
}
"""

class CaBr2App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CaBr2 - Betriebsanweisungsgenerator")
        self.resize(1400, 900)
        self.setStyleSheet(STYLES)
        
        self.client = GestisClient()
        self.data = {
            "praktikum": "",
            "assistent": "",
            "name": "",
            "platz": "",
            "praeparat": "",
            "stoffe": [],
            "gefahren": "",
            "schutzmassnahmen": "",
            "verhalten": "",
            "entsorgung": ""
        }
        
        self.init_ui()
        self.update_preview()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        self.btn_home = QPushButton("🏠")
        self.btn_home.setObjectName("SidebarBtn")
        self.btn_home.setProperty("active", True)
        
        self.btn_chem = QPushButton("🧪")
        self.btn_chem.setObjectName("SidebarBtn")
        
        self.btn_text = QPushButton("📝")
        self.btn_text.setObjectName("SidebarBtn")
        
        sidebar_layout.addWidget(self.btn_home)
        sidebar_layout.addWidget(self.btn_chem)
        sidebar_layout.addWidget(self.btn_text)
        sidebar_layout.addStretch()
        
        main_layout.addWidget(sidebar)

        # Splitter for Editor and Preview
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Editor
        self.editor_stack = QStackedWidget()
        self.init_editor_pages()
        self.splitter.addWidget(self.editor_stack)
        
        # Right side: Preview
        self.preview_view = QWebEngineView()
        self.preview_view.setMinimumWidth(500)
        self.splitter.addWidget(self.preview_view)
        
        main_layout.addWidget(self.splitter)
        
        # Connect signals
        self.btn_home.clicked.connect(lambda: self.switch_page(0))
        self.btn_chem.clicked.connect(lambda: self.switch_page(1))
        self.btn_text.clicked.connect(lambda: self.switch_page(2))

    def init_editor_pages(self):
        # Page 0: Home / Header Data
        page_home = QWidget()
        layout = QVBoxLayout(page_home)
        
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        
        card_layout.addWidget(QLabel("Kopfdaten", objectName="SectionTitle"))
        
        self.in_praktikum = QLineEdit(placeholderText="Praktikum (z.B. Anorganische Chemie)")
        self.in_assistent = QLineEdit(placeholderText="Assistent/in")
        self.in_name = QLineEdit(placeholderText="Name(n)")
        self.in_platz = QLineEdit(placeholderText="Platz")
        self.in_praeparat = QLineEdit(placeholderText="Herzustellendes Präparat")
        
        for w in [self.in_praktikum, self.in_assistent, self.in_name, self.in_platz, self.in_praeparat]:
            card_layout.addWidget(w)
            w.textChanged.connect(self.sync_data)
            
        card_layout.addStretch()
        layout.addWidget(card)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Speichern")
        btn_save.setObjectName("ActionBtn")
        btn_load = QPushButton("Laden")
        btn_load.setObjectName("ActionBtn")
        btn_export = QPushButton("PDF EXPORT")
        btn_export.setObjectName("ExportBtn")
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_load)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(btn_layout)
        self.editor_stack.addWidget(page_home)

        # Page 1: Substances
        page_chem = QWidget()
        layout_chem = QVBoxLayout(page_chem)
        
        # Search Card
        search_card = QFrame()
        search_card.setObjectName("Card")
        search_layout = QVBoxLayout(search_card)
        search_layout.addWidget(QLabel("GESTIS Suche", objectName="SectionTitle"))
        
        search_input_layout = QHBoxLayout()
        self.search_field = QLineEdit(placeholderText="Stoffname oder CAS-Nummer...")
        btn_search = QPushButton("Suche")
        btn_search.setObjectName("ActionBtn")
        search_input_layout.addWidget(self.search_field)
        search_input_layout.addWidget(btn_search)
        search_layout.addLayout(search_input_layout)
        
        # Search Results List
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(150)
        self.search_results.hide()
        search_layout.addWidget(self.search_results)
        
        layout_chem.addWidget(search_card)
        
        # Substances Table
        table_card = QFrame()
        table_card.setObjectName("Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.addWidget(QLabel("Eingesetzte Stoffe", objectName="SectionTitle"))
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Stoff", "MG", "Sdp/Smp", "GHS", "H/P", "Info", "Menge"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.table)
        
        row_btns = QHBoxLayout()
        btn_add = QPushButton("Manuell hinzufügen")
        btn_remove = QPushButton("Entfernen")
        row_btns.addWidget(btn_add)
        row_btns.addWidget(btn_remove)
        table_layout.addLayout(row_btns)
        
        layout_chem.addWidget(table_card)
        self.editor_stack.addWidget(page_chem)
        
        # Connections
        btn_search.clicked.connect(self.do_search)
        self.search_results.itemDoubleClicked.connect(self.add_from_search)
        btn_add.clicked.connect(self.add_manual_row)
        btn_remove.clicked.connect(self.remove_row)
        self.table.itemChanged.connect(self.sync_table_data)
        btn_export.clicked.connect(self.export_pdf)

    def export_pdf(self):
        try:
            from xhtml2pdf import pisa
            
            path, _ = QFileDialog.getSaveFileName(self, "PDF Exportieren", "", "PDF Dateien (*.pdf)")
            if path:
                if not path.endswith(".pdf"): path += ".pdf"
                
                html = self.generate_html()
                with open(path, "w+b") as out:
                    pisa_status = pisa.CreatePDF(html, dest=out)
                    
                if pisa_status.err:
                    logging.error("PDF Export failed")
                else:
                    logging.info(f"PDF exported to {path}")
        except ImportError:
            # Fallback if xhtml2pdf is missing, maybe just save HTML
            logging.error("xhtml2pdf not installed. Saving as HTML instead.")
            path, _ = QFileDialog.getSaveFileName(self, "HTML Exportieren", "", "HTML Dateien (*.html)")
            if path:
                if not path.endswith(".html"): path += ".html"
                with open(path, "w") as f:
                    f.write(self.generate_html())

        # Page 2: Texts
        page_text = QWidget()
        layout_text = QVBoxLayout(page_text)
        
        for title, attr in [
            ("Gefahren für Mensch und Umwelt", "gefahren"),
            ("Schutzmaßnahmen und Verhaltensregeln", "schutzmassnahmen"),
            ("Verhalten im Gefahrenfall", "verhalten"),
            ("Entsorgung", "entsorgung")
        ]:
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title, objectName="SectionTitle"))
            te = QTextEdit()
            te.textChanged.connect(self.sync_text_data)
            setattr(self, f"te_{attr}", te)
            cl.addWidget(te)
            layout_text.addWidget(card)
            
        self.editor_stack.addWidget(page_text)

    def switch_page(self, index):
        self.editor_stack.setCurrentIndex(index)
        for i, btn in enumerate([self.btn_home, self.btn_chem, self.btn_text]):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def do_search(self):
        query = self.search_field.text()
        if not query: return
        
        results = self.client.search(query)
        self.search_results.clear()
        if results:
            for item in results:
                list_item = QListWidgetItem(f"{item['name']} (CAS: {item.get('cas', 'N/A')})")
                list_item.setData(Qt.UserRole, item['id'])
                self.search_results.addItem(list_item)
            self.search_results.show()
        else:
            self.search_results.addItem("Keine Ergebnisse gefunden.")
            self.search_results.show()

    def add_from_search(self, item):
        zvg_id = item.data(Qt.UserRole)
        if not zvg_id: return
        
        article = self.client.get_article(zvg_id)
        if article:
            parsed = GestisParser.parse_article(article)
            self.add_to_table(parsed)
            self.search_results.hide()
            self.search_field.clear()

    def add_to_table(self, data):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Name/CAS/Formula
        name_info = f"{data['name']}\n{data['formula']}\n{data['cas']}".strip()
        self.table.setItem(row, 0, QTableWidgetItem(name_info))
        self.table.setItem(row, 1, QTableWidgetItem(data['molar_mass']))
        self.table.setItem(row, 2, QTableWidgetItem(f"{data['boiling_point']} / {data['melting_point']}"))
        
        # GHS
        symbols = ", ".join(data['ghs_symbols'])
        self.table.setItem(row, 3, QTableWidgetItem(symbols))
        
        # H/P Codes
        hp_codes = ", ".join([h['id'] for h in data['h_phrases']] + [p['id'] for p in data['p_phrases']])
        self.table.setItem(row, 4, QTableWidgetItem(hp_codes))
        
        # Info
        info = f"{data['wgk']}\n{data['mak_ld50']}".strip()
        self.table.setItem(row, 5, QTableWidgetItem(info))
        
        self.table.setItem(row, 6, QTableWidgetItem("")) # Menge
        
        # Store full H/P phrases for wording lookups
        if not hasattr(self, "hp_library"): self.hp_library = {}
        for h in data['h_phrases']: self.hp_library[h['id']] = h['text']
        for p in data['p_phrases']: self.hp_library[p['id']] = p['text']
        
        self.sync_table_data()

    def add_manual_row(self):
        self.table.insertRow(self.table.rowCount())

    def remove_row(self):
        curr = self.table.currentRow()
        if curr >= 0:
            self.table.removeRow(curr)
            self.sync_table_data()

    def sync_data(self):
        self.data["praktikum"] = self.in_praktikum.text()
        self.data["assistent"] = self.in_assistent.text()
        self.data["name"] = self.in_name.text()
        self.data["platz"] = self.in_platz.text()
        self.data["praeparat"] = self.in_praeparat.text()
        self.update_preview()

    def sync_table_data(self):
        self.data["stoffe"] = []
        for r in range(self.table.rowCount()):
            stoff = {
                "name": self.table.item(r, 0).text() if self.table.item(r, 0) else "",
                "mg": self.table.item(r, 1).text() if self.table.item(r, 1) else "",
                "sdp": self.table.item(r, 2).text() if self.table.item(r, 2) else "",
                "ghs": self.table.item(r, 3).text() if self.table.item(r, 3) else "",
                "hp": self.table.item(r, 4).text() if self.table.item(r, 4) else "",
                "info": self.table.item(r, 5).text() if self.table.item(r, 5) else "",
                "menge": self.table.item(r, 6).text() if self.table.item(r, 6) else ""
            }
            self.data["stoffe"].append(stoff)
        self.update_preview()

    def sync_text_data(self):
        self.data["gefahren"] = self.te_gefahren.toPlainText()
        self.data["schutzmassnahmen"] = self.te_schutzmassnahmen.toPlainText()
        self.data["verhalten"] = self.te_verhalten.toPlainText()
        self.data["entsorgung"] = self.te_entsorgung.toPlainText()
        self.update_preview()

    def update_preview(self):
        html = self.generate_html()
        self.preview_view.setHtml(html)

    def generate_html(self):
        # Base64 helper for symbols
        def get_base64_image(name):
            try:
                path = os.path.join(os.path.dirname(__file__), "..", "assets", "ghs_symbols", f"{name.lower()}.png")
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        data = base64.b64encode(f.read()).decode()
                        return f"data:image/png;base64,{data}"
            except:
                pass
            return ""

        rows = ""
        for s in self.data["stoffe"]:
            symbols_html = ""
            for sym in s["ghs"].split(","):
                sym = sym.strip()
                if sym:
                    b64 = get_base64_image(sym)
                    if b64:
                        symbols_html += f'<img src="{b64}" width="40" height="40" style="margin: 2px;">'
            
            rows += f"""
            <tr>
                <td>{s['name'].replace('\n', '<br>')}</td>
                <td>{s['mg']}</td>
                <td>{s['sdp'].replace('/', '<br>')}</td>
                <td style="text-align: center;">{symbols_html}</td>
                <td>{s['hp'].replace(',', '<br>')}</td>
                <td>{s['info'].replace('\n', '<br>')}</td>
                <td>{s['menge']}</td>
            </tr>
            """
            
        html = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 1cm; }}
                body {{ font-family: 'Arial', sans-serif; font-size: 9pt; line-height: 1.2; color: #333; }}
                .main-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                .main-table th, .main-table td {{ border: 1px solid black; padding: 4px; vertical-align: top; }}
                .header-table {{ width: 100%; border-collapse: collapse; border: 1px solid black; }}
                .header-table td {{ border: 1px solid black; padding: 5px; }}
                .title-block {{ text-align: center; border: 1px solid black; border-bottom: none; padding: 5px; font-weight: bold; font-size: 11pt; }}
                .sub-title {{ text-align: center; border: 1px solid black; border-bottom: none; padding: 5px; font-weight: bold; }}
                .section-box {{ border: 1px solid black; margin-top: -1px; padding: 5px; }}
                .section-header {{ font-weight: bold; text-decoration: underline; margin-bottom: 5px; }}
                .footer-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                .footer-table td {{ border: 1px solid black; height: 60px; padding: 5px; vertical-align: top; width: 50%; }}
                .sig-line {{ border-top: 1px solid black; width: 80%; margin-top: 40px; font-size: 8pt; }}
            </style>
        </head>
        <body>
            <div class="title-block">Betriebsanweisungen nach EG Nr. 1272/2008</div>
            <div class="sub-title">Für chemische Laboratorien des Campus Burghausen</div>
            <div class="sub-title" style="font-size: 11pt;">{self.data['praktikum'] or 'Praktikum Anorganische Chemie'}</div>
            
            <table class="header-table">
                <tr>
                    <td width="35%">Name(n)<br><b>{self.data['name'] or '&nbsp;'}</b></td>
                    <td width="15%">Platz<br><b>{self.data['platz'] or '&nbsp;'}</b></td>
                    <td width="50%">Assistent/in<br><b>{self.data['assistent'] or '&nbsp;'}</b></td>
                </tr>
                <tr>
                    <td colspan="3">Herzustellendes Präparat:<br><b>{self.data['praeparat'] or '&nbsp;'}</b></td>
                </tr>
            </table>
            
            <table class="main-table">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th width="20%">eingesetzte Stoffe und Produkte</th>
                        <th width="10%">MG [g/mol]</th>
                        <th width="10%">Sdp. Smp.</th>
                        <th width="15%">GHS-Symbole</th>
                        <th width="15%">H/P-Sätze (Nummern)</th>
                        <th width="15%">MAK LD50 WGK</th>
                        <th width="15%">für Ansatz benötigt</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else '<tr><td colspan="7" style="height: 100px;">&nbsp;</td></tr>'}
                </tbody>
            </table>
            
            <div style="text-align: center; font-weight: bold; padding: 5px; border: 1px solid black; border-top: none;">
                Wortlaut der wesentlichen oben genannten H- und P-Sätze:
            </div>
            <div style="border: 1px solid black; border-top: none; min-height: 50px; padding: 5px; display: flex;">
                 <div style="width: 50%; font-size: 8pt;">{self.get_hp_text(True)}</div>
                 <div style="width: 50%; font-size: 8pt; border-left: 1px solid black; padding-left: 5px;">{self.get_hp_text(False)}</div>
            </div>

            <div class="section-box">
                <div class="section-header">Gefahren für Mensch und Umwelt:</div>
                <div style="font-size: 8pt;">{self.data['gefahren'].replace('\n', '<br>') or '&nbsp;'}</div>
            </div>
            <div class="section-box">
                <div class="section-header">Schutzmaßnahmen und Verhaltensregeln:</div>
                <div style="font-size: 8pt;">{self.data['schutzmassnahmen'].replace('\n', '<br>') or '&nbsp;'}</div>
            </div>
            <div class="section-box">
                <div class="section-header">Verhalten im Gefahrenfall, Erste-Hilfe-Maßnahmen:</div>
                <div style="font-size: 8pt;">{self.data['verhalten'].replace('\n', '<br>') or '&nbsp;'}</div>
            </div>
            <div class="section-box">
                <div class="section-header">Entsorgung:</div>
                <div style="font-size: 8pt;">{self.data['entsorgung'].replace('\n', '<br>') or '&nbsp;'}</div>
            </div>

            <table class="footer-table">
                <tr>
                    <td>
                        Hiermit verpflichte ich mich, den Versuch gemäß den in dieser Betriebsanweisung aufgeführten Sicherheitsvorschriften durchzuführen.
                        <div class="sig-line">Unterschrift</div>
                    </td>
                    <td>
                        Präparat zur Synthese mit den auf der Vorderseite berechneten Chemikalienmengen freigegeben.
                        <div class="sig-line">Unterschrift</div>
                    </td>
                </tr>
            </table>
            
            <div style="font-size: 7pt; margin-top: 5px;">Quellen: GESTIS</div>
        </body>
        </html>
        """
        return html

    def get_hp_text(self, is_h):
        if not hasattr(self, "hp_library"): return ""
        
        codes = set()
        for s in self.data["stoffe"]:
            for code in s["hp"].split(","):
                code = code.strip()
                if is_h and code.startswith("H"): codes.add(code)
                elif not is_h and code.startswith("P"): codes.add(code)
        
        sorted_codes = sorted(list(codes))
        text = ""
        for c in sorted_codes:
            if c in self.hp_library:
                text += f"<b>{c}:</b> {self.hp_library[c]}<br>"
        return text

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CaBr2App()
    window.show()
    sys.exit(app.exec())
