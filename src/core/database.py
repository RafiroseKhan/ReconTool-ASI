import sqlite3
import datetime
import os

class DatabaseManager:
    """Handles persistence for user history, audit logs, and authentication."""
    def __init__(self, db_path="ai-recon-tool/data/recon_system.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # User History: Tracks recon runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    timestamp DATETIME,
                    file_a TEXT,
                    file_b TEXT,
                    status TEXT,
                    output_path TEXT
                )
            """)
            # Audit Logs: Tracks system events (Logins, Exports, Admin access)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT,
                    timestamp DATETIME,
                    details TEXT,
                    ip_address TEXT
                )
            """)
            # User Table: Handles auth and roles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    password TEXT,
                    role TEXT DEFAULT 'user'
                )
            """)
            # Ensure admins exist with passwords
            admins = [
                ('rafirosekhan@gmail.com', 'admin123', 'admin'), 
                ('ruhikh282@gmail.com', 'admin123', 'admin')
            ]
            cursor.executemany("INSERT OR IGNORE INTO users (email, password, role) VALUES (?, ?, ?)", admins)
            conn.commit()

    def log_recon(self, user_id, file_a, file_b, status, output):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO history (user_id, timestamp, file_a, file_b, status, output_path) VALUES (?, ?, ?, ?, ?, ?)",
                         (user_id, datetime.datetime.now(), file_a, file_b, status, output))

    def log_audit(self, user_id, action, details):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO audit_logs (user_id, action, timestamp, details) VALUES (?, ?, ?, ?)",
                         (user_id, action, datetime.datetime.now(), details))

    def verify_credentials(self, email, password):
        """Verifies if user exists and password matches."""
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT password FROM users WHERE email = ?", (email,)).fetchone()
            if res and res[0] == password:
                return True
            return False

    def create_user(self, email, password, role='user'):
        """Registers a new user."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", 
                             (email, password, role))
                conn.commit()
                return True, "User created successfully"
            except sqlite3.IntegrityError:
                return False, "User already exists"

    def is_admin(self, email):
        with sqlite3.connect(self.db_path) as conn:
            res = conn.execute("SELECT role FROM users WHERE email = ?", (email,)).fetchone()
            return res and res[0] == 'admin'

    def get_all_history(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM history ORDER BY timestamp DESC").fetchall()

    def get_all_audit(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC").fetchall()
