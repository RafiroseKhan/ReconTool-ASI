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

# Add the project root to sys.path for VS Code execution
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.coordinator import ReconCoordinator
from src.desktop.login import LoginScreen, SplashScreen
from src.desktop.admin import AdminPortal
from src.core.database import DatabaseManager

class ComparisonView(QDialog):
    def __init__(self, df_a, df_b, mapping, key_col=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aura - Intelligent Delta View")
        self.setMinimumSize(1200, 750)
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        self.table_a = QTableWidget()
        self.table_b = QTableWidget()
        
        self.populate_and_compare(df_a, df_b, mapping, key_col)
        
        self.table_a.verticalScrollBar().valueChanged.connect(self.table_b.verticalScrollBar().setValue)
        self.table_b.verticalScrollBar().valueChanged.connect(self.table_a.verticalScrollBar().setValue)
        
        splitter.addWidget(self.table_a)
        splitter.addWidget(self.table_b)
        layout.addWidget(splitter)

    def populate_and_compare(self, df_a, df_b, mapping, key_col):
        rows = len(df_a)
        cols = len(df_a.columns)
        for table in [self.table_a, self.table_b]:
            table.setRowCount(rows)
            table.setColumnCount(cols)
            table.setHorizontalHeaderLabels(df_a.columns)

        diff_color = QColor("#ff4d4d") 
        match_color = QColor("#1e3a1e") 
        logic_diff_color = QColor("#ffd54f") 
        missing_color = QColor("#333333")
        text_color = QColor("#ffffff")

        key_in_b = mapping.get(key_col, key_col)
        df_b_search = df_b.copy()

        def normalize_val(v):
            if pd.isna(v): return "nan"
            try:
                f_val = float(v)
                if f_val == int(f_val): return str(int(f_val)).strip()
                return str(f_val).strip()
            except:
                return str(v).strip()

        b_lookup = {}
        for _, row in df_b_search.iterrows():
            k = normalize_val(row[key_in_b])
            if k != "nan": b_lookup[k] = row

        mismatch_cells = 0
        total_data_cells = rows * cols

        for i in range(rows):
            row_a = df_a.iloc[i]
            val_key_a = normalize_val(row_a[key_col])
            row_b = b_lookup.get(val_key_a)

            for j, col_a in enumerate(df_a.columns):
                val_a = str(row_a[col_a]).strip()
                item_a = QTableWidgetItem(val_a)
                item_a.setForeground(text_color)
                
                if row_b is None:
                    item_a.setBackground(missing_color)
                    self.table_a.setItem(i, j, item_a)
                    self.table_b.setItem(i, j, QTableWidgetItem(""))
                    mismatch_cells += 1
                else:
                    col_b = mapping.get(col_a, col_a)
                    val_b = str(row_b[col_b]).strip() if col_b in row_b.index else ""
                    item_b = QTableWidgetItem(val_b)
                    item_b.setForeground(text_color)
                    
                    is_match = (val_a == val_b)
                    is_logical_match = False

                    if not is_match:
                        try:
                            if float(val_a) == float(val_b): is_match = True
                        except: pass
                        
                        if not is_match:
                            norm_a = val_a.replace("/", "-")
                            norm_b = val_b.replace("/", "-")
                            if norm_a == norm_b: is_logical_match = True

                    if is_match: bg = match_color
                    elif is_logical_match:
                        bg = logic_diff_color
                        item_a.setForeground(QColor("#000000"))
                        item_b.setForeground(QColor("#000000"))
                    else:
                        bg = diff_color
                        mismatch_cells += 1
                        item_a.setToolTip(f"B Value: {val_b}")
                        item_b.setToolTip(f"A Value: {val_a}")
                    
                    item_a.setBackground(bg); item_b.setBackground(bg)
                    self.table_a.setItem(i, j, item_a); self.table_b.setItem(i, j, item_b)

        accuracy = ((total_data_cells - mismatch_cells) / total_data_cells * 100) if total_data_cells > 0 else 0
        QMessageBox.information(self, "Aura Insights", f"Dataset Accuracy: {accuracy:.2f}%\nTotal Points Analyzed: {total_data_cells}")

class FileListWidget(QWidget):
    def __init__(self, filename, remove_callback, is_dark=True):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        label = QLabel(filename)
        color = "#ffffff" if is_dark else "#1d1d1f"
        label.setStyleSheet(f"color: {color}; font-size: 13px;")
        
        btn_del = QPushButton("×")
        btn_del.setFixedSize(22, 22)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("""
            QPushButton { background-color: #f44336; color: white; border-radius: 11px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: white; color: #f44336; }
        """)
        btn_del.clicked.connect(remove_callback)
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(btn_del)

class ReconWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, coordinator, files_a, files_b, key_col, mapping, db, user_id, tolerance=0.01):
        super().__init__()
        self.coordinator = coordinator; self.files_a = files_a; self.files_b = files_b
        self.key_col = key_col; self.mapping = mapping; self.db = db
        self.user_id = user_id; self.tolerance = tolerance

    def run(self):
        results = []
        total = len(self.files_a)
        try:
            for i, file_a in enumerate(self.files_a):
                if i < len(self.files_b):
                    file_b = self.files_b[i]
                    output_path = f"Recon_Report_{os.path.basename(file_a)}.xlsx"
                    self.coordinator.run_full_recon(file_a, file_b, self.key_col, self.mapping, output_path, self.tolerance)
                    self.db.log_recon(self.user_id, file_a, file_b, "SUCCESS", output_path)
                    results.append(output_path)
                self.progress.emit(int(((i + 1) / total) * 100))
            self.finished.emit(results)
        except Exception as e: self.error.emit(str(e))

