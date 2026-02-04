from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QMessageBox, QStackedWidget, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from src.core.database import DatabaseManager

class LoginScreen(QDialog):
    login_success = Signal(dict) # Signal emits user info on success

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setWindowTitle("AI Recon Tool - Secure Login")
        self.setFixedSize(400, 550)
        self.setWindowFlags(Qt.FramelessWindowHint) 
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Main Layout container
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 400, 550)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 2px solid #2196F3;
                border-radius: 15px;
            }
        """)

        self.main_layout = QVBoxLayout(self.container)
        
        # Stacked Widget to switch between Login and Register
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        
        self.init_login_ui()
        self.init_register_ui()

        # Close Button
        self.btn_close = QPushButton("×", self.container)
        self.btn_close.setGeometry(360, 10, 30, 30)
        self.btn_close.setStyleSheet("color: white; font-size: 20px; border: none; background: transparent;")
        self.btn_close.clicked.connect(self.reject)

    def init_login_ui(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(15)

        title = QLabel("Welcome Back")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: white; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Please sign in to continue")
        subtitle.setStyleSheet("color: #888; border: none;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Address")
        self.email_input.setStyleSheet(self.input_style())
        layout.addWidget(self.email_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet(self.input_style())
        layout.addWidget(self.pass_input)

        self.btn_login = QPushButton("Login")
        self.btn_login.setStyleSheet(self.button_style("#2196F3"))
        self.btn_login.clicked.connect(self.handle_email_login)
        layout.addWidget(self.btn_login)

        self.btn_google = QPushButton("Sign in with Google")
        self.btn_google.setStyleSheet(self.button_style("#ffffff", "#000000"))
        self.btn_google.clicked.connect(self.handle_google_login)
        layout.addWidget(self.btn_google)

        self.btn_switch_reg = QPushButton("Don't have an account? Create one")
        self.btn_switch_reg.setStyleSheet("color: #2196F3; border: none; background: transparent;")
        self.btn_switch_reg.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        layout.addWidget(self.btn_switch_reg)

        self.btn_guest = QPushButton("Continue as Guest")
        self.btn_guest.setStyleSheet(self.button_style("transparent", "#888"))
        self.btn_guest.setFlat(True)
        self.btn_guest.clicked.connect(self.handle_guest)
        layout.addWidget(self.btn_guest)

        self.stack.addWidget(page)

    def init_register_ui(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(15)

        title = QLabel("Create Account")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: white; border: none;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email Address")
        self.reg_email.setStyleSheet(self.input_style())
        layout.addWidget(self.reg_email)

        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText("Password")
        self.reg_pass.setEchoMode(QLineEdit.Password)
        self.reg_pass.setStyleSheet(self.input_style())
        layout.addWidget(self.reg_pass)

        self.btn_register = QPushButton("Register")
        self.btn_register.setStyleSheet(self.button_style("#4CAF50"))
        self.btn_register.clicked.connect(self.handle_registration)
        layout.addWidget(self.btn_register)

        self.btn_back = QPushButton("Back to Login")
        self.btn_back.setStyleSheet("color: #888; border: none; background: transparent;")
        self.btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(self.btn_back)

        self.stack.addWidget(page)

    def input_style(self):
        return """
            QLineEdit {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 10px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
            }
        """

    def button_style(self, bg, fg="white"):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 5px;
                padding: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.8;
                background-color: #3d3d3d;
                color: white;
            }}
        """

    def handle_email_login(self):
        email = self.email_input.text()
        password = self.pass_input.text()
        
        if self.db.verify_credentials(email, password):
            self.user_data = {"type": "email", "id": email}
            self.login_success.emit(self.user_data)
            self.accept()
        else:
            QMessageBox.warning(self, "Login Error", "Invalid Email or Password.")

    def handle_registration(self):
        email = self.reg_email.text()
        password = self.reg_pass.text()
        
        if "@" not in email or len(password) < 4:
            QMessageBox.warning(self, "Error", "Valid email and password (min 4 chars) required.")
            return
            
        success, msg = self.db.create_user(email, password)
        if success:
            QMessageBox.information(self, "Success", "Account created! You can now login.")
            self.stack.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Error", msg)

    def handle_google_login(self):
        # Simulated Google Auth Linking
        self.user_data = {"type": "google", "id": "rafirosekhan@gmail.com"}
        self.login_success.emit(self.user_data)
        self.accept()

    def handle_guest(self):
        self.user_data = {"type": "guest", "id": "Guest_Session"}
        self.login_success.emit(self.user_data)
        self.accept()
