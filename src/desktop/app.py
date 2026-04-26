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

class DropListWidget(QListWidget):
    def __init__(self, app_instance, group, parent=None):
        super().__init__(parent)
        self.app_instance = app_instance
        self.group = group
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            self.app_instance.process_paths(self.group, paths)
        else:
            super().dropEvent(event)

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.coordinator import ReconCoordinator
from src.desktop.login import LoginScreen, SplashScreen
from src.desktop.admin import AdminPortal
from src.core.database import DatabaseManager

class LocalToleranceDialog(QDialog):
    def __init__(self, mapping, current_local_tols=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Column-Specific Tolerances")
        self.setMinimumSize(500, 400)
        self.layout = QVBoxLayout(self)
        self.local_tols = current_local_tols or {}
        
        self.layout.addWidget(QLabel("Set specific tolerances for numeric columns (leaves global tolerance for others):"))
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Column Name", "Tolerance Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        
        # Populate with mapped numeric columns
        for col_a in mapping.keys():
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(col_a)
            item_name.setFlags(Qt.ItemIsEnabled) # Read only
            self.table.setItem(row, 0, item_name)
            
            val = str(self.local_tols.get(col_a, ""))
            self.table.setItem(row, 1, QTableWidgetItem(val))
            
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("APPLY LOCAL TOLERANCES")
        self.btn_save.clicked.connect(self.accept)
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)

    def get_tolerances(self):
        tols = {}
        for r in range(self.table.rowCount()):
            name = self.table.item(r, 0).text()
            val = self.table.item(r, 1).text().strip()
            if val:
                try: tols[name] = float(val)
                except: pass
        return tols

class DataMappingEditor(QDialog):
    def __init__(self, mapping_file, available_columns=None, parent=None):
        super().__init__(parent)
        self.mapping_file = mapping_file
        self.available_columns = available_columns or []
        self.setWindowTitle("Manage Data Mappings (Translations)")
        self.setMinimumSize(700, 500)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Define values that should be considered identical (e.g., SGP = Singapore):"))
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Target Column", "Source Value", "Mapped Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ ADD NEW RULE")
        self.btn_add.clicked.connect(self.add_row)
        btn_row.addWidget(self.btn_add)
        
        self.btn_del = QPushButton("- REMOVE SELECTED")
        self.btn_del.clicked.connect(self.remove_row)
        btn_row.addWidget(self.btn_del)
        layout.addLayout(btn_row)
        
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        self.btn_save = QPushButton("SAVE CHANGES")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px 30px;")
        self.btn_save.clicked.connect(self.save_data)
        save_layout.addWidget(self.btn_save)
        layout.addLayout(save_layout)
        
        self.load_data()

    def add_row(self, col="", src="", tgt=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Use ComboBox for Column Selection if columns are available
        if self.available_columns:
            combo = QComboBox()
            combo.addItems(self.available_columns)
            if col in self.available_columns:
                combo.setCurrentText(col)
            self.table.setCellWidget(row, 0, combo)
        else:
            self.table.setItem(row, 0, QTableWidgetItem(col))
            
        self.table.setItem(row, 1, QTableWidgetItem(src))
        self.table.setItem(row, 2, QTableWidgetItem(tgt))

    def remove_row(self):
        self.table.removeRow(self.table.currentRow())

    def load_data(self):
        if os.path.exists(self.mapping_file):
            try:
                df = pd.read_csv(self.mapping_file)
                for _, r in df.iterrows():
                    self.add_row(str(r['Column']), str(r['Source Value']), str(r['Target Value']))
            except: pass

    def save_data(self):
        data = []
        for r in range(self.table.rowCount()):
            # Get text from widget if it's a combo, otherwise from item
            widget = self.table.cellWidget(r, 0)
            if isinstance(widget, QComboBox):
                col = widget.currentText().strip()
            else:
                item = self.table.item(r, 0)
                col = item.text().strip() if item else ""
                
            src_item = self.table.item(r, 1)
            tgt_item = self.table.item(r, 2)
            
            src = src_item.text().strip() if src_item else ""
            tgt = tgt_item.text().strip() if tgt_item else ""
            
            if col and src and tgt:
                data.append({"Column": col, "Source Value": src, "Target Value": tgt})
        
        pd.DataFrame(data).to_csv(self.mapping_file, index=False)
        QMessageBox.information(self, "Success", "Data Mapping file updated successfully.")
        self.accept()

class CustomPrimaryKeyDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Composite Primary Key")
        self.setMinimumSize(400, 500)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select two or more columns to create a Composite Key:"))
        
        self.column_list = QListWidget()
        self.column_list.setSelectionMode(QListWidget.MultiSelection)
        for col in columns:
            self.column_list.addItem(col)
        layout.addWidget(self.column_list)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("CREATE COMPOSITE KEY")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)
        
        self.btn_cancel = QPushButton("CANCEL")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)

    def get_selected_columns(self):
        return [item.text() for item in self.column_list.selectedItems()]

