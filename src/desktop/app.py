import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

class ReconApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Recon Tool - Desktop (Phase 1)")
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

    def select_file_a(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Group A", "", "Excel/CSV/PDF (*.xlsx *.xls *.csv *.pdf)")
        if path:
            self.lbl_a.setText(f"A: {path}")

    def select_file_b(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Group B", "", "Excel/CSV/PDF (*.xlsx *.xls *.csv *.pdf)")
        if path:
            self.lbl_b.setText(f"B: {path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReconApp()
    window.show()
    sys.exit(app.exec())
