import sys
import os
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QComboBox, QGroupBox, QListWidget, QDialog, QProgressBar,
                             QTabWidget, QSplitter, QFrame, QGraphicsOpacityEffect,
                             QListWidgetItem)
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QIcon, QPixmap, QFont

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.coordinator import ReconCoordinator
from src.desktop.login import LoginScreen, SplashScreen
from src.desktop.admin import AdminPortal
from src.core.database import DatabaseManager

class ComparisonView(QDialog):
    def __init__(self, df_a, df_b, mapping, key_col=None, parent=None, accepted_logical_matches=None):
        super().__init__(parent)
        self.setWindowTitle("Aura - Intelligent Delta View")
        self.setMinimumSize(1200, 800)
        self.layout = QVBoxLayout(self)
        
        self.accepted_logical_matches = accepted_logical_matches if accepted_logical_matches is not None else set()
        
        controls_layout = QHBoxLayout()
        info_icon = QLabel("ℹ")
        info_icon.setStyleSheet("color: #ffd54f; font-size: 18px; font-weight: bold;")
        controls_layout.addWidget(info_icon)
        
        self.info_label = QLabel("Yellow cells represent 'Logical Matches'. Use these buttons to accept them as matches:")
        self.info_label.setStyleSheet("color: #aaa; font-size: 11px;")
        controls_layout.addWidget(self.info_label)
        
        controls_layout.addStretch()
        
        self.btn_accept_all_yellow = QPushButton("ACCEPT ALL LOGICAL MATCHES")
        self.btn_accept_all_yellow.setStyleSheet("""
            QPushButton { background-color: #333; color: #ffd54f; border: 1px solid #ffd54f; padding: 5px 15px; font-size: 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #ffd54f; color: black; }
        """)
        self.btn_accept_all_yellow.clicked.connect(self.accept_all_yellow)
        controls_layout.addWidget(self.btn_accept_all_yellow)

        self.btn_revert_yellow = QPushButton("REVERT ACCEPTED MATCHES")
        self.btn_revert_yellow.setStyleSheet("""
            QPushButton { background-color: #333; color: #888; border: 1px solid #555; padding: 5px 15px; font-size: 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #555; color: white; }
        """)
        self.btn_revert_yellow.clicked.connect(self.revert_all_yellow)
        controls_layout.addWidget(self.btn_revert_yellow)
        
        controls_layout.addStretch()

        self.btn_save_choices = QPushButton("SAVE & APPLY CHANGES")
        self.btn_save_choices.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; border: none; padding: 8px 20px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_save_choices.clicked.connect(self.accept)
        controls_layout.addWidget(self.btn_save_choices)
        
        self.layout.addLayout(controls_layout)
        
        splitter = QSplitter(Qt.Horizontal)
        self.table_a = QTableWidget()
        self.table_b = QTableWidget()
        
        self.match_color = QColor("#1e3a1e") 
        self.logic_diff_color = QColor("#ffd54f") 
        
        self.populate_and_compare(df_a, df_b, mapping, key_col)
        
        self.table_a.verticalScrollBar().valueChanged.connect(self.table_b.verticalScrollBar().setValue)
        self.table_b.verticalScrollBar().valueChanged.connect(self.table_a.verticalScrollBar().setValue)
        
        splitter.addWidget(self.table_a)
        splitter.addWidget(self.table_b)
        self.layout.addWidget(splitter)

    def accept_all_yellow(self):
        for row in range(self.table_a.rowCount()):
            for col in range(self.table_a.columnCount()):
                item_a = self.table_a.item(row, col)
                if item_a and item_a.background().color() == self.logic_diff_color:
                    col_name = self.table_a.horizontalHeaderItem(col).text()
                    self.accepted_logical_matches.add((row, col_name))
                    item_a.setBackground(self.match_color)
                    item_a.setForeground(QColor("#ffffff"))
                    item_b = self.table_b.item(row, col)
                    if item_b:
                        item_b.setBackground(self.match_color)
                        item_b.setForeground(QColor("#ffffff"))

    def revert_all_yellow(self):
        for row, col_name in list(self.accepted_logical_matches):
            col_idx = -1
            for c in range(self.table_a.columnCount()):
                if self.table_a.horizontalHeaderItem(c).text() == col_name:
                    col_idx = c
                    break
            if col_idx != -1:
                for table in [self.table_a, self.table_b]:
                    item = table.item(row, col_idx)
                    if item:
                        item.setBackground(self.logic_diff_color)
                        item.setForeground(QColor("#000000"))
        self.accepted_logical_matches.clear()

    def populate_and_compare(self, df_a, df_b, mapping, key_col):
        # 1. Debug Log: What are we actually comparing?
        print(f"DEBUG: Comparing using Primary Key '{key_col}'")
        print(f"DEBUG: Mapping applied: {mapping}")
        
        target_key_col = mapping.get(key_col, key_col)
        print(f"DEBUG: Looking for '{key_col}' (A) in '{target_key_col}' (B)")

        rows = len(df_a)
        cols = len(df_a.columns)
        self.table_a.setRowCount(rows); self.table_a.setColumnCount(cols)
        self.table_b.setRowCount(rows); self.table_b.setColumnCount(cols)
        
        self.table_a.setHorizontalHeaderLabels(df_a.columns)
        
        b_headers = []
        for col_a in df_a.columns:
            mapped_b = mapping.get(col_a)
            b_headers.append(f"{mapped_b} (B)" if mapped_b else "-")
        self.table_b.setHorizontalHeaderLabels(b_headers)

        def normalize_val(v):
            if pd.isna(v): return "nan"
            try:
                # Handle cases like 699451 vs 699451.0
                f_val = float(v)
                if f_val == int(f_val):
                    return str(int(f_val)).strip()
                return str(f_val).strip()
            except:
                return str(v).strip()

        # 2. Build a robust lookup for B
        b_lookup = {}
        if target_key_col in df_b.columns:
            for _, row in df_b.iterrows():
                # Normalize key for matching
                k = normalize_val(row[target_key_col])
                b_lookup[k] = row
        else:
            print(f"ERROR: {target_key_col} not found in Group B columns: {df_b.columns.tolist()}")

        # Colors
        match_color = self.match_color 
        logic_diff_color = self.logic_diff_color 
        diff_color = QColor("#ff4d4d") 
        missing_color = QColor("#333333")
        text_color = QColor("#ffffff")

        # 3. Populate
        for i in range(rows):
            row_a = df_a.iloc[i]
            val_key_a = normalize_val(row_a[key_col])
            row_b = b_lookup.get(val_key_a)

            for j, col_a in enumerate(df_a.columns):
                # A Side
                val_a = str(row_a[col_a]).strip()
                item_a = QTableWidgetItem(val_a)
                item_a.setForeground(text_color)
                self.table_a.setItem(i, j, item_a)
                
                # B Side
                if row_b is not None:
                    col_b = mapping.get(col_a)
                    val_b = ""
                    if col_b and col_b in row_b.index:
                        val_b = str(row_b[col_b]).strip()
                    
                    item_b = QTableWidgetItem(val_b)
                    item_b.setForeground(text_color)
                    
                    # Logic
                    is_match = (val_a == val_b)
                    is_logical_match = False
                    if not is_match:
                        try:
                            if float(val_a) == float(val_b): is_match = True
                        except: pass
                        if not is_match and val_a.replace("/", "-") == val_b.replace("/", "-"): 
                            is_logical_match = True

                    if (i, col_a) in self.accepted_logical_matches:
                        bg = match_color
                    elif is_match:
                        bg = match_color
                    elif is_logical_match:
                        bg = logic_diff_color
                        item_a.setForeground(QColor("#000000"))
                        item_b.setForeground(QColor("#000000"))
                    else:
                        bg = diff_color
                    
                    item_a.setBackground(bg); item_b.setBackground(bg)
                    self.table_b.setItem(i, j, item_b)
                else:
                    # Key missing in B
                    item_a.setBackground(missing_color)
                    item_b = QTableWidgetItem("MISSING IN B")
                    item_b.setBackground(missing_color)
                    item_b.setForeground(QColor("#888"))
                    self.table_b.setItem(i, j, item_b)

