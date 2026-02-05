from src.core.coordinator import ReconCoordinator
from src.desktop.login import LoginScreen
from src.desktop.admin import AdminPortal
from src.core.database import DatabaseManager
import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QComboBox, QGroupBox, QListWidget, QDialog, QProgressBar,
                             QTabWidget, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QPixmap

class ComparisonView(QDialog):
    def __init__(self, df_a, df_b, mapping, key_col=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Side-by-Side Comparison (Beyond Compare Style)")
        self.setMinimumSize(1200, 700)
        layout = QVBoxLayout(self)
        
        # Comparison logic: Align B to A based on mapping
        inv_mapping = {v: k for k, v in mapping.items()}
        df_b_aligned = df_b.rename(columns=inv_mapping)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Table A
        self.table_a = QTableWidget()
        # Table B
        self.table_b = QTableWidget()
        
        self.populate_and_compare(df_a, df_b_aligned, mapping, key_col)
        
        # Synchronize Scrolling
        self.table_a.verticalScrollBar().valueChanged.connect(
            self.table_b.verticalScrollBar().setValue
        )
        self.table_b.verticalScrollBar().valueChanged.connect(
            self.table_a.verticalScrollBar().setValue
        )
        
        splitter.addWidget(self.table_a)
        splitter.addWidget(self.table_b)
        layout.addWidget(splitter)

    def populate_and_compare(self, df_a, df_b, mapping, key_col):
        rows = max(len(df_a), len(df_b))
        cols = len(df_a.columns)
        
        for table in [self.table_a, self.table_b]:
            table.setRowCount(rows)
            table.setColumnCount(cols)
            table.setHorizontalHeaderLabels(df_a.columns)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # Indexing for fast lookup
        if key_col and key_col in df_a.columns and key_col in df_b.columns:
            df_b_idx = df_b.set_index(key_col)
        else:
            df_b_idx = df_b # Fallback to index matching

        for i in range(len(df_a)):
            row_a = df_a.iloc[i]
            key_val = row_a[key_col] if key_col else i
            
            try:
                if key_col:
                    row_b = df_b_idx.loc[key_val]
                    # Handle multiple matches
                    if isinstance(row_b, pd.DataFrame): row_b = row_b.iloc[0]
                else:
                    row_b = df_b.iloc[i]
                found_b = True
            except:
                found_b = False

            for j, col in enumerate(df_a.columns):
                val_a = str(row_a[col])
                item_a = QTableWidgetItem(val_a)
                
                if not found_b:
                    # Red for no match in B
                    item_a.setBackground(QColor("#5a1d1d")) # Dark Red
                    self.table_a.setItem(i, j, item_a)
                    self.table_b.setItem(i, j, QTableWidgetItem(""))
                else:
                    val_b = str(row_b[col]) if col in row_b else ""
                    item_b = QTableWidgetItem(val_b)
                    
                    if val_a == val_b:
                        # Green for match
                        bg = QColor("#1e3a1e") # Dark Green
                    else:
                        # Yellow for partial (mismatching content)
                        bg = QColor("#5a5a1d") # Dark Yellow
                    
                    item_a.setBackground(bg)
                    item_b.setBackground(bg)
                    self.table_a.setItem(i, j, item_a)
                    self.table_b.setItem(i, j, item_b)

class ReconWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, coordinator, files_a, files_b, key_col, mapping, db, user_id):
        super().__init__()
        self.coordinator = coordinator
        self.files_a = files_a
        self.files_b = files_b
        self.key_col = key_col
        self.mapping = mapping
        self.db = db
        self.user_id = user_id

    def run(self):
        results = []
        total = len(self.files_a)
        try:
            for i, file_a in enumerate(self.files_a):
                if i < len(self.files_b):
                    file_b = self.files_b[i]
                    self.status.emit(f"Processing: {os.path.basename(file_a)} vs {os.path.basename(file_b)}...")
                    output_path = f"Recon_Report_{os.path.basename(file_a)}.xlsx"
                    self.coordinator.run_full_recon(file_a, file_b, key_col=self.key_col, mapping=self.mapping, output_path=output_path)
                    self.db.log_recon(self.user_id, file_a, file_b, "SUCCESS", output_path)
                    results.append(output_path)
                progress_val = int(((i + 1) / total) * 100)
                self.progress.emit(progress_val)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class ReconApp(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info or {"type": "guest", "id": "Guest"}
        self.db = DatabaseManager()
        self.coordinator = ReconCoordinator()
        self.is_dark_mode = True
        
        self.files_a = []
        self.files_b = []
        self.setWindowTitle("AI Recon Tool - Professional Suite")
        self.setMinimumSize(1100, 800)
        
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar
        top_bar = QHBoxLayout()
        
        # Logo placeholder or I button
        self.btn_info = QPushButton("ℹ")
        self.btn_info.setFixedSize(35, 35)
        self.btn_info.clicked.connect(self.show_info)
        top_bar.addWidget(self.btn_info)

        if self.db.is_admin(self.user_info['id']):
            self.btn_admin = QPushButton("🛡️ Admin")
            self.btn_admin.clicked.connect(self.open_admin_portal)
            top_bar.addWidget(self.btn_admin)
        
        top_bar.addStretch()

        # Settings Section (Theme Toggle)
        self.btn_theme = QPushButton("🌙" if self.is_dark_mode else "☀️")
        self.btn_theme.setFixedSize(40, 35)
        self.btn_theme.setToolTip("Toggle Light/Dark Mode")
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
        files_group = QGroupBox("1. Select Batches of Files")
        files_layout = QHBoxLayout()
        vbox_a = QVBoxLayout(); self.list_a = QListWidget(); self.btn_add_a = QPushButton("Add Group A")
        vbox_a.addWidget(self.btn_add_a); vbox_a.addWidget(self.list_a)
        vbox_b = QVBoxLayout(); self.list_b = QListWidget(); self.btn_add_b = QPushButton("Add Group B")
        vbox_b.addWidget(self.btn_add_b); vbox_b.addWidget(self.list_b)
        files_layout.addLayout(vbox_a); files_layout.addLayout(vbox_b)
        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # 2. Config
        config_group = QGroupBox("2. Review & Configure Analysis")
        config_layout = QVBoxLayout()
        
        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("Analyze Files & Suggest Mapping")
        self.btn_compare_view = QPushButton("🔍") # Icon-style
        self.btn_compare_view.setFixedSize(50, 40)
        self.btn_compare_view.setToolTip("Side-by-Side Comparison")
        self.btn_compare_view.setEnabled(False)
        btn_row.addWidget(self.btn_analyze)
        btn_row.addWidget(self.btn_compare_view)
        config_layout.addLayout(btn_row)

        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Primary Key:"))
        self.combo_key = QComboBox()
        key_layout.addWidget(self.combo_key)
        config_layout.addLayout(key_layout)

        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Group A Column", "Group B Column", "Match Status"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        config_layout.addWidget(self.mapping_table)
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 3. Exec
        exec_layout = QVBoxLayout()
        self.progress_label = QLabel("Ready"); self.progress_label.hide(); exec_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar(); self.progress_bar.hide(); exec_layout.addWidget(self.progress_bar)
        self.btn_reconcile = QPushButton("Run Full Batch Reconciliation")
        exec_layout.addWidget(self.btn_reconcile)
        main_layout.addLayout(exec_layout)

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
                QGroupBox { border: 2px solid #3d3d3d; border-radius: 8px; margin-top: 20px; font-weight: bold; color: #2196F3; }
                QPushButton { background-color: #333333; border: 1px solid #555555; border-radius: 4px; padding: 8px; color: #e0e0e0; }
                QPushButton:hover { background-color: #444444; border: 1px solid #2196F3; }
                QListWidget, QTableWidget, QComboBox { background-color: #252526; border: 1px solid #3d3d3d; color: #e0e0e0; }
                QHeaderView::section { background-color: #333333; color: #e0e0e0; padding: 5px; border: 1px solid #3d3d3d; }
                QProgressBar { border: 2px solid #3d3d3d; text-align: center; }
                QProgressBar::chunk { background-color: #4CAF50; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f5f5f5; color: #333333; font-family: 'Segoe UI'; }
                QGroupBox { border: 2px solid #cccccc; border-radius: 8px; margin-top: 20px; font-weight: bold; color: #1976D2; }
                QPushButton { background-color: #e0e0e0; border: 1px solid #999999; border-radius: 4px; padding: 8px; color: #333333; }
                QPushButton:hover { background-color: #d0d0d0; border: 1px solid #1976D2; }
                QListWidget, QTableWidget, QComboBox { background-color: #ffffff; border: 1px solid #cccccc; color: #333333; }
                QHeaderView::section { background-color: #eeeeee; color: #333333; padding: 5px; border: 1px solid #cccccc; }
                QProgressBar { border: 2px solid #cccccc; text-align: center; }
                QProgressBar::chunk { background-color: #4CAF50; }
            """)

    def show_info(self):
        msg = QDialog(self)
        msg.setWindowTitle("About Application")
        msg.setFixedSize(500, 450)
        layout = QVBoxLayout(msg)
        
        # App Logo
        logo_label = QLabel()
        pixmap = QPixmap("assets/logo.png")
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        info_text = QLabel("""
            <div style='text-align: center;'>
                <h2 style='color: #2196F3;'>AI Recon Tool</h2>
                <p><b>Version 1.0.0</b></p>
                <p>Multi-format AI Reconciliation Engine</p>
                <hr>
                <p><b>Created By:</b></p>
                <p>Rafirose Khan Shah<br>Ruhi Khanna</p>
                <p><small>rafirosekhan@gmail.com | ruhikh282@gmail.com</small></p>
            </div>
        """)
        info_text.setTextFormat(Qt.RichText)
        layout.addWidget(info_text)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(msg.accept)
        layout.addWidget(btn_close)
        msg.exec()

    def handle_user_menu(self, index):
        if self.user_menu.itemText(index) == "Logout":
            self.close()

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
        self.progress_bar.show(); self.progress_label.show()
        self.worker = ReconWorker(self.coordinator, self.files_a, self.files_b, self.combo_key.currentText(), mapping, self.db, self.user_info['id'])
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
