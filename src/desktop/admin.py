from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QTabWidget, QWidget, QHBoxLayout, QPushButton, QMessageBox)
from PySide6.QtCore import Qt

class AdminPortal(QDialog):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setWindowTitle("System Administration & Audit Portal")
        self.setMinimumSize(1000, 700)
        
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
        
        # Tab 2: User Management (Blocking/Unblocking)
        self.user_tab = QWidget()
        self.user_layout = QVBoxLayout(self.user_tab)
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHorizontalHeaderLabels(["Email", "Role", "Status"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_layout.addWidget(self.user_table)
        
        user_btn_layout = QHBoxLayout()
        self.btn_block = QPushButton("BLOCK USER")
        self.btn_block.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        self.btn_block.clicked.connect(lambda: self.toggle_user_status('Blocked'))
        
        self.btn_unblock = QPushButton("UNBLOCK USER")
        self.btn_unblock.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_unblock.clicked.connect(lambda: self.toggle_user_status('Active'))
        
        user_btn_layout.addWidget(self.btn_block)
        user_btn_layout.addWidget(self.btn_unblock)
        self.user_layout.addLayout(user_btn_layout)
        
        self.tabs.addTab(self.user_tab, "User Management")

        # Tab 3: Audit Logs
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

    def toggle_user_status(self, status):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a user first.")
            return
            
        email = self.user_table.item(row, 0).text()
        if self.db.is_admin(email) and status == 'Blocked':
            QMessageBox.critical(self, "Error", "Administrators cannot be blocked.")
            return
            
        if self.db.update_user_status(email, status):
            QMessageBox.information(self, "Success", f"User {email} is now {status}.")
            self.refresh_data()

    def refresh_data(self):
        # Load History
        history = self.db.get_all_history()
        self.history_table.setRowCount(len(history))
        for r_idx, row in enumerate(history):
            for c_idx, val in enumerate(row[:6]):
                self.history_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
        
        # Load Users
        users = self.db.get_all_users()
        self.user_table.setRowCount(len(users))
        for r_idx, row in enumerate(users):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                if c_idx == 2: # Status column
                    if val == 'Blocked':
                        item.setForeground(Qt.red)
                    else:
                        item.setForeground(Qt.green)
                self.user_table.setItem(r_idx, c_idx, item)

        # Load Audit
        audit = self.db.get_all_audit()
        self.audit_table.setRowCount(len(audit))
        for r_idx, row in enumerate(audit):
            for c_idx, val in enumerate(row[:5]):
                self.audit_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