class FileListWidget(QWidget):
    def __init__(self, filename, remove_callback, is_dark=True):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        label = QLabel(filename)
        label.setStyleSheet(f"color: {'#ffffff' if is_dark else '#1d1d1f'}; font-size: 13px;")
        btn_del = QPushButton("×")
        btn_del.setFixedSize(22, 22); btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("QPushButton { background-color: #f44336; color: white; border-radius: 11px; font-weight: bold; border: none; }")
        btn_del.clicked.connect(remove_callback)
        layout.addWidget(label); layout.addStretch(); layout.addWidget(btn_del)

class ReconWorker(QThread):
    progress = Signal(int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, coordinator, files_a, files_b, key_col, mapping, db, user_id, tolerance, accepted_matches):
        super().__init__()
        self.coordinator = coordinator; self.files_a = files_a; self.files_b = files_b
        self.key_col = key_col; self.mapping = mapping; self.db = db
        self.user_id = user_id; self.tolerance = tolerance; self.accepted_matches = accepted_matches

    def run(self):
        results = []
        try:
            for i, file_a in enumerate(self.files_a):
                if i < len(self.files_b):
                    file_b = self.files_b[i]
                    output_path = f"Recon_Report_{os.path.basename(file_a)}.xlsx"
                    self.coordinator.run_full_recon(file_a, file_b, self.key_col, self.mapping, output_path, self.tolerance, self.accepted_matches)
                    self.db.log_recon(self.user_id, file_a, file_b, "SUCCESS", output_path)
                    results.append(output_path)
                self.progress.emit(int(((i + 1) / len(self.files_a)) * 100))
            self.finished.emit(results)
        except Exception as e: self.error.emit(str(e))

