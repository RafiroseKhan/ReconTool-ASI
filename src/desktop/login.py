import sys
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

class LoginScreen(QDialog):
    login_success = Signal(dict) # Signal emits user info on success

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Recon Tool - Secure Login")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.FramelessWindowHint) # Clean borderless look
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Main Layout container for styling
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 400, 500)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 2px solid #2196F3;
                border-radius: 15px;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(15)

        # Header
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

        # Email Input
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email Address")
        self.email_input.setStyleSheet(self.input_style())
        layout.addWidget(self.email_input)

        # Password Input
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setStyleSheet(self.input_style())
        layout.addWidget(self.pass_input)

        # Login Button
        self.btn_login = QPushButton("Login with Email")
        self.btn_login.setStyleSheet(self.button_style("#2196F3"))
        self.btn_login.clicked.connect(self.handle_email_login)
        layout.addWidget(self.btn_login)

        # Google Login
        self.btn_google = QPushButton("Sign in with Google")
        self.btn_google.setStyleSheet(self.button_style("#ffffff", "#000000"))
        self.btn_google.clicked.connect(self.handle_google_login)
        layout.addWidget(self.btn_google)

        # Guest Option
        self.btn_guest = QPushButton("Continue as Guest")
        self.btn_guest.setStyleSheet(self.button_style("transparent", "#888"))
        self.btn_guest.setFlat(True)
        self.btn_guest.clicked.connect(self.handle_guest)
        layout.addWidget(self.btn_guest)

        layout.addStretch()

        # Close Button
        self.btn_close = QPushButton("×", self.container)
        self.btn_close.setGeometry(360, 10, 30, 30)
        self.btn_close.setStyleSheet("color: white; font-size: 20px; border: none;")
        self.btn_close.clicked.connect(self.reject)

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
        if "@" in email:
            self.user_data = {"type": "email", "id": email}
            self.login_success.emit(self.user_data)
            self.accept()
        else:
            QMessageBox.warning(self, "Login Error", "Please enter a valid email address.")

    def handle_google_login(self):
        self.user_data = {"type": "google", "id": "google_user@gmail.com"}
        self.login_success.emit(self.user_data)
        self.accept()

    def handle_guest(self):
        self.user_data = {"type": "guest", "id": "Guest_Session"}
        self.login_success.emit(self.user_data)
        self.accept()
