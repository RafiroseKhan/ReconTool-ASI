from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QTabWidget, QWidget)
from PySide6.QtCore import Qt

class AdminPortal(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("System Administration & Audit Portal")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Reconciliation History
        self.history_tab = QWidget()
        self.history_layout = QVBoxLayout(self.history_tab)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["ID", "User", "Timestamp", "File A", "File B", "Status"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_layout.addWidget(self.history_table)
        self.tabs.addTab(self.history_tab, "User Activity History")
        
        # Tab 2: Audit Logs
        self.audit_tab = QWidget()
        self.audit_layout = QVBoxLayout(self.audit_tab)
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["ID", "User", "Action", "Timestamp", "Details"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.audit_layout.addWidget(self.audit_table)
        self.tabs.addTab(self.audit_tab, "Security Audit Logs")
        
        layout.addWidget(self.tabs)
        self.refresh_data()

    def refresh_data(self):
        # Load History
        history = self.db.get_all_history()
        self.history_table.setRowCount(len(history))
        for r_idx, row in enumerate(history):
            for c_idx, val in enumerate(row[:6]):
                self.history_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
        
        # Load Audit
        audit = self.db.get_all_audit()
        self.audit_table.setRowCount(len(audit))
        for r_idx, row in enumerate(audit):
            for c_idx, val in enumerate(row[:5]):
                self.audit_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