class ReconApp(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info or {"type": "guest", "id": "Guest"}
        self.db = DatabaseManager(); self.coordinator = ReconCoordinator()
        self.is_dark_mode = True; self.files_a = []; self.files_b = []
        self.accepted_logical_matches = set()
        self.setWindowTitle("AURA - Automated Universal Reconciliation AI")
        self.setMinimumSize(1200, 850)
        self.init_ui(); self.apply_theme()

    def init_ui(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)

        top_bar = QHBoxLayout()
        # FUTURISTIC APP TITLE
        title_container = QVBoxLayout()
        app_title = QLabel("AURA"); app_title.setFont(QFont("Segoe UI Light", 24))
        app_title.setStyleSheet("color: #2196F3; letter-spacing: 6px; margin: 0; padding: 0; border: none;")
        
        org_label = QLabel("POWERED BY ANDILE SOLUTIONS"); org_label.setStyleSheet("color: #555; font-size: 9px; font-weight: bold; letter-spacing: 2px; margin-top: 0px; border: none;")
        
        title_container.addWidget(app_title)
        title_container.addWidget(org_label)
        title_container.setSpacing(0)
        top_bar.addLayout(title_container); top_bar.addSpacing(30)
        
        self.btn_info = QPushButton("ℹ"); self.btn_info.setFixedSize(40, 40)
        self.btn_info.setCursor(Qt.PointingHandCursor)
        self.btn_info.clicked.connect(self.show_info)
        top_bar.addWidget(self.btn_info)
        
        if self.db.is_admin(self.user_info['id']):
            self.btn_admin = QPushButton("ADMIN PANEL"); self.btn_admin.setFixedWidth(130)
            self.btn_admin.setCursor(Qt.PointingHandCursor)
            self.btn_admin.clicked.connect(self.open_admin_portal)
            top_bar.addWidget(self.btn_admin)
        
        top_bar.addStretch()
        self.btn_theme = QPushButton("🌙"); self.btn_theme.setFixedSize(45, 40)
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)

        self.user_menu = QComboBox(); self.user_menu.addItems([f"USER: {self.user_info['id'].upper()}", "LOGOUT SYSTEM"])
        self.user_menu.setFixedWidth(220); self.user_menu.activated.connect(self.handle_user_menu)
        top_bar.addWidget(self.user_menu)
        main_layout.addLayout(top_bar)

        files_group = QGroupBox("1. DATA INGESTION")
        files_layout = QHBoxLayout()
        for grp in ['a', 'b']:
            vbox = QVBoxLayout(); btn = QPushButton(f"IMPORT GROUP {grp.upper()}"); btn.clicked.connect(lambda c=0, g=grp: self.select_files(g))
            lst = QListWidget(); setattr(self, f"list_{grp}", lst); vbox.addWidget(btn); vbox.addWidget(lst); files_layout.addLayout(vbox)
        files_group.setLayout(files_layout); main_layout.addWidget(files_group)

        config_group = QGroupBox("2. MAPPING STRATEGY")
        config_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("INITIALIZE AI MAPPING"); self.btn_analyze.clicked.connect(self.run_analysis)
        self.btn_add_mapping = QPushButton("+ ADD FIELD"); self.btn_add_mapping.clicked.connect(self.add_mapping_row)
        self.btn_compare_view = QPushButton("SIDE-BY-SIDE ANALYTICS"); self.btn_compare_view.setEnabled(False); self.btn_compare_view.clicked.connect(self.open_comparison_view)
        btn_row.addWidget(self.btn_analyze); btn_row.addWidget(self.btn_add_mapping); btn_row.addWidget(self.btn_compare_view); btn_row.addStretch()
        config_layout.addLayout(btn_row)

        key_row = QHBoxLayout(); key_row.addWidget(QLabel("PRIMARY KEY:")); self.combo_key = QComboBox(); self.combo_key.setFixedWidth(200); key_row.addWidget(self.combo_key)
        key_row.addSpacing(20); key_row.addWidget(QLabel("TOLERANCE:")); self.spin_tol = QComboBox(); self.spin_tol.addItems(["0.00", "0.01", "0.05"]); self.spin_tol.setEditable(True); self.spin_tol.setCurrentText("0.01"); key_row.addWidget(self.spin_tol); key_row.addStretch(); config_layout.addLayout(key_row)

        self.mapping_table = QTableWidget(0, 3); self.mapping_table.setHorizontalHeaderLabels(["SOURCE (A)", "TARGET (B)", "STATUS"]); self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); config_layout.addWidget(self.mapping_table)
        config_group.setLayout(config_layout); main_layout.addWidget(config_group)

        self.progress_bar = QProgressBar(); self.progress_bar.hide(); main_layout.addWidget(self.progress_bar)
        self.btn_reconcile = QPushButton("RUN GLOBAL RECONCILIATION"); self.btn_reconcile.setFixedHeight(55)
        self.btn_reconcile.setCursor(Qt.PointingHandCursor)
        self.btn_reconcile.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white; letter-spacing: 1px;"); 
        main_layout.addWidget(self.btn_reconcile)

        self.btn_analyze.clicked.connect(self.run_analysis); self.btn_compare_view.clicked.connect(self.open_comparison_view); self.btn_reconcile.clicked.connect(self.run_reconciliation)

    def select_files(self, group):
        paths, _ = QFileDialog.getOpenFileNames(self, "Ingest Files", "", "Excel/CSV (*.xlsx *.csv)")
        if paths:
            target_list = self.list_a if group == 'a' else self.list_b
            file_store = self.files_a if group == 'a' else self.files_b
            for p in paths:
                if p not in file_store:
                    file_store.append(p); item = QListWidgetItem(target_list)
                    w = FileListWidget(os.path.basename(p), lambda g=group, p_path=p: self.remove_file(g, p_path), self.is_dark_mode)
                    item.setSizeHint(w.sizeHint()); target_list.addItem(item); target_list.setItemWidget(item, w)

    def remove_file(self, group, path):
        store = self.files_a if group == 'a' else self.files_b
        target_list = self.list_a if group == 'a' else self.list_b
        if path in store:
            idx = store.index(path); store.pop(idx); target_list.takeItem(idx)

    def run_analysis(self):
        if not self.files_a or not self.files_b: return
        try:
            self.current_df_a = self.coordinator.get_handler(self.files_a[0]).read(self.files_a[0])
            self.current_df_b = self.coordinator.get_handler(self.files_b[0]).read(self.files_b[0])
            self.accepted_logical_matches = set()
            self.combo_key.clear(); self.combo_key.addItems(self.current_df_a.columns.tolist())
            self.combo_key.setCurrentText(self.coordinator.mapper.suggest_primary_key(self.current_df_a))
            mapping = self.coordinator.mapper.suggest_mapping(self.current_df_a.columns.tolist(), self.current_df_b.columns.tolist())
            self.update_mapping_table(mapping)
            self.btn_compare_view.setEnabled(True)
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def update_mapping_table(self, mapping):
        self.mapping_table.setRowCount(0)
        for ca, cb in mapping.items():
            self.add_mapping_row(ca, cb)

    def add_mapping_row(self, val_a=None, val_b=None):
        if not hasattr(self, 'current_df_a'): return
        row = self.mapping_table.rowCount(); self.mapping_table.insertRow(row)
        cb_a = QComboBox(); cb_a.addItems(self.current_df_a.columns.tolist()); self.mapping_table.setCellWidget(row, 0, cb_a)
        if val_a: cb_a.setCurrentText(val_a)
        cb_b = QComboBox(); cb_b.addItems(self.current_df_b.columns.tolist()); self.mapping_table.setCellWidget(row, 1, cb_b)
        if val_b: cb_b.setCurrentText(val_b)
        self.mapping_table.setItem(row, 2, QTableWidgetItem("READY"))

    def get_current_mapping(self):
        m = {}
        for r in range(self.mapping_table.rowCount()):
            ca = self.mapping_table.cellWidget(r, 0).currentText()
            cb = self.mapping_table.cellWidget(r, 1).currentText()
            m[ca] = cb
        return m

    def open_comparison_view(self):
        view = ComparisonView(self.current_df_a, self.current_df_b, self.get_current_mapping(), self.combo_key.currentText(), self, set(self.accepted_logical_matches))
        if view.exec() == QDialog.Accepted:
            self.accepted_logical_matches = view.accepted_logical_matches
            QMessageBox.information(self, "Aura", "Choices Applied to Memory.")

    def run_reconciliation(self):
        mapping = self.get_current_mapping()
        try: tol = float(self.spin_tol.currentText())
        except: tol = 0.01
        self.progress_bar.show(); self.btn_reconcile.setEnabled(False)
        self.worker = ReconWorker(self.coordinator, self.files_a, self.files_b, self.combo_key.currentText(), mapping, self.db, self.user_info['id'], tol, self.accepted_logical_matches)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(lambda: (self.progress_bar.hide(), self.btn_reconcile.setEnabled(True), QMessageBox.information(self, "Aura", "Process Complete.")))
        self.worker.error.connect(lambda e: (self.progress_bar.hide(), self.btn_reconcile.setEnabled(True), QMessageBox.critical(self, "Error", e)))
        self.worker.start()

    def apply_theme(self):
        if self.is_dark_mode:
            bg, fg, panel = "#121212", "#e0e0e0", "#1e1e1e"
            self.setStyleSheet(f"""
                QMainWindow, QWidget {{ background-color: {bg}; color: {fg}; font-family: 'Segoe UI'; }} 
                QGroupBox {{ border: 1px solid #333; font-weight: bold; padding-top: 15px; color: #2196F3; font-size: 11px; }} 
                QListWidget, QTableWidget {{ background-color: {panel}; border: 1px solid #333; color: {fg}; border-radius: 8px; }}
                QPushButton {{ background-color: #222; border: 1px solid #333; padding: 10px; border-radius: 6px; color: white; }}
                QPushButton:hover {{ background-color: #2196F3; border-color: #2196F3; }}
                QHeaderView::section {{ background-color: #252525; color: #888; border: none; padding: 5px; }}
            """)
        else:
            bg, fg, panel = "#f5f5f7", "#1d1d1f", "#ffffff"
            self.setStyleSheet(f"""
                QMainWindow, QWidget {{ background-color: {bg}; color: {fg}; font-family: 'Segoe UI'; }} 
                QGroupBox {{ border: 1px solid #d2d2d7; font-weight: bold; padding-top: 15px; color: #0071e3; font-size: 11px; }} 
                QListWidget, QTableWidget {{ background-color: {panel}; border: 1px solid #d2d2d7; color: {fg}; border-radius: 8px; }} 
                QPushButton {{ background-color: #ffffff; border: 1px solid #d2d2d7; padding: 10px; border-radius: 6px; color: {fg}; }}
                QPushButton:hover {{ background-color: #0071e3; color: white; border-color: #0071e3; }}
                QHeaderView::section {{ background-color: #f0f0f0; color: #666; border: none; padding: 5px; }}
            """)

    def handle_user_menu(self, index):
        if "LOGOUT" in self.user_menu.itemText(index):
            self.close()
            login = LoginScreen()
            if login.exec() == QDialog.Accepted:
                self.user_info = getattr(login, 'user_data', {"type": "guest", "id": "Guest"})
                self.init_ui(); self.show()

    def show_info(self):
        msg = QDialog(self)
        msg.setWindowTitle("Aura Information")
        msg.setFixedSize(550, 500)
        layout = QVBoxLayout(msg)
        layout.setContentsMargins(40, 40, 40, 40)
        
        info_text = QLabel(f"""
            <div style='text-align: center; font-family: Segoe UI Light;'>
                <h1 style='color: #2196F3; font-size: 42px; margin: 0; font-weight: 100;'>AURA</h1>
                <p style='color: #888; font-size: 11px; font-weight: bold; margin-bottom: 20px; letter-spacing: 2px;'>AUTOMATED UNIVERSAL RECONCILIATION AI</p>
                <hr style='border: 0; border-top: 1px solid #eee;'>
                
                <p style='text-align: center; margin-top: 25px; font-size: 14px; line-height: 1.6; color: #555;'>
                    Intelligent financial reconciliation platform designed for extreme accuracy and cross-format data integrity.
                </p>

                <div style='margin-top: 35px; text-align: center;'>
                    <span style='color: #888; font-size: 12px;'>Developed by:</span><br>
                    <b style='font-size: 15px; color: #333;'>Rafirose Khan Shah & Ruhi Khanna</b>
                </div>
                <div style='margin-top: 15px; font-size: 13px; color: #2196F3;'>
                    rafirosekhan@gmail.com | ruhikh282@gmail.com
                </div>
                <div style='margin-top: 50px; font-size: 10px; color: #bbb;'>
                    VERSION 1.2.8<br>
                    © 2026 ASI SYSTEMS ™
                </div>
            </div>
        """)
        info_text.setTextFormat(Qt.RichText); info_text.setWordWrap(True); layout.addWidget(info_text)
        btn = QPushButton("DISMISS")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(msg.accept); layout.addWidget(btn); msg.exec()

    def open_admin_portal(self): AdminPortal(self.db).exec()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode; self.btn_theme.setText("🌙" if self.is_dark_mode else "☀️"); self.apply_theme()
        # Update existing items color for visibility
        for grp_list in [self.list_a, self.list_b]:
            for i in range(grp_list.count()):
                item = grp_list.item(i); widget = grp_list.itemWidget(item)
                if isinstance(widget, FileListWidget):
                    widget.findChild(QLabel).setStyleSheet(f"color: {'#ffffff' if self.is_dark_mode else '#1d1d1f'}; font-size: 13px;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = SplashScreen()
    if splash.exec() == QDialog.Accepted:
        login = LoginScreen()
        if login.exec() == QDialog.Accepted:
            user_data = getattr(login, 'user_data', {"type": "guest", "id": "Guest"})
            window = ReconApp(user_info=user_data)
            window.show()
            sys.exit(app.exec())