class ReconApp(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info or {"type": "guest", "id": "Guest"}
        self.db = DatabaseManager(); self.coordinator = ReconCoordinator()
        self.is_dark_mode = True; self.files_a = []; self.files_b = []
        self.setWindowTitle("AURA - Automated Universal Reconciliation AI")
        self.setMinimumSize(1200, 850)
        self.init_ui()
        self.apply_theme()
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.centralWidget().setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(800); self.anim.setStartValue(0); self.anim.setEndValue(1); self.anim.start()

    def init_ui(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)

        top_bar = QHBoxLayout()
        # FUTURISTIC APP TITLE (Version 1.2.8 style)
        app_title = QLabel("AURA"); app_title.setFont(QFont("Segoe UI Light", 24))
        app_title.setStyleSheet("color: #2196F3; letter-spacing: 6px;")
        top_bar.addWidget(app_title); top_bar.addSpacing(30)
        
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

        files_group = QGroupBox("STEP 1: DATA SOURCE INGESTION")
        files_layout = QHBoxLayout()
        for grp in ['a', 'b']:
            vbox = QVBoxLayout()
            btn = QPushButton(f"IMPORT GROUP {grp.upper()} DATA")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, g=grp: self.select_files(g))
            list_w = QListWidget(); setattr(self, f"list_{grp}", list_w)
            vbox.addWidget(btn); vbox.addWidget(list_w)
            files_layout.addLayout(vbox)
        files_group.setLayout(files_layout); main_layout.addWidget(files_group)

        config_group = QGroupBox("2. RECONCILIATION STRATEGY")
        config_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("INITIALIZE AI MAPPING")
        self.btn_analyze.setCursor(Qt.PointingHandCursor)
        self.btn_compare_view = QPushButton("SIDE-BY-SIDE ANALYTICS")
        self.btn_compare_view.setCursor(Qt.PointingHandCursor)
        self.btn_compare_view.setEnabled(False)
        btn_row.addWidget(self.btn_analyze); btn_row.addWidget(self.btn_compare_view); btn_row.addStretch()
        config_layout.addLayout(btn_row)

        key_row = QHBoxLayout(); key_row.addWidget(QLabel("PRIMARY IDENTIFIER:")); self.combo_key = QComboBox(); self.combo_key.setFixedWidth(250)
        key_row.addWidget(self.combo_key); key_row.addSpacing(30); key_row.addWidget(QLabel("TOLERANCE:")); self.spin_tolerance = QComboBox()
        self.spin_tolerance.addItems(["0.00", "0.01", "0.05", "1.00"]); self.spin_tolerance.setEditable(True); self.spin_tolerance.setCurrentText("0.01")
        key_row.addWidget(self.spin_tolerance); key_row.addStretch(); config_layout.addLayout(key_row)

        self.mapping_table = QTableWidget(0, 3); self.mapping_table.setHorizontalHeaderLabels(["SOURCE FIELD", "TARGET MATCH", "STATUS"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); config_layout.addWidget(self.mapping_table)
        config_group.setLayout(config_layout); main_layout.addWidget(config_group)

        self.progress_bar = QProgressBar(); self.progress_bar.hide(); main_layout.addWidget(self.progress_bar)
        self.btn_reconcile = QPushButton("RUN GLOBAL RECONCILIATION"); self.btn_reconcile.setFixedHeight(55)
        self.btn_reconcile.setCursor(Qt.PointingHandCursor)
        self.btn_reconcile.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white; letter-spacing: 1px;"); main_layout.addWidget(self.btn_reconcile)

        self.btn_analyze.clicked.connect(self.run_analysis); self.btn_compare_view.clicked.connect(self.open_comparison_view); self.btn_reconcile.clicked.connect(self.run_reconciliation)

    def select_files(self, group):
        paths, _ = QFileDialog.getOpenFileNames(self, "Aura - Ingest Files", "", "Data Files (*.xlsx *.xls *.csv)")
        if paths:
            target_list = self.list_a if group == 'a' else self.list_b
            file_store = self.files_a if group == 'a' else self.files_b
            for p in paths:
                if p not in file_store:
                    file_store.append(p)
                    item = QListWidgetItem(target_list)
                    widget = FileListWidget(os.path.basename(p), lambda path=p, g=group: self.remove_file(g, path), is_dark=self.is_dark_mode)
                    item.setSizeHint(widget.sizeHint())
                    target_list.addItem(item); target_list.setItemWidget(item, widget)

    def remove_file(self, group, path):
        store = self.files_a if group == 'a' else self.files_b
        target_list = self.list_a if group == 'a' else self.list_b
        if path in store:
            idx = store.index(path)
            store.pop(idx)
            target_list.takeItem(idx)

    def run_analysis(self):
        if not self.files_a or not self.files_b: return
        try:
            self.current_df_a = self.coordinator.get_handler(self.files_a[0]).read(self.files_a[0])
            self.current_df_b = self.coordinator.get_handler(self.files_b[0]).read(self.files_b[0])
            self.combo_key.clear(); self.combo_key.addItems(self.current_df_a.columns.tolist())
            self.combo_key.setCurrentText(self.coordinator.mapper.suggest_primary_key(self.current_df_a))
            mapping = self.coordinator.mapper.suggest_mapping(self.current_df_a.columns.tolist(), self.current_df_b.columns.tolist())
            self.update_mapping_table(mapping, self.current_df_b.columns.tolist())
            self.btn_compare_view.setEnabled(True)
        except Exception as e: QMessageBox.critical(self, "Aura Error", str(e))

    def update_mapping_table(self, mapping: dict, cols_b: list):
        self.mapping_table.setRowCount(len(mapping))
        for row, (col_a, col_b) in enumerate(mapping.items()):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(col_a))
            cb = QComboBox(); cb.addItems(cols_b); cb.setCurrentText(col_b)
            self.mapping_table.setCellWidget(row, 1, cb)
            self.mapping_table.setItem(row, 2, QTableWidgetItem("VERIFIED"))

    def open_comparison_view(self):
        mapping = {self.mapping_table.item(r, 0).text(): self.mapping_table.cellWidget(r, 1).currentText() for r in range(self.mapping_table.rowCount())}
        ComparisonView(self.current_df_a, self.current_df_b, mapping, self.combo_key.currentText(), self).exec()

    def run_reconciliation(self):
        mapping = {self.mapping_table.item(r, 0).text(): self.mapping_table.cellWidget(r, 1).currentText() for r in range(self.mapping_table.rowCount())}
        try: tol = float(self.spin_tolerance.currentText())
        except: tol = 0.01
        self.progress_bar.show()
        self.worker = ReconWorker(self.coordinator, self.files_a, self.files_b, self.combo_key.currentText(), mapping, self.db, self.user_info['id'], tolerance=tol)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(lambda: (self.progress_bar.hide(), QMessageBox.information(self, "Aura", "Batch Process Finalized!")))
        self.worker.start()

    def handle_user_menu(self, index):
        if "LOGOUT" in self.user_menu.itemText(index):
            self.close()
            login = LoginScreen()
            if login.exec() == QDialog.Accepted:
                self.user_info = getattr(login, 'user_data', {"type": "guest", "id": "Guest"})
                self.init_ui(); self.show()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode; self.btn_theme.setText("🌙" if self.is_dark_mode else "☀️"); self.apply_theme()
        # Update existing items color for visibility
        for grp_list in [self.list_a, self.list_b]:
            for i in range(grp_list.count()):
                item = grp_list.item(i); widget = grp_list.itemWidget(item)
                if isinstance(widget, FileListWidget):
                    widget.findChild(QLabel).setStyleSheet(f"color: {'#ffffff' if self.is_dark_mode else '#1d1d1f'}; font-size: 13px;")

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
