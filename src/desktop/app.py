from src.core.coordinator import ReconCoordinator
from src.desktop.login import LoginScreen
from src.desktop.admin import AdminPortal
from src.core.database import DatabaseManager
import sys
import os
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QComboBox, QGroupBox, QListWidget, QDialog, QProgressBar,
                             QTabWidget, QSplitter, QFrame)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap

class ComparisonView(QDialog):
    def __init__(self, df_a, df_b, mapping, key_col=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Side-by-Side Comparison")
        self.setMinimumSize(1200, 750)
        layout = QVBoxLayout(self)
        
        # Comparison logic: Align B to A based on mapping
        inv_mapping = {v: k for k, v in mapping.items()}
        df_b_aligned = df_b.rename(columns=inv_mapping)
        
        splitter = QSplitter(Qt.Horizontal)
        self.table_a = QTableWidget()
        self.table_b = QTableWidget()
        
        self.populate_and_compare(df_a, df_b_aligned, mapping, key_col)
        
        # Synchronize Scrolling
        self.table_a.verticalScrollBar().valueChanged.connect(self.table_b.verticalScrollBar().setValue)
        self.table_b.verticalScrollBar().valueChanged.connect(self.table_a.verticalScrollBar().setValue)
        
        splitter.addWidget(self.table_a)
        splitter.addWidget(self.table_b)
        layout.addWidget(splitter)

    def populate_and_compare(self, df_a, df_b, mapping, key_col):
        # 1. Prepare Tables
        rows = len(df_a)
        cols = len(df_a.columns)
        for table in [self.table_a, self.table_b]:
            table.setRowCount(rows)
            table.setColumnCount(cols)
            table.setHorizontalHeaderLabels(df_a.columns)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # Style definitions
        diff_color = QColor("#ff4d4d") # Red
        diff_text = QColor("#ffffff")
        match_color = QColor("#1e3a1e") # Dark Green
        match_text = QColor("#e0e0e0")
        missing_color = QColor("#3d3d3d")

        total_cells = 0
        mismatch_cells = 0

        # 2. Setup Indexing for B using the mapped key
        key_in_b = mapping.get(key_col, key_col)
        
        # Create a copy of B with string keys for reliable lookup
        df_b_search = df_b.copy()
        if key_in_b in df_b_search.columns:
            df_b_search[key_in_b] = df_b_search[key_in_b].astype(str).str.strip()
            df_b_idx = df_b_search.set_index(key_in_b)
        else:
            df_b_idx = df_b_search

        for i in range(rows):
            row_a = df_a.iloc[i]
            val_key_a = str(row_a[key_col]).strip()
            
            # Find matching row in B
            row_b = None
            try:
                if key_in_b in df_b_search.columns:
                    if val_key_a in df_b_idx.index:
                        match_data = df_b_idx.loc[val_key_a]
                        row_b = match_data.iloc[0] if isinstance(match_data, pd.DataFrame) else match_data
            except Exception:
                row_b = None

            for j, col_a in enumerate(df_a.columns):
                val_a = str(row_a[col_a]).strip()
                item_a = QTableWidgetItem(val_a)
                total_cells += 1
                
                if row_b is None:
                    # Row missing in B
                    item_a.setBackground(missing_color)
                    self.table_a.setItem(i, j, item_a)
                    self.table_b.setItem(i, j, QTableWidgetItem(""))
                    mismatch_cells += 1
                else:
                    # Map Group A column to Group B column
                    col_b = mapping.get(col_a, col_a)
                    val_b = str(row_b[col_b]).strip() if col_b in row_b.index else ""
                    item_b = QTableWidgetItem(val_b)
                    
                    if val_a == val_b:
                        bg, fg = match_color, match_text
                    else:
                        bg, fg = diff_color, diff_text
                        mismatch_cells += 1
                        item_a.setToolTip(f"B value: {val_b}")
                        item_b.setToolTip(f"A value: {val_a}")
                    
                    item_a.setBackground(bg); item_a.setForeground(fg)
                    item_b.setBackground(bg); item_b.setForeground(fg)
                    self.table_a.setItem(i, j, item_a)
                    self.table_b.setItem(i, j, item_b)

        # 3. Accuracy Calculation fix
        # Accuracy is the % of cells that matched
        accuracy = ((total_cells - mismatch_cells) / total_cells * 100) if total_cells > 0 else 0
        diff_rate = 100 - accuracy

        QMessageBox.information(self, "Comparison Statistics", 
                                f"Comparison Complete!\n\n"
                                f"Accuracy Score: {accuracy:.2f}%\n"
                                f"Difference Rate: {diff_rate:.2f}%\n"
                                f"Total Cells Scanned: {total_cells}\n"
                                f"Mismatched Cells: {mismatch_cells}")

class ReconWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, coordinator, files_a, files_b, key_col, mapping, db, user_id, tolerance=0.01):
        super().__init__()
        self.coordinator = coordinator
        self.files_a = files_a; self.files_b = files_b
        self.key_col = key_col; self.mapping = mapping
        self.db = db; self.user_id = user_id
        self.tolerance = tolerance

    def run(self):
        results = []
        total = len(self.files_a)
        try:
            for i, file_a in enumerate(self.files_a):
                if i < len(self.files_b):
                    file_b = self.files_b[i]
                    self.status.emit(f"Processing: {os.path.basename(file_a)} vs {os.path.basename(file_b)}...")
                    output_path = f"Recon_Report_{os.path.basename(file_a)}.xlsx"
                    self.coordinator.run_full_recon(file_a, file_b, key_col=self.key_col, mapping=self.mapping, output_path=output_path, tolerance=self.tolerance)
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
        self.is_dark_mode = True
        self.files_a = []; self.files_b = []
        self.setWindowTitle("AI Recon Tool - Professional Suite")
        self.setMinimumSize(1200, 850)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top Bar
        top_bar = QHBoxLayout()
        self.btn_info = QPushButton("ℹ")
        self.btn_info.setFixedSize(35, 35)
        self.btn_info.setCursor(Qt.PointingHandCursor)
        self.btn_info.clicked.connect(self.show_info)
        top_bar.addWidget(self.btn_info)

        if self.db.is_admin(self.user_info['id']):
            self.btn_admin = QPushButton("🛡️ Admin")
            self.btn_admin.setFixedWidth(100)
            self.btn_admin.clicked.connect(self.open_admin_portal)
            top_bar.addWidget(self.btn_admin)
        
        top_bar.addStretch()

        self.btn_theme = QPushButton("🌙" if self.is_dark_mode else "☀️")
        self.btn_theme.setFixedSize(40, 35)
        self.btn_theme.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.btn_theme)

        self.user_menu = QComboBox()
        self.user_menu.addItem(f"👤 {self.user_info['id']}")
        self.user_menu.addItem("Logout")
        self.user_menu.setFixedWidth(150)
        self.user_menu.activated.connect(self.handle_user_menu)
        top_bar.addWidget(self.user_menu)
        main_layout.addLayout(top_bar)

        # 1. File Selection
        files_group = QGroupBox("1. Select Batch Files")
        files_group.setObjectName("FileGroup")
        files_layout = QHBoxLayout()
        files_layout.setContentsMargins(15, 25, 15, 15) # Top margin for title spacing
        
        vbox_a = QVBoxLayout()
        self.btn_add_a = QPushButton("Add Group A")
        self.btn_add_a.setFixedWidth(150)
        self.list_a = QListWidget()
        vbox_a.addWidget(self.btn_add_a); vbox_a.addWidget(self.list_a)
        
        vbox_b = QVBoxLayout()
        self.btn_add_b = QPushButton("Add Group B")
        self.btn_add_b.setFixedWidth(150)
        self.list_b = QListWidget()
        vbox_b.addWidget(self.btn_add_b); vbox_b.addWidget(self.list_b)
        
        files_layout.addLayout(vbox_a); files_layout.addLayout(vbox_b)
        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # 2. Config
        config_group = QGroupBox("2. Review & Configure Analysis")
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(15, 25, 15, 15)
        
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("Analyze Files & Suggest Mapping")
        self.btn_analyze.setFixedWidth(250)
        self.btn_compare_view = QPushButton("Side-by-Side Comparison") # Text button
        self.btn_compare_view.setFixedWidth(200)
        self.btn_compare_view.setEnabled(False)
        btn_row.addWidget(self.btn_analyze)
        btn_row.addWidget(self.btn_compare_view)
        btn_row.addStretch()
        config_layout.addLayout(btn_row)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Primary Key (Unique ID):"))
        self.combo_key = QComboBox()
        self.combo_key.setFixedWidth(250)
        key_row.addWidget(self.combo_key)
        
        key_row.addSpacing(20)
        key_row.addWidget(QLabel("Tolerance:"))
        self.spin_tolerance = QComboBox()
        self.spin_tolerance.addItems(["0.00", "0.01", "0.05", "1.00", "10.00"])
        self.spin_tolerance.setEditable(True)
        self.spin_tolerance.setFixedWidth(100)
        self.spin_tolerance.setCurrentText("0.01")
        key_row.addWidget(self.spin_tolerance)
        
        key_row.addStretch()
        config_layout.addLayout(key_row)

        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Group A Column", "Group B Column", "Match Status"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        config_layout.addWidget(self.mapping_table)
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 3. Exec
        exec_group = QFrame()
        exec_layout = QVBoxLayout(exec_group)
        self.progress_label = QLabel("Ready"); self.progress_label.hide(); self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_bar = QProgressBar(); self.progress_bar.hide(); self.progress_bar.setFixedHeight(15)
        exec_layout.addWidget(self.progress_label); exec_layout.addWidget(self.progress_bar)
        
        btn_recon_row = QHBoxLayout()
        btn_recon_row.addStretch()
        self.btn_reconcile = QPushButton("Run Full Batch Reconciliation")
        self.btn_reconcile.setFixedSize(300, 45)
        self.btn_reconcile.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #4CAF50; color: white;")
        btn_recon_row.addWidget(self.btn_reconcile)
        btn_recon_row.addStretch()
        exec_layout.addLayout(btn_recon_row)
        main_layout.addWidget(exec_group)

        # Connections
        self.btn_add_a.clicked.connect(lambda: self.select_files('a'))
        self.btn_add_b.clicked.connect(lambda: self.select_files('b'))
        self.btn_analyze.clicked.connect(self.run_analysis)
        self.btn_compare_view.clicked.connect(self.open_comparison_view)
        self.btn_reconcile.clicked.connect(self.run_reconciliation)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.btn_theme.setText("🌙" if self.is_dark_mode else "☀️")
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: 'Segoe UI'; }
                QGroupBox { border: 1px solid #3d3d3d; border-radius: 8px; margin-top: 15px; font-weight: bold; color: #2196F3; font-size: 13px; }
                QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
                QPushButton { background-color: #333333; border: 1px solid #555555; border-radius: 6px; padding: 8px; color: #e0e0e0; }
                QPushButton:hover { background-color: #444444; border: 1px solid #2196F3; }
                QListWidget, QTableWidget, QComboBox { background-color: #252526; border: 1px solid #3d3d3d; color: #e0e0e0; border-radius: 4px; }
                QHeaderView::section { background-color: #333333; color: #e0e0e0; padding: 5px; border: 1px solid #3d3d3d; }
                QProgressBar { border: 1px solid #3d3d3d; text-align: center; border-radius: 7px; background: #252526; }
                QProgressBar::chunk { background-color: #4CAF50; border-radius: 7px; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f8f9fa; color: #212529; font-family: 'Segoe UI'; }
                QGroupBox { border: 1px solid #dee2e6; border-radius: 8px; margin-top: 15px; font-weight: bold; color: #0d6efd; font-size: 13px; }
                QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; }
                QPushButton { background-color: #ffffff; border: 1px solid #ced4da; border-radius: 6px; padding: 8px; color: #212529; }
                QPushButton:hover { background-color: #e9ecef; border: 1px solid #0d6efd; }
                QListWidget, QTableWidget, QComboBox { background-color: #ffffff; border: 1px solid #ced4da; color: #212529; border-radius: 4px; }
                QHeaderView::section { background-color: #e9ecef; color: #212529; padding: 5px; border: 1px solid #ced4da; }
                QProgressBar { border: 1px solid #ced4da; text-align: center; border-radius: 7px; background: #e9ecef; }
                QProgressBar::chunk { background-color: #198754; border-radius: 7px; }
            """)

    def show_info(self):
        msg = QDialog(self)
        msg.setWindowTitle("About AI Recon Tool")
        msg.setFixedSize(500, 480)
        layout = QVBoxLayout(msg)
        layout.setContentsMargins(30, 30, 30, 30)
        
        logo_label = QLabel()
        pixmap = QPixmap("assets/logo.png")
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        info_text = QLabel(f"""
            <div style='text-align: center; font-family: Segoe UI;'>
                <h2 style='color: {"#2196F3" if self.is_dark_mode else "#0d6efd"}; margin-top: 10px;'>AI RECON TOOL</h2>
                <p style='color: {"#888" if self.is_dark_mode else "#666"};'>Professional Data Reconciliation Suite</p>
                <hr style='border: 0; border-top: 1px solid #3d3d3d;'>
                <div style='margin-top: 15px;'>
                    <b>Created By:</b><br>
                    <span style='font-size: 14px;'>Rafirose Khan Shah & Ruhi Khanna</span>
                </div>
                <div style='margin-top: 10px; color: #2196F3;'>
                    rafirosekhan@gmail.com<br>ruhikh282@gmail.com
                </div>
                <p style='margin-top: 20px; font-size: 11px; color: #888;'>Version 1.0.0 | © 2026 ASI</p>
            </div>
        """)
        info_text.setTextFormat(Qt.RichText)
        layout.addWidget(info_text)
        
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(msg.accept)
        layout.setAlignment(btn_close, Qt.AlignCenter)
        layout.addWidget(btn_close)
        msg.exec()

    def handle_user_menu(self, index):
        if self.user_menu.itemText(index) == "Logout": self.close()

    def select_files(self, group):
        files, _ = QFileDialog.getOpenFileNames(self, f"Select Group {group.upper()}", "", "Data Files (*.xlsx *.xls *.csv *.pdf)")
        if files:
            if group == 'a': self.files_a.extend(files); self.list_a.addItems([os.path.basename(f) for f in files])
            else: self.files_b.extend(files); self.list_b.addItems([os.path.basename(f) for f in files])

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
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def update_mapping_table(self, mapping: dict, cols_b: list):
        self.mapping_table.setRowCount(len(mapping))
        for row, (col_a, col_b) in enumerate(mapping.items()):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(col_a))
            cb = QComboBox(); cb.addItems(cols_b); cb.setCurrentText(col_b)
            self.mapping_table.setCellWidget(row, 1, cb)
            self.mapping_table.setItem(row, 2, QTableWidgetItem("AI Match"))

    def open_comparison_view(self):
        mapping = {}
        for r in range(self.mapping_table.rowCount()):
            mapping[self.mapping_table.item(r, 0).text()] = self.mapping_table.cellWidget(r, 1).currentText()
        view = ComparisonView(self.current_df_a, self.current_df_b, mapping, self.combo_key.currentText(), self)
        view.exec()

    def run_reconciliation(self):
        mapping = {}
        for r in range(self.mapping_table.rowCount()):
            mapping[self.mapping_table.item(r, 0).text()] = self.mapping_table.cellWidget(r, 1).currentText()
        
        try:
            tolerance = float(self.spin_tolerance.currentText())
        except ValueError:
            tolerance = 0.01
            
        self.progress_bar.show(); self.progress_label.show()
        self.worker = ReconWorker(self.coordinator, self.files_a, self.files_b, self.combo_key.currentText(), mapping, self.db, self.user_info['id'], tolerance=tolerance)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.progress_label.setText)
        self.worker.finished.connect(lambda: (self.progress_bar.hide(), self.progress_label.hide(), QMessageBox.information(self, "Done", "Batch Complete")))
        self.worker.start()

    def open_admin_portal(self):
        portal = AdminPortal(self.db); portal.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginScreen()
    if login.exec() == QDialog.Accepted:
        user_data = getattr(login, 'user_data', {"type": "guest", "id": "Guest"})
        window = ReconApp(user_info=user_data)
        window.show()
        sys.exit(app.exec())