class ComparisonView(QDialog):
    def __init__(self, df_a, df_b, mapping, key_col=None, parent=None, accepted_logical_matches=None):
        super().__init__(parent)
        self.setWindowTitle("Aura - Intelligent Delta View")
        self.setMinimumSize(1200, 800)
        self.layout = QVBoxLayout(self)
        
        self.accepted_logical_matches = accepted_logical_matches if accepted_logical_matches is not None else set()
        self.data_mapping = {} # Store translations
        
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
        
        target_key_col = mapping.get(key_col, key_col)
        
        # Handle composite key logic
        key_parts_a = key_col.split("+")
        key_parts_b = [mapping.get(p, p) for p in key_parts_a]
        is_composite = len(key_parts_a) > 1

        rows = len(df_a)
        
        # WE ALWAYS ADD A 'UNIQUE KEY' COLUMN AT THE START FOR CONSISTENCY
        mapped_cols_a = list(mapping.keys())
        display_cols = ["UNIQUE KEY"] + mapped_cols_a
        cols = len(display_cols)
        
        self.table_a.setRowCount(rows); self.table_a.setColumnCount(cols)
        self.table_b.setRowCount(rows); self.table_b.setColumnCount(cols)
        
        self.table_a.setHorizontalHeaderLabels(display_cols)
        
        b_headers = ["UNIQUE KEY (B)"]
        for col_a in mapped_cols_a:
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
        # Support composite keys in lookup
        for _, row in df_b.iterrows():
            if is_composite:
                # Use key_parts_b (mapped columns from B) to build the lookup key
                k = "+".join([normalize_val(row.get(p, "nan")) for p in key_parts_b])
            else:
                # Use target_key_col (mapped single column from B)
                k = normalize_val(row.get(target_key_col, "nan"))
            b_lookup[k] = row

        # Colors
        match_color = self.match_color 
        logic_diff_color = self.logic_diff_color 
        diff_color = QColor("#ff4d4d") 
        missing_color = QColor("#333333")
        text_color = QColor("#ffffff")

        # Standardize both sides to use '+' joined string for composite keys
        def get_comp_key(row, parts):
            return "+".join([normalize_val(row.get(p, "nan")) for p in parts])

        # 3. Populate
        for i in range(rows):
            row_a = df_a.iloc[i]
            
            # Generate the Key for this row (Composite or Single)
            if is_composite:
                val_key_a = get_comp_key(row_a, key_parts_a)
            else:
                val_key_a = normalize_val(row_a.get(key_col, "nan"))
                
            row_b = b_lookup.get(val_key_a)

            # SET THE UNIQUE KEY COLUMN (Index 0)
            item_key_a = QTableWidgetItem(val_key_a)
            item_key_a.setForeground(text_color); item_key_a.setFont(QFont("Segoe UI", 9, QFont.Bold))
            item_key_a.setBackground(match_color if row_b is not None else missing_color)
            self.table_a.setItem(i, 0, item_key_a)
            
            # B Side Key
            comp_b_text = ""
            if row_b is not None:
                if is_composite:
                    comp_b_text = get_comp_key(row_b, key_parts_b)
                else:
                    comp_b_text = normalize_val(row_b.get(target_key_col, "nan"))
            else:
                comp_b_text = "MISSING"
                
            item_key_b = QTableWidgetItem(comp_b_text)
            item_key_b.setForeground(text_color if row_b is not None else QColor("#888"))
            item_key_b.setFont(QFont("Segoe UI", 9, QFont.Bold))
            item_key_b.setBackground(match_color if row_b is not None else missing_color)
            self.table_b.setItem(i, 0, item_key_b)

            # POPULATE DATA COLUMNS (Starting at Index 1)
            for j, col_a in enumerate(mapped_cols_a):
                # A Side
                if '+' in col_a:
                    val_a = get_comp_key(row_a, col_a.split('+'))
                else:
                    val_a = normalize_val(row_a.get(col_a, "nan"))
                    
                item_a = QTableWidgetItem(val_a)
                item_a.setForeground(text_color)
                self.table_a.setItem(i, j + 1, item_a)
                
                # B Side
                if row_b is not None:
                    col_b = mapping.get(col_a)
                    val_b = ""
                    if col_b:
                        if '+' in col_b:
                            val_b = get_comp_key(row_b, col_b.split('+'))
                        elif col_b in row_b.index:
                            val_b = normalize_val(row_b[col_b])
                    
                    item_b = QTableWidgetItem(val_b)
                    item_b.setForeground(text_color)
                    
                    # Logic
                    # Apply Data Mapping for UI Comparison
                    val_a_mapped = val_a
                    if col_a in self.data_mapping and val_a in self.data_mapping[col_a]:
                        val_a_mapped = self.data_mapping[col_a][val_a]
                    
                    val_b_mapped = val_b
                    if col_b in self.data_mapping and val_b in self.data_mapping[col_b]:
                        val_b_mapped = self.data_mapping[col_b][val_b]

                    # Case-Insensitive Match Logic
                    is_match = (str(val_a_mapped).strip().lower() == str(val_b_mapped).strip().lower())
                    is_logical_match = False
                    numeric_diff = None
                    if not is_match:
                        try:
                            num_a = float(val_a_mapped)
                            num_b = float(val_b_mapped)
                            if num_a == num_b: is_match = True
                            else: numeric_diff = num_a - num_b
                        except: pass
                        
                        # Date/Format Logical Match (Case Insensitive)
                        if not is_match and str(val_a_mapped).replace("/", "-").lower() == str(val_b_mapped).replace("/", "-").lower(): 
                            is_logical_match = True

                    bg = match_color
                    if (i, col_a) in self.accepted_logical_matches: bg = match_color
                    elif is_match: bg = match_color
                    elif is_logical_match:
                        bg = logic_diff_color
                        item_a.setForeground(QColor("#000000")); item_b.setForeground(QColor("#000000"))
                    else:
                        bg = diff_color
                        if numeric_diff is not None:
                            sign = "+" if numeric_diff > 0 else ""
                            item_b.setText(f"{val_b}   [ Δ {sign}{numeric_diff:g} ]")
                    
                    item_a.setBackground(bg); item_b.setBackground(bg)
                    self.table_b.setItem(i, j + 1, item_b)
                else:
                    item_a.setBackground(missing_color)
                    item_b = QTableWidgetItem("MISSING")
                    item_b.setBackground(missing_color); item_b.setForeground(QColor("#888"))
                    self.table_b.setItem(i, j + 1, item_b)

