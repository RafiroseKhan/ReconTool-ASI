from src.core.coordinator import ReconCoordinator
import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)

class ReconApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.coordinator = ReconCoordinator()
        self.path_a = None
        self.path_b = None
        self.setWindowTitle("AI Recon Tool - Desktop (Phase 1)")
        # ... [rest of init remains similar]
        self.setMinimumSize(800, 600)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # File Selection Area
        file_layout = QHBoxLayout()
        self.btn_file_a = QPushButton("Select Group A (Excel/CSV/PDF)")
        self.btn_file_b = QPushButton("Select Group B (Excel/CSV/PDF)")
        file_layout.addWidget(self.btn_file_a)
        file_layout.addWidget(self.btn_file_b)
        layout.addLayout(file_layout)

        # Labels for selected files
        self.lbl_a = QLabel("No file selected")
        self.lbl_b = QLabel("No file selected")
        layout.addWidget(self.lbl_a)
        layout.addWidget(self.lbl_b)

        # Mapping Table (AI Suggestions will appear here)
        layout.addWidget(QLabel("AI Column Mapping Suggestions:"))
        self.mapping_table = QTableWidget(0, 3)
        self.mapping_table.setHorizontalHeaderLabels(["Group A Column", "Group B Column", "Confidence"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.mapping_table)

        # Action Buttons
        self.btn_reconcile = QPushButton("Run Reconciliation")
        self.btn_reconcile.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        layout.addWidget(self.btn_reconcile)

        # Connect Signals
        self.btn_file_a.clicked.connect(self.select_file_a)
        self.btn_file_b.clicked.connect(self.select_file_b)
        self.btn_reconcile.clicked.connect(self.run_reconciliation)

    def select_file_a(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Group A", "", "Excel/CSV/PDF (*.xlsx *.xls *.csv *.pdf)")
        if path:
            self.path_a = path
            self.lbl_a.setText(f"A: {path}")

    def select_file_b(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Group B", "", "Excel/CSV/PDF (*.xlsx *.xls *.csv *.pdf)")
        if path:
            self.path_b = path
            self.lbl_b.setText(f"B: {path}")

    def update_mapping_table(self, mapping: dict):
        """Updates the UI table with AI-suggested column mappings."""
        self.mapping_table.setRowCount(len(mapping))
        for row, (col_a, col_b) in enumerate(mapping.items()):
            self.mapping_table.setItem(row, 0, QTableWidgetItem(col_a))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(col_b))
            self.mapping_table.setItem(row, 2, QTableWidgetItem("High (AI)"))

    def run_reconciliation(self):
        if not self.path_a or not self.path_b:
            QMessageBox.warning(self, "Error", "Please select both files.")
            return
            
        try:
            # 1. Preview Mapping first (Internal logic)
            df_a = self.coordinator.get_handler(self.path_a).read(self.path_a)
            df_b = self.coordinator.get_handler(self.path_b).read(self.path_b)
            mapping = self.coordinator.mapper.suggest_mapping(df_a.columns.tolist(), df_b.columns.tolist())
            self.update_mapping_table(mapping)

            # 2. Run the actual process
            output_path = "recon_output.xlsx"
            self.coordinator.run_full_recon(self.path_a, self.path_b, key_col="ID", output_path=output_path)
            QMessageBox.information(self, "Success", f"Report generated: {os.path.abspath(output_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReconApp()
    window.show()
    sys.exit(app.exec())
