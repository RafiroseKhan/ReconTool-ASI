import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication, QDialog
from src.desktop.app import SplashScreen, LoginScreen, ReconApp

def main():
    app = QApplication(sys.argv)
    splash = SplashScreen()
    if splash.exec() == QDialog.Accepted:
        login = LoginScreen()
        if login.exec() == QDialog.Accepted:
            user_data = getattr(login, 'user_data', {"type": "guest", "id": "Guest"})
            window = ReconApp(user_info=user_data)
            window.show()
            sys.exit(app.exec())

if __name__ == "__main__":
    main()