class ManualPairingDialog(QDialog):
    def __init__(self, app_instance, is_dark=True):
        super().__init__()
        self.app = app_instance
        self.setWindowTitle("Manual File Pairing")
        self.setMinimumSize(600, 400)
        self.setStyleSheet(app_instance.styleSheet())
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select a file from Group A and Group B, then click 'Link Pair' to align them."))
        
        self.lists_layout = QHBoxLayout()
        self.list_a = QListWidget()
        self.list_b = QListWidget()
        
        self.refresh_lists()
        
        self.lists_layout.addWidget(self.list_a)
        self.lists_layout.addWidget(self.list_b)
        layout.addLayout(self.lists_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_link = QPushButton("LINK PAIR")
        self.btn_link.clicked.connect(self.link_pair)
        btn_layout.addWidget(self.btn_link)
        
        self.btn_close = QPushButton("DONE")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

    def refresh_lists(self):
        self.list_a.clear()
        self.list_b.clear()
        for p in self.app.files_a:
            self.list_a.addItem(os.path.basename(p))
        for p in self.app.files_b:
            self.list_b.addItem(os.path.basename(p))

    def link_pair(self):
        row_a = self.list_a.currentRow()
        row_b = self.list_b.currentRow()
        if row_a < 0 or row_b < 0:
            QMessageBox.warning(self, "Warning", "Please select a file from both lists.")
            return
            
        file_a = self.app.files_a.pop(row_a)
        file_b = self.app.files_b.pop(row_b)
        
        self.app.files_a.insert(0, file_a)
        self.app.files_b.insert(0, file_b)
        
        self.refresh_lists()

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

    def __init__(self, coordinator, files_a, files_b, key_col, mapping, db, user_id, tolerance, accepted_matches, auto_map=False):
        super().__init__()
        self.coordinator = coordinator; self.files_a = files_a; self.files_b = files_b
        self.key_col = key_col; self.mapping = mapping; self.db = db
        self.user_id = user_id; self.tolerance = tolerance; self.accepted_matches = accepted_matches
        self.auto_map = auto_map

    def run(self):
        results = []
        try:
            for i, file_a in enumerate(self.files_a):
                if i < len(self.files_b):
                    file_b = self.files_b[i]
                    output_path = f"Recon_Report_{os.path.basename(file_a)}.xlsx"
                    
                    current_key = self.key_col
                    current_mapping = self.mapping
                    
                    if self.auto_map:
                        df_a = self.coordinator.get_handler(file_a).read(file_a)
                        df_b = self.coordinator.get_handler(file_b).read(file_b)
                        current_key = self.coordinator.mapper.suggest_primary_key(df_a)
                        current_mapping = self.coordinator.mapper.suggest_mapping(df_a.columns.tolist(), df_b.columns.tolist())

                    self.coordinator.run_full_recon(file_a, file_b, current_key, current_mapping, output_path, self.tolerance, self.accepted_matches)
                    self.db.log_recon(self.user_id, file_a, file_b, "SUCCESS", output_path)
                    results.append(output_path)
                self.progress.emit(int(((i + 1) / len(self.files_a)) * 100))
            self.finished.emit(results)
        except Exception as e: 
            import traceback
            err_msg = traceback.format_exc()
            with open('error_log_app.txt', 'a') as f:
                f.write(err_msg + "\n")
            self.error.emit(str(e))

class ReconApp(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info or {"type": "guest", "id": "Guest"}
        self.db = DatabaseManager(); self.coordinator = ReconCoordinator()
        self.is_dark_mode = True; self.files_a = []; self.files_b = []
        self.accepted_logical_matches = set()
        self.local_tolerances = {} # New: store per-column tols
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
            vbox = QVBoxLayout()
            h_btn = QHBoxLayout()
            h_btn.setSpacing(10)
            
            btn_file = QPushButton(f"📄 ADD FILES ({grp.upper()})")
            btn_file.setCursor(Qt.PointingHandCursor)
            btn_file.clicked.connect(lambda c=0, g=grp: self.select_files(g))
            
            btn_folder = QPushButton(f"📁 ADD FOLDER")
            btn_folder.setCursor(Qt.PointingHandCursor)
            btn_folder.clicked.connect(lambda c=0, g=grp: self.select_folder(g))
            
            h_btn.addWidget(btn_file)
            h_btn.addWidget(btn_folder)
            
            lst = DropListWidget(self, grp)
            setattr(self, f"list_{grp}", lst)
            vbox.addLayout(h_btn)
            vbox.addWidget(lst)
            files_layout.addLayout(vbox)
        
        outer_files_layout = QVBoxLayout()
        outer_files_layout.addLayout(files_layout)
        
        self.btn_manual_pair = QPushButton("MANUAL FILE PAIRING")
        self.btn_manual_pair.clicked.connect(self.open_manual_pairing)
        self.btn_manual_pair.setStyleSheet("background-color: #555; font-weight: bold; margin-top: 10px;")
        outer_files_layout.addWidget(self.btn_manual_pair)
        
        files_group.setLayout(outer_files_layout); main_layout.addWidget(files_group)

        config_group = QGroupBox("2. MAPPING STRATEGY")
        config_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("INITIALIZE AI MAPPING"); self.btn_analyze.clicked.connect(self.run_analysis)
        
        self.combo_pair_selector = QComboBox()
        self.combo_pair_selector.setFixedWidth(200)
        self.combo_pair_selector.currentIndexChanged.connect(self.run_analysis)
        
        self.btn_add_mapping = QPushButton("+ ADD FIELD"); self.btn_add_mapping.clicked.connect(self.add_mapping_row)
        
        self.btn_manage_translations = QPushButton("MANAGE TRANSLATIONS"); self.btn_manage_translations.clicked.connect(self.open_translation_manager)
        self.btn_manage_translations.setStyleSheet("background-color: #673AB7; color: white;")
        
        self.btn_compare_view = QPushButton("SIDE-BY-SIDE ANALYTICS"); self.btn_compare_view.setEnabled(False); self.btn_compare_view.clicked.connect(self.open_comparison_view)
        
        btn_row.addWidget(self.btn_analyze); 
        btn_row.addWidget(QLabel("SELECT PAIR:"))
        btn_row.addWidget(self.combo_pair_selector)
        btn_row.addWidget(self.btn_add_mapping); 
        btn_row.addWidget(self.btn_manage_translations)
        btn_row.addWidget(self.btn_compare_view); btn_row.addStretch()
        config_layout.addLayout(btn_row)

        key_row = QHBoxLayout(); key_row.addWidget(QLabel("PRIMARY KEY:")); self.combo_key = QComboBox(); self.combo_key.setEditable(True); self.combo_key.setFixedWidth(200); key_row.addWidget(self.combo_key)
        
        self.btn_composite_key = QPushButton("＋ COMPOSITE"); self.btn_composite_key.setFixedWidth(100)
        self.btn_composite_key.clicked.connect(self.create_composite_key)
        self.btn_composite_key.setStyleSheet("background-color: #444; font-size: 10px; font-weight: bold;")
        key_row.addWidget(self.btn_composite_key)
        
        key_row.addSpacing(20); key_row.addWidget(QLabel("GLOBAL TOL:")); self.spin_tol = QComboBox(); self.spin_tol.addItems(["0.00", "0.01", "0.05"]); self.spin_tol.setEditable(True); self.spin_tol.setFixedWidth(80); self.spin_tol.setCurrentText("0.01"); key_row.addWidget(self.spin_tol)
        
        self.btn_local_tol = QPushButton("⚙️ COLUMN TOLERANCE"); self.btn_local_tol.setFixedWidth(150)
        self.btn_local_tol.clicked.connect(self.open_local_tolerance_manager)
        self.btn_local_tol.setStyleSheet("background-color: #555; font-size: 10px; font-weight: bold;")
        key_row.addWidget(self.btn_local_tol)

        key_row.addStretch(); config_layout.addLayout(key_row)

        self.mapping_table = QTableWidget(0, 3); self.mapping_table.setHorizontalHeaderLabels(["SOURCE (A)", "TARGET (B)", "STATUS"]); self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); config_layout.addWidget(self.mapping_table)
        config_group.setLayout(config_layout); main_layout.addWidget(config_group)

        self.progress_bar = QProgressBar(); self.progress_bar.hide(); main_layout.addWidget(self.progress_bar)
        
        recon_btns_layout = QHBoxLayout()
        self.btn_reconcile = QPushButton("RUN RECONCILIATION (SELECTED PAIR)"); self.btn_reconcile.setFixedHeight(55)
        self.btn_reconcile.setCursor(Qt.PointingHandCursor)
        self.btn_reconcile.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white; letter-spacing: 1px;")
        
        self.btn_reconcile_global = QPushButton("RUN GLOBAL RECONCILIATION"); self.btn_reconcile_global.setFixedHeight(55)
        self.btn_reconcile_global.setCursor(Qt.PointingHandCursor)
        self.btn_reconcile_global.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white; letter-spacing: 1px;")
        
        recon_btns_layout.addWidget(self.btn_reconcile)
        recon_btns_layout.addWidget(self.btn_reconcile_global)
        main_layout.addLayout(recon_btns_layout)

        self.btn_analyze.clicked.connect(self.run_analysis); self.btn_compare_view.clicked.connect(self.open_comparison_view); self.btn_reconcile.clicked.connect(self.run_reconciliation); self.btn_reconcile_global.clicked.connect(self.run_global_reconciliation)

    def update_pair_selector(self):
        self.combo_pair_selector.blockSignals(True)
        self.combo_pair_selector.clear()
        max_len = max(len(self.files_a), len(self.files_b))
        for i in range(max_len):
            fa = os.path.basename(self.files_a[i]) if i < len(self.files_a) else "None"
            fb = os.path.basename(self.files_b[i]) if i < len(self.files_b) else "None"
            self.combo_pair_selector.addItem(f"Pair {i+1}: {fa} vs {fb}", i)
        self.combo_pair_selector.blockSignals(False)

    def align_files_by_name(self):
        bases_a = [os.path.basename(p) for p in self.files_a]
        bases_b = [os.path.basename(p) for p in self.files_b]
        
        common = set(bases_a).intersection(set(bases_b))
        if not common: return
        
        sorted_common = sorted(list(common))
        new_a, new_b = [], []
        
        for base in sorted_common:
            new_a.append(self.files_a[bases_a.index(base)])
            new_b.append(self.files_b[bases_b.index(base)])
            
        for p in self.files_a:
            if os.path.basename(p) not in common: new_a.append(p)
        for p in self.files_b:
            if os.path.basename(p) not in common: new_b.append(p)
            
        self.files_a, self.files_b = new_a, new_b
        
        for grp in ['a', 'b']:
            store = self.files_a if grp == 'a' else self.files_b
            target_list = self.list_a if grp == 'a' else self.list_b
            target_list.clear()
            for p in store:
                item = QListWidgetItem(target_list)
                w = FileListWidget(os.path.basename(p), lambda checked=False, g=grp, p_path=p: self.remove_file(g, p_path), self.is_dark_mode)
                item.setSizeHint(w.sizeHint()); target_list.addItem(item); target_list.setItemWidget(item, w)
        self.update_pair_selector()

    def select_files(self, group):
        paths, _ = QFileDialog.getOpenFileNames(self, f"Select Files for Group {group.upper()}", "", "Data Files (*.xlsx *.csv *.pdf)")
        if paths:
            self.process_paths(group, paths)

    def select_folder(self, group):
        folder = QFileDialog.getExistingDirectory(self, f"Select Folder for Group {group.upper()}")
        if folder:
            self.process_paths(group, [folder])

    def process_paths(self, group, selected_paths):
        all_paths = []
        for path in selected_paths:
            if os.path.isdir(path):
                folder_files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(('.xlsx', '.csv', '.pdf'))]
                all_paths.extend(folder_files)
            elif path.lower().endswith(('.xlsx', '.csv', '.pdf')):
                all_paths.append(path)
        
        if all_paths:
            target_list = self.list_a if group == 'a' else self.list_b
            file_store = self.files_a if group == 'a' else self.files_b
            for p in all_paths:
                if p not in file_store:
                    file_store.append(p)
                    item = QListWidgetItem(target_list)
                    w = FileListWidget(os.path.basename(p), lambda checked=False, g=group, p_path=p: self.remove_file(g, p_path), self.is_dark_mode)
                    item.setSizeHint(w.sizeHint()); target_list.addItem(item); target_list.setItemWidget(item, w)
            self.align_files_by_name()
            self.update_pair_selector()
        self.update_pair_selector()

    def open_manual_pairing(self):
        if not self.files_a or not self.files_b:
            QMessageBox.information(self, "Info", "Please import files into both groups first.")
            return
        dlg = ManualPairingDialog(self, self.is_dark_mode)
        if dlg.exec():
            # Update main UI lists
            for grp in ['a', 'b']:
                store = self.files_a if grp == 'a' else self.files_b
                target_list = self.list_a if grp == 'a' else self.list_b
                target_list.clear()
                for p in store:
                    item = QListWidgetItem(target_list)
                    w = FileListWidget(os.path.basename(p), lambda checked=False, g=grp, p_path=p: self.remove_file(g, p_path), self.is_dark_mode)
                    item.setSizeHint(w.sizeHint()); target_list.addItem(item); target_list.setItemWidget(item, w)
            self.update_pair_selector()

    def remove_file(self, group, path):
        store = self.files_a if group == 'a' else self.files_b
        target_list = self.list_a if group == 'a' else self.list_b
        if path in store:
            idx = store.index(path); store.pop(idx); target_list.takeItem(idx)
            self.update_pair_selector()

    def run_analysis(self):
        if not self.files_a or not self.files_b: return
        idx = self.combo_pair_selector.currentIndex() if self.combo_pair_selector.currentIndex() >= 0 else 0
        if idx >= len(self.files_a) or idx >= len(self.files_b): return
        
        try:
            self.current_df_a = self.coordinator.get_handler(self.files_a[idx]).read(self.files_a[idx])
            self.current_df_b = self.coordinator.get_handler(self.files_b[idx]).read(self.files_b[idx])
            
            if self.current_df_a.empty:
                QMessageBox.warning(self, "Warning", "Source A file appears to be empty or contains no readable tables.")
                return
            if self.current_df_b.empty:
                QMessageBox.warning(self, "Warning", "Source B file appears to be empty or contains no readable tables.")
                return

            self.accepted_logical_matches = set()
            self.combo_key.clear(); self.combo_key.addItems(self.current_df_a.columns.tolist())
            self.combo_key.setCurrentText(self.coordinator.mapper.suggest_primary_key(self.current_df_a))
            mapping = self.coordinator.mapper.suggest_mapping(self.current_df_a.columns.tolist(), self.current_df_b.columns.tolist())
            self.update_mapping_table(mapping)
            self.btn_compare_view.setEnabled(True)
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            with open('error_log_app.txt', 'a') as f:
                f.write(err_msg + "\n")
            QMessageBox.critical(self, "Error", str(e))

    def update_mapping_table(self, mapping):
        self.mapping_table.setRowCount(0)
        for ca, cb in mapping.items():
            self.add_mapping_row(ca, cb)

    def add_mapping_row(self, val_a=None, val_b=None):
        if not hasattr(self, 'current_df_a'): return
        row = self.mapping_table.rowCount(); self.mapping_table.insertRow(row)
        
        def create_selector(cols, initial_val):
            w = QWidget()
            layout = QHBoxLayout(w)
            layout.setContentsMargins(2, 2, 2, 2)
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(cols)
            if initial_val: cb.setCurrentText(initial_val)
            
            btn = QPushButton("≡")
            btn.setFixedWidth(25)
            btn.setToolTip("Select multiple columns")
            def open_selector():
                dlg = CustomPrimaryKeyDialog(cols, self)
                dlg.setWindowTitle("Select Multiple Columns")
                if dlg.exec() == QDialog.Accepted:
                    selected = dlg.get_selected_columns()
                    if selected:
                        cb.setCurrentText("+".join(selected))
            btn.clicked.connect(open_selector)
            
            layout.addWidget(cb)
            layout.addWidget(btn)
            return w
            
        w_a = create_selector(self.current_df_a.columns.tolist(), val_a)
        self.mapping_table.setCellWidget(row, 0, w_a)
        
        w_b = create_selector(self.current_df_b.columns.tolist(), val_b)
        self.mapping_table.setCellWidget(row, 1, w_b)
        
        self.mapping_table.setItem(row, 2, QTableWidgetItem("READY"))

    def get_current_mapping(self):
        m = {}
        for r in range(self.mapping_table.rowCount()):
            widget_a = self.mapping_table.cellWidget(r, 0)
            widget_b = self.mapping_table.cellWidget(r, 1)
            
            ca = widget_a.findChild(QComboBox).currentText() if widget_a else ""
            cb = widget_b.findChild(QComboBox).currentText() if widget_b else ""
            
            if ca and cb:
                m[ca] = cb
        return m

    def open_comparison_view(self):
        view = ComparisonView(self.current_df_a, self.current_df_b, self.get_current_mapping(), self.combo_key.currentText(), self, set(self.accepted_logical_matches))
        
        # Apply Data Mapping to the Comparison View
        map_file = os.path.join(project_root, "data", "data_mapping.csv")
        if os.path.exists(map_file):
            try:
                map_df = pd.read_csv(map_file)
                data_map_dict = {}
                for _, row in map_df.iterrows():
                    col = str(row['Column']).strip()
                    src = str(row['Source Value']).strip()
                    tgt = str(row['Target Value']).strip()
                    if col not in data_map_dict: data_map_dict[col] = {}
                    data_map_dict[col][src] = tgt
                view.data_mapping = data_map_dict
                # Refresh view with mapping
                view.populate_and_compare(self.current_df_a, self.current_df_b, self.get_current_mapping(), self.combo_key.currentText())
            except: pass

        if view.exec() == QDialog.Accepted:
            self.accepted_logical_matches = view.accepted_logical_matches
            QMessageBox.information(self, "Aura", "Choices Applied to Memory.")

    def run_global_reconciliation(self):
        mapping = self.get_current_mapping()
        try: tol = float(self.spin_tol.currentText())
        except: tol = 0.01
        
        # Merge global tolerance with local overrides for the engine
        full_tolerances = {"default": tol}
        full_tolerances.update(self.local_tolerances)
        
        if not self.files_a or not self.files_b:
            QMessageBox.critical(self, "Error", "No files available for global reconciliation.")
            return

        min_len = min(len(self.files_a), len(self.files_b))
        paired_files_a = self.files_a[:min_len]
        paired_files_b = self.files_b[:min_len]

        self.progress_bar.show()
        self.btn_reconcile.setEnabled(False)
        self.btn_reconcile_global.setEnabled(False)
        
        self.worker = ReconWorker(self.coordinator, paired_files_a, paired_files_b, self.combo_key.currentText(), mapping, self.db, self.user_info['id'], full_tolerances, self.accepted_logical_matches, auto_map=True)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(lambda: (self.progress_bar.hide(), self.btn_reconcile.setEnabled(True), self.btn_reconcile_global.setEnabled(True), QMessageBox.information(self, "Aura", "Global Process Complete.")))
        self.worker.error.connect(lambda e: (self.progress_bar.hide(), self.btn_reconcile.setEnabled(True), self.btn_reconcile_global.setEnabled(True), QMessageBox.critical(self, "Error", e)))
        self.worker.start()

    def run_reconciliation(self):
        mapping = self.get_current_mapping()
        try: tol = float(self.spin_tol.currentText())
        except: tol = 0.01
        
        # Merge global tolerance with local overrides for the engine
        full_tolerances = {"default": tol}
        full_tolerances.update(self.local_tolerances)
        
        idx = self.combo_pair_selector.currentIndex() if self.combo_pair_selector.currentIndex() >= 0 else 0
        if idx >= len(self.files_a) or idx >= len(self.files_b):
            QMessageBox.critical(self, "Error", "No valid pair selected for reconciliation.")
            return
            
        selected_file_a = [self.files_a[idx]]
        selected_file_b = [self.files_b[idx]]

        self.progress_bar.show(); self.btn_reconcile.setEnabled(False)
        self.worker = ReconWorker(self.coordinator, selected_file_a, selected_file_b, self.combo_key.currentText(), mapping, self.db, self.user_info['id'], full_tolerances, self.accepted_logical_matches, auto_map=False)
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
                    VERSION 1.0.0<br>
                    © 2026 ASI SYSTEMS ™
                </div>
            </div>
        """)
        info_text.setTextFormat(Qt.RichText); info_text.setWordWrap(True); layout.addWidget(info_text)
        btn = QPushButton("DISMISS")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(msg.accept); layout.addWidget(btn); msg.exec()

    def open_admin_portal(self): AdminPortal(self.db).exec()

    def open_local_tolerance_manager(self):
        if not hasattr(self, 'current_df_a'):
            QMessageBox.warning(self, "Warning", "Please run analysis on a pair first.")
            return
        mapping = self.get_current_mapping()
        dlg = LocalToleranceDialog(mapping, self.local_tolerances, self)
        if dlg.exec() == QDialog.Accepted:
            self.local_tolerances = dlg.get_tolerances()
            QMessageBox.information(self, "Aura", "Column-specific tolerances applied.")

    def open_translation_manager(self):
        map_file = os.path.join(project_root, "data", "data_mapping.csv")
        cols = []
        if hasattr(self, 'current_df_a'):
            cols = self.current_df_a.columns.tolist()
        
        dlg = DataMappingEditor(map_file, available_columns=cols, parent=self)
        dlg.exec()

    def create_composite_key(self):
        if not hasattr(self, 'current_df_a'):
            QMessageBox.warning(self, "Warning", "Please run analysis on a pair first.")
            return
            
        dlg = CustomPrimaryKeyDialog(self.current_df_a.columns.tolist(), self)
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected_columns()
            if len(selected) < 2:
                QMessageBox.warning(self, "Warning", "Please select at least 2 columns.")
                return
            
            # Create the composite key string
            composite_key_name = "+".join(selected)
            
            # Check if it already exists in the combo, if not add it
            if self.combo_key.findText(composite_key_name) == -1:
                self.combo_key.addItem(composite_key_name)
            
            self.combo_key.setCurrentText(composite_key_name)
            QMessageBox.information(self, "Aura", f"Composite Key '{composite_key_name}' created and selected.")

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
