from src.core.coordinator import ReconCoordinator
from src.desktop.login import LoginScreen
from src.desktop.admin import AdminPortal
from src.core.database import DatabaseManager
import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QComboBox, QGroupBox, QListWidget, QDialog, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal

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
                # Simple matching by index for this batch mode
                if i < len(self.files_b):
                    file_b = self.files_b[i]
                    self.status.emit(f"Processing: {os.path.basename(file_a)} vs {os.path.basename(file_b)}...")
                    
                    output_path = f"Recon_Report_{os.path.basename(file_a)}.xlsx"
                    self.coordinator.run_full_recon(
                        file_a, 
                        file_b, 
                        key_col=self.key_col, 
                        mapping=self.mapping, 
                        output_path=output_path
                    )
                    
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
        
        # Log session start
        self.db.log_audit(self.user_info['id'], "SESSION_START", f"User logged in via {self.user_info['type']}")
        
        self.files_a = []
        self.files_b = []
        self.setWindowTitle("AI Recon Tool - Professional Suite")
        self.setMinimumSize(1100, 800)
        
        # Apply Dark Theme
        self.apply_dark_theme()

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar for Admin & Profile
        top_bar = QHBoxLayout()
        if self.db.is_admin(self.user_info['id']):
            self.btn_admin = QPushButton("🛡️ Admin Portal")
            self.btn_admin.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 5px 15px;")
            self.btn_admin.clicked.connect(self.open_admin_portal)
            top_bar.addWidget(self.btn_admin)
        
        top_bar.addStretch()
        
        # Info Button
        self.btn_info = QPushButton("ℹ")
        self.btn_info.setFixedSize(30, 30)
        self.btn_info.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border-radius: 15px;
                color: #2196F3;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #2196F3;
            }
            QPushButton:hover {
                background-color: #2196F3;
                color: white;
            }
        """)
        self.btn_info.clicked.connect(self.show_info)
        top_bar.addWidget(self.btn_info)

        # User Profile Display with Logout Dropdown
        self.user_menu = QComboBox()
        self.user_menu.addItem(f"👤 {self.user_info['id']}")
        self.user_menu.addItem("Logout")
        self.user_menu.setFixedWidth(200)
        self.user_menu.activated.connect(self.handle_user_menu)
        top_bar.addWidget(self.user_menu)
        
        main_layout.addLayout(top_bar)

        # 1. File Management Section
        files_group = QGroupBox("1. Select Batches of Files")
        files_layout = QHBoxLayout()
        
        # Group A
        vbox_a = QVBoxLayout()
        self.btn_add_a = QPushButton("Add Files to Group A")
        self.btn_clear_a = QPushButton("Clear A")
        self.list_a = QListWidget()
        vbox_a.addWidget(self.btn_add_a)
        vbox_a.addWidget(self.list_a)
        vbox_a.addWidget(self.btn_clear_a)
        
        # Group B
        vbox_b = QVBoxLayout()
        self.btn_add_b = QPushButton("Add Files to Group B")
        self.btn_clear_b = QPushButton("Clear B")
        self.list_b = QListWidget()
        vbox_b.addWidget(self.btn_add_b)
        vbox_b.addWidget(self.list_b)
        vbox_b.addWidget(self.btn_clear_b)
        
        files_layout.addLayout(vbox_a)
        files_layout.addLayout(vbox_b)
        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # 2. Configuration Section
        config_group = QGroupBox("2. Review & Configure Analysis")
        config_layout = QVBoxLayout()
        
        # Analyze Button
        self.btn_analyze = QPushButton("Analyze Files & Suggest Mapping")
        self.btn_analyze.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        config_layout.addWidget(self.btn_analyze)

        # Key Selection
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Primary Key (Unique ID):"))
        self.combo_key = QComboBox()
        self.combo_key.setToolTip("Select the column that uniquely identifies each row (e.g., Trade ID)")
        key_layout.addWidget(self.combo_key)
        config_layout.addLayout(key_layout)

        # Mapping Table
        config_layout.addWidget(QLabel("AI Column Mapping Suggestions (Editable):"))
        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Group A Column", "Group B Column", "Match Status"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        config_layout.addWidget(self.mapping_table)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 3. Execution Section
        exec_layout = QVBoxLayout()
        
        self.progress_label = QLabel("Ready")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.hide()
        exec_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.progress_bar.hide()
        exec_layout.addWidget(self.progress_bar)

        self.btn_reconcile = QPushButton("Run Full Batch Reconciliation")
        self.btn_reconcile.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 15px; font-size: 14px;")
        exec_layout.addWidget(self.btn_reconcile)
        main_layout.addLayout(exec_layout)

        # Connect Signals
        self.btn_add_a.clicked.connect(lambda: self.select_files('a'))
        self.btn_add_b.clicked.connect(lambda: self.select_files('b'))
        self.btn_clear_a.clicked.connect(lambda: self.clear_files('a'))
        self.btn_clear_b.clicked.connect(lambda: self.clear_files('b'))
        self.btn_analyze.clicked.connect(self.run_analysis)
        self.btn_reconcile.clicked.connect(self.run_reconciliation)

    def open_admin_portal(self):
        portal = AdminPortal(self.db)
        portal.exec()

    def show_info(self):
        info_text = """
        <div style='font-family: Segoe UI, Arial;'>
            <h2 style='color: #2196F3;'>AI Recon Tool - Professional Suite</h2>
            <p><b>Version:</b> 1.0.0</p>
            <p>A multi-format reconciliation engine supporting Excel, CSV, and Scanned PDFs with AI-powered column mapping.</p>
            <hr style='border: 0; border-top: 1px solid #3d3d3d;'>
            <p style='font-size: 14px;'><b>Created By:</b></p>
            <ul style='list-style: none; padding-left: 0;'>
                <li style='margin-bottom: 10px;'>
                    <b>Rafirose Khan Shah</b><br>
                    <a href='mailto:rafirosekhan@gmail.com' style='color: #2196F3; text-decoration: none;'>rafirosekhan@gmail.com</a>
                </li>
                <li>
                    <b>Ruhi Khanna</b><br>
                    <a href='mailto:ruhikh282@gmail.com' style='color: #2196F3; text-decoration: none;'>ruhikh282@gmail.com</a>
                </li>
            </ul>
            <p style='font-style: italic; color: #888; margin-top: 20px;'>Building the future of financial data reconciliation.</p>
        </div>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("About Application")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info_text)
        msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
            }
            QLabel {
                min-width: 450px;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #333333;
                color: #e0e0e0;
                padding: 5px 15px;
                border: 1px solid #555;
            }
        """)
        msg.exec()

    def handle_user_menu(self, index):
        if self.user_menu.itemText(index) == "Logout":
            self.db.log_audit(self.user_info['id'], "LOGOUT", "User logged out")
            self.is_logging_out = True
            self.close() 

    def select_files(self, group):
        files, _ = QFileDialog.getOpenFileNames(self, f"Select Files for Group {group.upper()}", "", "Data Files (*.xlsx *.xls *.csv *.pdf)")
        if files:
            if group == 'a':
                self.files_a.extend(files)
                self.list_a.addItems([os.path.basename(f) for f in files])
            else:
                self.files_b.extend(files)
                self.list_b.addItems([os.path.basename(f) for f in files])

    def clear_files(self, group):
        if group == 'a':
            self.files_a = []
            self.list_a.clear()
        else:
            self.files_b = []
            self.list_b.clear()

    def run_analysis(self):
        if not self.files_a or not self.files_b:
            QMessageBox.warning(self, "Error", "Please add files to both groups first.")
            return
        
        try:
            # Analyze based on the first file of the batch
            df_a = self.coordinator.get_handler(self.files_a[0]).read(self.files_a[0])
            df_b = self.coordinator.get_handler(self.files_b[0]).read(self.files_b[0])
            
            # Populate Key Dropdown
            self.combo_key.clear()
            self.combo_key.addItems(df_a.columns.tolist())
            suggested_key = self.coordinator.mapper.suggest_primary_key(df_a)
            self.combo_key.setCurrentText(suggested_key)
            
            # Suggest Mappings
            mapping = self.coordinator.mapper.suggest_mapping(df_a.columns.tolist(), df_b.columns.tolist())
            self.update_mapping_table(mapping, df_b.columns.tolist())
            
            QMessageBox.information(self, "Analysis Complete", "AI has analyzed the file structure.\n\n1. Select the correct Primary Key from the dropdown.\n2. Review/Edit the column mappings using the dropdowns.")
            self.db.log_audit(self.user_info['id'], "FILE_ANALYSIS", f"Analyzed {os.path.basename(self.files_a[0])}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")

    def update_mapping_table(self, mapping: dict, cols_b: list):
        self.mapping_table.setRowCount(len(mapping))
        for row, (col_a, col_b) in enumerate(mapping.items()):
            # Column A (Read Only)
            item_a = QTableWidgetItem(col_a)
            item_a.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.mapping_table.setItem(row, 0, item_a)
            
            # Column B (Dropdown for selection)
            combo_b = QComboBox()
            combo_b.addItems(cols_b)
            if col_b in cols_b:
                combo_b.setCurrentText(col_b)
            self.mapping_table.setCellWidget(row, 1, combo_b)
            
            # Match Status
            status_item = QTableWidgetItem("AI Suggestion")
            status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.mapping_table.setItem(row, 2, status_item)

    def run_reconciliation(self):
        if not self.files_a or not self.files_b:
            QMessageBox.warning(self, "Error", "No files selected.")
            return
        
        key_col = self.combo_key.currentText()
        if not key_col:
            QMessageBox.warning(self, "Error", "Please run analysis and select a primary key first.")
            return

        # Get current mapping from dropdown widgets in the table
        mapping = {}
        for row in range(self.mapping_table.rowCount()):
            item_a = self.mapping_table.item(row, 0)
            combo_b = self.mapping_table.cellWidget(row, 1)
            if item_a and combo_b:
                mapping[item_a.text()] = combo_b.currentText()

        # UI Setup for Progress
        self.btn_reconcile.setEnabled(False)
        self.btn_analyze.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.show()

        # Initialize Worker Thread
        self.worker = ReconWorker(
            self.coordinator, 
            self.files_a, 
            self.files_b, 
            key_col, 
            mapping, 
            self.db, 
            self.user_info['id']
        )
        
        # Connect signals
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.progress_label.setText)
        self.worker.error.connect(self.handle_recon_error)
        self.worker.finished.connect(self.handle_recon_finished)
        
        # Start
        self.worker.start()

    def handle_recon_error(self, error_msg):
        self.reset_ui_after_run()
        QMessageBox.critical(self, "Error", f"Reconciliation failed: {error_msg}")

    def handle_recon_finished(self, results):
        self.reset_ui_after_run()
        self.db.log_audit(self.user_info['id'], "RECON_BATCH_FINISH", f"Processed {len(results)} pairs")
        QMessageBox.information(self, "Success", f"Batch Reconciliation Complete!\n\nProcessed {len(results)} pairs.\nCheck the project folder for the output files.")

    def reset_ui_after_run(self):
        self.btn_reconcile.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.progress_bar.hide()
        self.progress_label.hide()
        self.progress_label.setText("Ready")

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial;
            }
            QGroupBox {
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 20px;
                font-weight: bold;
                color: #2196F3;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #444444;
                border: 1px solid #2196F3;
            }
            QListWidget, QTableWidget, QComboBox {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                color: #e0e0e0;
                gridline-color: #3d3d3d;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #e0e0e0;
                padding: 5px;
                border: 1px solid #3d3d3d;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                selection-background-color: #2196F3;
            }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    while True:
        login = LoginScreen()
        if login.exec() == QDialog.Accepted:
            user_data = getattr(login, 'user_data', {"type": "guest", "id": "Guest"})
            window = ReconApp(user_info=user_data)
            window.show()
            app.exec() # Wait for window to close
            
            # Check if we are logging out or exiting
            if not getattr(window, 'is_logging_out', False):
                break
        else:
            break
    sys.exit()
