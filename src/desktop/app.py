from src.core.coordinator import ReconCoordinator
import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                             QComboBox, QGroupBox, QListWidget)
from PySide6.QtCore import Qt

class ReconApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.coordinator = ReconCoordinator()
        self.files_a = []
        self.files_b = []
        self.setWindowTitle("AI Recon Tool - Professional Suite")
        self.setMinimumSize(1000, 750)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

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
        exec_layout = QHBoxLayout()
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
            self.update_mapping_table(mapping)
            
            QMessageBox.information(self, "Analysis Complete", "AI has analyzed the file structure.\n\n1. Select the correct Primary Key from the dropdown.\n2. Review/Edit the column mappings in the table.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")

    def update_mapping_table(self, mapping: dict):
        self.mapping_table.setRowCount(len(mapping))
        for row, (col_a, col_b) in enumerate(mapping.items()):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(col_a))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(col_b))
            status_item = QTableWidgetItem("AI Matched")
            status_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled) # Make status read-only
            self.mapping_table.setItem(row, 2, status_item)

    def run_reconciliation(self):
        if not self.files_a or not self.files_b:
            QMessageBox.warning(self, "Error", "No files selected.")
            return
        
        key_col = self.combo_key.currentText()
        if not key_col:
            QMessageBox.warning(self, "Error", "Please run analysis and select a primary key first.")
            return

        try:
            # Get current mapping from editable table
            mapping = {}
            for row in range(self.mapping_table.rowCount()):
                col_a = self.mapping_table.item(row, 0).text()
                col_b = self.mapping_table.item(row, 1).text()
                mapping[col_a] = col_b

            # For Phase 1 Batch, we process the first pair
            # (Future update: loop through all files for full batch merge)
            output_path = "batch_recon_output.xlsx"
            self.coordinator.run_full_recon(self.files_a[0], self.files_b[0], key_col=key_col, output_path=output_path)
            
            QMessageBox.information(self, "Success", f"Reconciliation Complete!\n\nKey Used: {key_col}\nOutput: {os.path.abspath(output_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Reconciliation failed: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReconApp()
    window.show()
    sys.exit(app.exec())
