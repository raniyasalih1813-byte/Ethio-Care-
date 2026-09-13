"""
ETHIOPIAN EMERGENCY MANAGEMENT AND RESPONSE SYSTEM
===================================================

A complete desktop emergency reporting system built with:
    - Python 3
    - Tkinter / ttk
    - SQLite
    - Tkinter-only image support (no third-party packages required)

FEATURES
--------
1. User registration and user login.
2. Separate administrator login.
3. Administrator password is 102030.
4. The administrator password is NEVER displayed on the public/front page.
5. Emergency help information.
6. Ethiopian emergency contact numbers.
7. Emergency reporting form.
8. Strong validation with clear "INVALID" messages.
9. Administrator can view, search, filter and update reports.
10. Administrator can change report status.
11. Real-world accident/emergency photographs from Wikimedia Commons
    can be downloaded into a local gallery when internet is available. The app does not require Pillow or any other package.
12. The application still starts if the photo download fails.
13. SQLite database stores users and emergency reports.
14. Passwords are stored as hashes rather than plain text.
15. User can view their own submitted reports and status.
16. Admin can export reports to CSV.
17. Attractive dark emergency-themed interface.
18. Responsive scrolling panels and reusable widgets.
19. Confirmation dialogs for destructive actions.
20. Error handling around database and network operations.

IMPORTANT
---------
This is an educational emergency-management prototype. It does not replace
real emergency services. For a life-threatening emergency, call the appropriate
local emergency service immediately.

Commonly published Ethiopia contacts used in this prototype:
    General Emergency: 911
    Police: 991
    Ambulance / Ethiopian Red Cross (Addis Ababa): 907
    Fire and Rescue: 939
    Traffic Police (Addis Ababa): 945

Numbers can vary by region and can change. Verify local contacts where you are.
"""

# ============================================================
# 001 - STANDARD LIBRARY IMPORTS
# ============================================================

import csv
import hashlib
import os
import re
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    BOTTOM,
    END,
    LEFT,
    RIGHT,
    TOP,
    X,
    Y,
    CENTER,
    DISABLED,
    NORMAL,
    HORIZONTAL,
    VERTICAL,
    ANCHOR,
)
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ============================================================
# 002 - IMAGE SUPPORT (TKINTER ONLY - NO EXTRA INSTALLS)
# ============================================================
# Tkinter is included with standard Python installations.  This version
# deliberately does not require Pillow or any third-party package.
# PNG/GIF images are displayed directly by Tkinter.
PIL_AVAILABLE = False


# ============================================================
# 003 - APPLICATION PATHS
# ============================================================

APP_TITLE = "Ethiopian Emergency Management & Response System"
APP_VERSION = "2.0"
BASE_DIR = Path(__file__).resolve().parent
# Keep application data in the user-writable home directory so the program
# also works when the .py file is launched from a protected/read-only folder.
DATA_DIR = Path.home() / "EthiopianEmergencySystem"
PHOTO_DIR = DATA_DIR / "emergency_photos"
EXPORT_DIR = DATA_DIR / "exports"
DB_FILE = DATA_DIR / "emergency_system.db"


# ============================================================
# 004 - DATABASE SETTINGS
# ============================================================

DATABASE_TIMEOUT = 10
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "102030"


# ============================================================
# 005 - STATUS VALUES
# ============================================================

STATUS_PENDING = "Pending"
STATUS_REVIEWING = "Under Review"
STATUS_DISPATCHED = "Dispatched"
STATUS_IN_PROGRESS = "In Progress"
STATUS_RESOLVED = "Resolved"
STATUS_CANCELLED = "Cancelled"

STATUS_VALUES = [
    STATUS_PENDING,
    STATUS_REVIEWING,
    STATUS_DISPATCHED,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
    STATUS_CANCELLED,
]


# ============================================================
# 006 - EMERGENCY TYPES
# ============================================================

EMERGENCY_TYPES = [
    "Fire",
    "Road Accident",
    "Medical Emergency",
    "Crime / Security",
    "Building Collapse",
    "Flood",
    "Rescue",
    "Gas Leak",
    "Electrical Emergency",
    "Missing Person",
    "Other",
]


# ============================================================
# 007 - ETHIOPIAN EMERGENCY CONTACTS
# ============================================================

EMERGENCY_CONTACTS = [
    {
        "service": "General Emergency",
        "number": "911",
        "description": "General emergency assistance.",
        "location": "Ethiopia",
    },
    {
        "service": "Police",
        "number": "991",
        "description": "Police emergency assistance.",
        "location": "Ethiopia / commonly published",
    },
    {
        "service": "Ambulance",
        "number": "907",
        "description": "Ethiopian Red Cross ambulance service.",
        "location": "Addis Ababa",
    },
    {
        "service": "Fire & Rescue",
        "number": "939",
        "description": "Fire and rescue emergency service.",
        "location": "Addis Ababa / commonly published",
    },
    {
        "service": "Traffic Police",
        "number": "945",
        "description": "Traffic-related emergency assistance.",
        "location": "Addis Ababa",
    },
    {
        "service": "Federal Police",
        "number": "916",
        "description": "Federal Police contact listed by official sources.",
        "location": "Ethiopia",
    },
]


# ============================================================
# 008 - HELP INFORMATION
# ============================================================

HELP_INFORMATION = [
    (
        "FIRE",
        "Leave the building if it is unsafe. Do not use elevators. "
        "If smoke is present, stay low and move toward a safe exit. "
        "Call fire and rescue immediately."
    ),
    (
        "ROAD ACCIDENT",
        "Move to a safe place if possible. Warn approaching traffic. "
        "Do not move seriously injured people unless remaining there "
        "creates immediate danger. Call emergency services."
    ),
    (
        "MEDICAL EMERGENCY",
        "Call an ambulance or emergency service. Give the exact location, "
        "nearby landmark and number of people needing help. Follow the "
        "dispatcher instructions."
    ),
    (
        "CRIME / SECURITY",
        "Move away from immediate danger. Do not confront a dangerous person. "
        "Call police and provide location and a short description."
    ),
    (
        "BUILDING COLLAPSE",
        "Keep away from unstable structures and falling debris. Do not enter "
        "a damaged building unless instructed by trained responders."
    ),
    (
        "FLOOD",
        "Avoid fast-moving water and flooded electrical areas. Move to higher "
        "ground where safe. Never drive through unknown floodwater."
    ),
    (
        "GAS LEAK",
        "Do not create flames or sparks. Leave the area and contact emergency "
        "services from a safe location."
    ),
    (
        "ELECTRICAL EMERGENCY",
        "Do not touch fallen power lines or electrical equipment in water. "
        "Keep others away and contact the appropriate emergency service."
    ),
]


# ============================================================
# 009 - REAL PHOTO SOURCES
# ============================================================

# These are Wikimedia Commons files. The application downloads copies when
# the user opens the photo gallery and an internet connection is available.
# The source pages should be credited in the application.
PHOTO_SOURCES = [
    {
        "filename": "building_fire_1917.gif",
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/8f/Seattle_-_Building_fire%2C_1917.gif",
        "title": "Building Fire Response",
        "credit": "Seattle Municipal Archives via Wikimedia Commons, CC BY 2.0",
        "source_page": "https://commons.wikimedia.org/wiki/File:Seattle_-_Building_fire,_1917.gif",
    },
    {
        "filename": "pike_place_fire_1974.gif",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7c/Fire_at_Pike_Place_Market%2C_1974.gif",
        "title": "Pike Place Market Fire, 1974",
        "credit": "Seattle Municipal Archives via Wikimedia Commons",
        "source_page": "https://commons.wikimedia.org/wiki/File:Fire_at_Pike_Place_Market,_1974.gif",
    },
    {
        "filename": "helicopter_crash.gif",
        "url": "https://upload.wikimedia.org/wikipedia/commons/4/4c/HelicopterCrash.gif",
        "title": "Helicopter Crash",
        "credit": "Wikimedia Commons",
        "source_page": "https://commons.wikimedia.org/wiki/File:HelicopterCrash.gif",
    },
    {
        "filename": "firefighters_1927.gif",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0f/Firefighters_at_Fire_Station_No._14%2C_1927_%283024896443%29.gif",
        "title": "Firefighters, 1927",
        "credit": "Seattle Municipal Archives via Wikimedia Commons, CC BY 2.0",
        "source_page": "https://commons.wikimedia.org/wiki/File:Firefighters_at_Fire_Station_No._14,_1927_(3024896443).gif",
    },
]



# ============================================================
# 010 - THEME
# ============================================================

BG = "#0d1117"
PANEL = "#161b22"
PANEL_2 = "#1f2630"
CARD = "#202832"
TEXT = "#f4f7fb"
MUTED = "#aeb8c4"
RED = "#e53935"
RED_DARK = "#a61b1b"
ORANGE = "#ff8f00"
GREEN = "#21c77a"
BLUE = "#4da3ff"
YELLOW = "#ffd166"
WHITE = "#ffffff"
BORDER = "#303a46"


# ============================================================
# 011 - FONTS
# ============================================================

FONT_TITLE = ("Segoe UI", 25, "bold")
FONT_SUBTITLE = ("Segoe UI", 13)
FONT_HEADING = ("Segoe UI", 17, "bold")
FONT_CARD = ("Segoe UI", 12, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_BIG_NUMBER = ("Segoe UI", 22, "bold")


# ============================================================
# 012 - UTILITY: ENSURE DIRECTORIES
# ============================================================

def ensure_directories():
    """Create all application directories."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 013 - UTILITY: PASSWORD HASH
# ============================================================

def hash_password(password):
    """Return a SHA-256 password hash."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ============================================================
# 014 - UTILITY: TIMESTAMP
# ============================================================

def now_text():
    """Return a readable local timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# 015 - UTILITY: NORMALIZE
# ============================================================

def clean_text(value):
    """Trim surrounding whitespace and collapse repeated whitespace."""
    if value is None:
        return ""
    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    return value


# ============================================================
# 016 - VALIDATION: NAME
# ============================================================

def validate_name(value):
    """Validate a person's name."""
    value = clean_text(value)
    if not value:
        return False, "Name is required."
    if len(value) < 2:
        return False, "Name must contain at least 2 characters."
    if len(value) > 80:
        return False, "Name is too long."
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+", value):
        return False, "INVALID: name must contain letters, spaces, apostrophes or hyphens only."
    if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", value):
        return False, "INVALID: enter a real name."
    return True, ""


# ============================================================
# 017 - VALIDATION: PHONE
# ============================================================

def normalize_phone(value):
    """Remove harmless phone separators while preserving +."""
    value = clean_text(value)
    return re.sub(r"[ ()\-]", "", value)


# ============================================================
# 018 - VALIDATION: ETHIOPIAN PHONE
# ============================================================

def validate_phone(value):
    """Validate common Ethiopian mobile/fixed phone formats."""
    value = normalize_phone(value)
    patterns = [
        r"^09\d{8}$",
        r"^07\d{8}$",
        r"^\+2519\d{8}$",
        r"^\+2517\d{8}$",
        r"^2519\d{8}$",
        r"^2517\d{8}$",
        r"^0\d{2,3}\d{6,7}$",
    ]
    if not value:
        return False, "Phone number is required."
    if not any(re.fullmatch(pattern, value) for pattern in patterns):
        return False, "INVALID: enter a valid Ethiopian phone number."
    return True, ""


# ============================================================
# 019 - VALIDATION: USERNAME
# ============================================================

def validate_username(value):
    """Validate a username."""
    value = clean_text(value)
    if len(value) < 3:
        return False, "Username must contain at least 3 characters."
    if len(value) > 30:
        return False, "Username is too long."
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return False, "INVALID: username may contain letters, numbers, _, . and - only."
    return True, ""


# ============================================================
# 020 - VALIDATION: PASSWORD
# ============================================================

def validate_password(value):
    """Validate a new user's password."""
    if len(value) < 6:
        return False, "Password must contain at least 6 characters."
    if len(value) > 100:
        return False, "Password is too long."
    return True, ""


# ============================================================
# 021 - VALIDATION: LOCATION
# ============================================================

def validate_location(value):
    """Validate emergency location."""
    value = clean_text(value)
    if not value:
        return False, "Location is required."
    if len(value) < 3:
        return False, "Location is too short."
    if len(value) > 200:
        return False, "Location is too long."
    if re.fullmatch(r"[\W_]+", value):
        return False, "INVALID: location cannot contain symbols only."
    return True, ""


# ============================================================
# 022 - VALIDATION: DESCRIPTION
# ============================================================

def validate_description(value):
    """Validate emergency description."""
    value = clean_text(value)
    if not value:
        return False, "Description is required."
    if len(value) < 10:
        return False, "Description must contain at least 10 characters."
    if len(value) > 2000:
        return False, "Description cannot exceed 2000 characters."
    if re.fullmatch(r"[\W_]+", value):
        return False, "INVALID: description must contain meaningful text."
    return True, ""


# ============================================================
# 023 - DATABASE CLASS
# ============================================================

class Database:
    """SQLite database manager for the emergency system."""

    def __init__(self, path):
        self.path = str(path)
        self.initialize()

    # ========================================================
    # 024 - DATABASE CONNECTION
    # ========================================================

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=DATABASE_TIMEOUT)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    # ========================================================
    # 025 - DATABASE INITIALIZATION
    # ========================================================

    def initialize(self):
        ensure_directories()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS emergencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    emergency_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    admin_note TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emergency_id INTEGER NOT NULL,
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    changed_by TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    FOREIGN KEY(emergency_id) REFERENCES emergencies(id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS app_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    action TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        self.ensure_admin()

    # ========================================================
    # 026 - ENSURE ADMIN
    # ========================================================

    def ensure_admin(self):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM users WHERE username = ?",
                (DEFAULT_ADMIN_USERNAME,),
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO users
                    (full_name, phone, username, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "System Administrator",
                        "0000000000",
                        DEFAULT_ADMIN_USERNAME,
                        hash_password(DEFAULT_ADMIN_PASSWORD),
                        "admin",
                        now_text(),
                    ),
                )
                connection.commit()

    # ========================================================
    # 027 - LOG
    # ========================================================

    def log(self, username, action):
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO app_logs(username, action, created_at) VALUES (?, ?, ?)",
                (username, action, now_text()),
            )
            connection.commit()

    # ========================================================
    # 028 - CREATE USER
    # ========================================================

    def create_user(self, full_name, phone, username, password):
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO users
                (full_name, phone, username, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, 'user', ?)
                """,
                (
                    clean_text(full_name),
                    normalize_phone(phone),
                    clean_text(username),
                    hash_password(password),
                    now_text(),
                ),
            )
            connection.commit()

    # ========================================================
    # 029 - AUTHENTICATE
    # ========================================================

    def authenticate(self, username, password):
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, full_name, phone, username, password_hash, role, created_at
                FROM users
                WHERE username = ?
                """,
                (clean_text(username),),
            ).fetchone()
            if row is None:
                return None
            if row["password_hash"] != hash_password(password):
                return None
            return dict(row)

    # ========================================================
    # 030 - CREATE EMERGENCY
    # ========================================================

    def create_emergency(
        self,
        user_id,
        name,
        location,
        phone,
        emergency_type,
        description,
    ):
        timestamp = now_text()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO emergencies
                (
                    user_id,
                    name,
                    location,
                    phone,
                    emergency_type,
                    description,
                    status,
                    admin_note,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    clean_text(name),
                    clean_text(location),
                    normalize_phone(phone),
                    clean_text(emergency_type),
                    clean_text(description),
                    STATUS_PENDING,
                    "",
                    timestamp,
                    timestamp,
                ),
            )
            emergency_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO status_history
                (emergency_id, old_status, new_status, note, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    emergency_id,
                    None,
                    STATUS_PENDING,
                    "Report submitted.",
                    "system",
                    timestamp,
                ),
            )
            connection.commit()
            return emergency_id

    # ========================================================
    # 031 - GET USER REPORTS
    # ========================================================

    def get_user_reports(self, user_id):
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM emergencies
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ========================================================
    # 032 - GET ALL REPORTS
    # ========================================================

    def get_all_reports(self):
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.*,
                    u.username AS account_username
                FROM emergencies e
                LEFT JOIN users u ON e.user_id = u.id
                ORDER BY e.id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    # ========================================================
    # 033 - GET REPORT
    # ========================================================

    def get_report(self, emergency_id):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM emergencies WHERE id = ?",
                (emergency_id,),
            ).fetchone()
            return dict(row) if row else None

    # ========================================================
    # 034 - UPDATE STATUS
    # ========================================================

    def update_status(self, emergency_id, new_status, note, changed_by):
        timestamp = now_text()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM emergencies WHERE id = ?",
                (emergency_id,),
            ).fetchone()
            if row is None:
                return False
            old_status = row["status"]
            connection.execute(
                """
                UPDATE emergencies
                SET status = ?, admin_note = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    new_status,
                    clean_text(note),
                    timestamp,
                    emergency_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO status_history
                (emergency_id, old_status, new_status, note, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    emergency_id,
                    old_status,
                    new_status,
                    clean_text(note),
                    changed_by,
                    timestamp,
                ),
            )
            connection.commit()
            return True

    # ========================================================
    # 035 - REPORT COUNT
    # ========================================================

    def count_reports(self):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM emergencies"
            ).fetchone()
            return row["total"]

    # ========================================================
    # 036 - STATUS COUNT
    # ========================================================

    def count_status(self, status):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM emergencies WHERE status = ?",
                (status,),
            ).fetchone()
            return row["total"]

    # ========================================================
    # 037 - USER COUNT
    # ========================================================

    def count_users(self):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM users WHERE role = 'user'"
            ).fetchone()
            return row["total"]

    # ========================================================
    # 038 - HISTORY
    # ========================================================

    def get_history(self, emergency_id):
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM status_history
                WHERE emergency_id = ?
                ORDER BY id DESC
                """,
                (emergency_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ========================================================
    # 039 - SEARCH REPORTS
    # ========================================================

    def search_reports(self, search_text="", status="All"):
        search_text = clean_text(search_text)
        like = f"%{search_text}%"
        with self.connect() as connection:
            if status == "All":
                rows = connection.execute(
                    """
                    SELECT e.*, u.username AS account_username
                    FROM emergencies e
                    LEFT JOIN users u ON e.user_id = u.id
                    WHERE
                        e.name LIKE ?
                        OR e.location LIKE ?
                        OR e.phone LIKE ?
                        OR e.emergency_type LIKE ?
                        OR e.description LIKE ?
                        OR e.status LIKE ?
                    ORDER BY e.id DESC
                    """,
                    (like, like, like, like, like, like),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT e.*, u.username AS account_username
                    FROM emergencies e
                    LEFT JOIN users u ON e.user_id = u.id
                    WHERE
                        e.status = ?
                        AND (
                            e.name LIKE ?
                            OR e.location LIKE ?
                            OR e.phone LIKE ?
                            OR e.emergency_type LIKE ?
                            OR e.description LIKE ?
                        )
                    ORDER BY e.id DESC
                    """,
                    (status, like, like, like, like, like),
                ).fetchall()
            return [dict(row) for row in rows]


# ============================================================
# 040 - PHOTO MANAGER
# ============================================================

class PhotoManager:
    """Downloads and prepares real emergency photographs."""

    def __init__(self):
        ensure_directories()
        self.photos = {}
        self.loading = False

    # ========================================================
    # 041 - IMAGE URL
    # ========================================================

    def build_url(self, source):
        return source["url"]

    # ========================================================
    # 042 - DOWNLOAD ONE PHOTO
    # ========================================================

    def download_photo(self, source):
        destination = PHOTO_DIR / source["filename"]
        if destination.exists() and destination.stat().st_size > 1000:
            return destination
        try:
            request = urllib.request.Request(
                self.build_url(source),
                headers={"User-Agent": "EmergencyManagementEducationalApp/3.0"},
            )
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read()
            if len(data) < 1000:
                return None
            destination.write_bytes(data)
            return destination
        except Exception:
            return None

    # ========================================================
    # 043 - DOWNLOAD ALL
    # ========================================================

    def download_all(self, callback=None):
        if self.loading:
            return
        self.loading = True

        def worker():
            results = []
            for source in PHOTO_SOURCES:
                path = self.download_photo(source)
                if path:
                    results.append((source, path))
            self.loading = False
            self.photos = {source["filename"]: path for source, path in results}
            if callback:
                callback(results)

        threading.Thread(target=worker, daemon=True).start()

    # ========================================================
    # 044 - LOCAL PHOTO PATHS
    # ========================================================

    def local_paths(self):
        paths = []
        for source in PHOTO_SOURCES:
            path = PHOTO_DIR / source["filename"]
            if path.exists():
                paths.append((source, path))
        return paths

    # ========================================================
    # 045 - CREATE TKINTER IMAGE
    # ========================================================

    def thumbnail(self, path, width=300, height=190):
        """Load a GIF/PNG directly with Tkinter; no Pillow is required."""
        try:
            image = tk.PhotoImage(file=str(path))
            # subsample keeps large images from overwhelming the UI.
            factor = max(1, int(max(image.width() / width, image.height() / height)))
            if factor > 1:
                image = image.subsample(factor, factor)
            return image
        except Exception:
            return None


# ============================================================
# 046 - BASE APP CLASS
# ============================================================

class EmergencyApp:
    """Main application controller."""

    def __init__(self, root):
        self.root = root
        self.db = Database(DB_FILE)
        self.photo_manager = PhotoManager()
        self.current_user = None
        self.current_frame = None
        self.images = []
        self.style = ttk.Style()
        self.configure_style()
        self.configure_root()
        self.show_welcome()

    # ========================================================
    # 047 - STYLE
    # ========================================================

    def configure_style(self):
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(
            "TFrame",
            background=BG,
        )
        self.style.configure(
            "Card.TFrame",
            background=CARD,
        )
        self.style.configure(
            "TLabel",
            background=BG,
            foreground=TEXT,
            font=FONT_BODY,
        )
        self.style.configure(
            "Card.TLabel",
            background=CARD,
            foreground=TEXT,
            font=FONT_BODY,
        )
        self.style.configure(
            "Heading.TLabel",
            background=BG,
            foreground=TEXT,
            font=FONT_HEADING,
        )
        self.style.configure(
            "Muted.TLabel",
            background=BG,
            foreground=MUTED,
            font=FONT_BODY,
        )
        self.style.configure(
            "CardMuted.TLabel",
            background=CARD,
            foreground=MUTED,
            font=FONT_SMALL,
        )
        self.style.configure(
            "Danger.TButton",
            font=FONT_BUTTON,
            foreground=WHITE,
            background=RED,
            padding=(14, 9),
        )
        self.style.map(
            "Danger.TButton",
            background=[("active", RED_DARK)],
        )
        self.style.configure(
            "Accent.TButton",
            font=FONT_BUTTON,
            foreground=WHITE,
            background=BLUE,
            padding=(14, 9),
        )
        self.style.map(
            "Accent.TButton",
            background=[("active", "#2d7dcc")],
        )
        self.style.configure(
            "Success.TButton",
            font=FONT_BUTTON,
            foreground=WHITE,
            background=GREEN,
            padding=(14, 9),
        )
        self.style.map(
            "Success.TButton",
            background=[("active", "#159a5c")],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=PANEL_2,
            foreground=TEXT,
            insertcolor=TEXT,
            padding=8,
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=PANEL_2,
            background=PANEL_2,
            foreground=TEXT,
            padding=7,
        )
        self.style.configure(
            "Treeview",
            background=PANEL_2,
            fieldbackground=PANEL_2,
            foreground=TEXT,
            rowheight=32,
            font=FONT_SMALL,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#2b3440",
            foreground=WHITE,
            font=FONT_SMALL,
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#34506e")],
            foreground=[("selected", WHITE)],
        )

    # ========================================================
    # 048 - ROOT CONFIG
    # ========================================================

    def configure_root(self):
        self.root.title(APP_TITLE)
        self.root.geometry("1180x760")
        self.root.minsize(980, 650)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ========================================================
    # 049 - CLEAR
    # ========================================================

    def clear_frame(self):
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None
        self.images.clear()

    # ========================================================
    # 050 - CREATE ROOT FRAME
    # ========================================================

    def make_frame(self):
        self.clear_frame()
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=BOTH, expand=True)
        self.current_frame = frame
        return frame

    # ========================================================
    # 051 - TITLE
    # ========================================================

    def add_title(self, parent, title, subtitle=None):
        wrapper = tk.Frame(parent, bg=BG)
        wrapper.pack(fill=X, padx=30, pady=(24, 8))
        tk.Label(
            wrapper,
            text=title,
            bg=BG,
            fg=TEXT,
            font=FONT_TITLE,
        ).pack(anchor="w")
        if subtitle:
            tk.Label(
                wrapper,
                text=subtitle,
                bg=BG,
                fg=MUTED,
                font=FONT_SUBTITLE,
            ).pack(anchor="w", pady=(5, 0))
        return wrapper

    # ========================================================
    # 052 - BUTTON
    # ========================================================

    def button(self, parent, text, command, kind="accent", width=None):
        if kind == "danger":
            style = "Danger.TButton"
        elif kind == "success":
            style = "Success.TButton"
        else:
            style = "Accent.TButton"
        kwargs = {"text": text, "command": command, "style": style}
        if width:
            kwargs["width"] = width
        return ttk.Button(parent, **kwargs)

    # ========================================================
    # 053 - STATUS MESSAGE
    # ========================================================

    def status_message(self, parent, variable, text, error=False):
        variable.set(text)
        return

    # ========================================================
    # 054 - SCROLLABLE FRAME
    # ========================================================

    def scrollable(self, parent):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(
            outer,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(
            outer,
            orient=VERTICAL,
            command=canvas.yview,
        )
        inner = tk.Frame(canvas, bg=BG)

        window_id = canvas.create_window(
            (0, 0),
            window=inner,
            anchor="nw",
        )

        def update_scroll(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_inner(event):
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", update_scroll)
        canvas.bind("<Configure>", resize_inner)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        return inner

    # ========================================================
    # 055 - WELCOME PAGE
    # ========================================================

    def show_welcome(self):
        frame = self.make_frame()

        top = tk.Frame(frame, bg=BG)
        top.pack(fill=X, padx=30, pady=(22, 8))

        tk.Label(
            top,
            text="🚨",
            bg=BG,
            fg=RED,
            font=("Segoe UI Emoji", 34),
        ).pack(side=LEFT, padx=(0, 12))

        heading = tk.Frame(top, bg=BG)
        heading.pack(side=LEFT)

        tk.Label(
            heading,
            text="EMERGENCY RESPONSE",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")

        tk.Label(
            heading,
            text="Ethiopian Emergency Management & Response System",
            bg=BG,
            fg=MUTED,
            font=FONT_SUBTITLE,
        ).pack(anchor="w")

        hero = tk.Frame(
            frame,
            bg="#151a21",
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        hero.pack(fill=BOTH, expand=True, padx=30, pady=18)

        hero_left = tk.Frame(hero, bg="#151a21")
        hero_left.pack(side=LEFT, fill=BOTH, expand=True, padx=35, pady=30)

        tk.Label(
            hero_left,
            text="When every second matters.",
            bg="#151a21",
            fg=WHITE,
            font=("Segoe UI", 27, "bold"),
            wraplength=520,
            justify=LEFT,
        ).pack(anchor="w", pady=(20, 12))

        tk.Label(
            hero_left,
            text=(
                "Report emergencies, access safety information, "
                "and let authorized administrators track response status."
            ),
            bg="#151a21",
            fg=MUTED,
            font=("Segoe UI", 13),
            wraplength=530,
            justify=LEFT,
        ).pack(anchor="w", pady=(0, 22))

        warning = tk.Frame(hero_left, bg="#2a2020")
        warning.pack(fill=X, pady=(0, 24))

        tk.Label(
            warning,
            text="⚠ FOR LIFE-THREATENING EMERGENCIES",
            bg="#2a2020",
            fg=YELLOW,
            font=FONT_CARD,
        ).pack(anchor="w", padx=15, pady=(12, 3))

        tk.Label(
            warning,
            text="Call the appropriate emergency service immediately.",
            bg="#2a2020",
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=15, pady=(0, 12))

        actions = tk.Frame(hero_left, bg="#151a21")
        actions.pack(fill=X)

        self.button(
            actions,
            "CREATE USER ACCOUNT",
            self.show_register,
            "success",
        ).pack(side=LEFT, padx=(0, 10))

        self.button(
            actions,
            "USER LOGIN",
            self.show_login,
            "accent",
        ).pack(side=LEFT, padx=(0, 10))

        self.button(
            actions,
            "EMERGENCY HELP",
            self.show_help,
            "danger",
        ).pack(side=LEFT)

        # The front page intentionally does NOT show the admin password.
        self.button(
            frame,
            "ADMIN LOGIN",
            self.show_admin_login,
            "danger",
        ).pack(pady=(0, 8))

        tk.Label(
            frame,
            text=f"Version {APP_VERSION} • SQLite local database • Educational prototype",
            bg=BG,
            fg=MUTED,
            font=FONT_SMALL,
        ).pack(pady=(0, 12))

        self.load_front_photo(hero)

    # ========================================================
    # 056 - FRONT PHOTO
    # ========================================================

    def load_front_photo(self, hero):
        right = tk.Frame(hero, bg="#151a21", width=440)
        right.pack(side=RIGHT, fill=Y, padx=20, pady=20)
        right.pack_propagate(False)

        photo = None
        local = self.photo_manager.local_paths()
        if local:
            photo = self.photo_manager.thumbnail(
                local[0][1],
                width=420,
                height=420,
            )

        if photo:
            self.images.append(photo)
            tk.Label(
                right,
                image=photo,
                bg="#151a21",
            ).pack(fill=BOTH, expand=True, padx=5, pady=5)
        else:
            visual = tk.Frame(right, bg="#2b1717")
            visual.pack(fill=BOTH, expand=True, padx=5, pady=5)
            tk.Label(
                visual,
                text="🔥",
                bg="#2b1717",
                fg=ORANGE,
                font=("Segoe UI Emoji", 70),
            ).pack(pady=(70, 15))
            tk.Label(
                visual,
                text="REAL EMERGENCY\nPHOTO GALLERY",
                bg="#2b1717",
                fg=WHITE,
                font=("Segoe UI", 18, "bold"),
                justify=CENTER,
            ).pack()
            tk.Label(
                visual,
                text="Open Photo Gallery after login\nto download real reference photos.",
                bg="#2b1717",
                fg=MUTED,
                font=FONT_BODY,
                justify=CENTER,
            ).pack(pady=12)

        # Start the background download only when no local photo exists.
        # IMPORTANT FIX: the old callback rebuilt the welcome page, which
        # started another download and rebuilt the page again repeatedly.
        # That caused the window to shake/flicker.  We keep the same photo
        # feature, but refresh the page only once after the first download.
        if not local:
            self.photo_manager.download_all(
                callback=lambda _results: self.root.after(0, self._refresh_welcome_photo)
            )

    # ========================================================
    # 056B - REFRESH WELCOME PHOTO
    # ========================================================

    def _refresh_welcome_photo(self):
        """Refresh the welcome page after the first real photo downloads."""
        if self.current_user is None:
            self.show_welcome()

    # ========================================================
    # 057 - REGISTER PAGE
    # ========================================================

    def show_register(self):
        frame = self.make_frame()
        self.add_title(
            frame,
            "Create User Account",
            "Enter valid information. INVALID entries are rejected before saving.",
        )

        outer = tk.Frame(frame, bg=BG)
        outer.pack(fill=BOTH, expand=True, padx=30, pady=10)

        card = tk.Frame(
            outer,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.pack(anchor="n", fill=X, padx=120, pady=10)

        fields = {}

        def add_field(label_text, key, show=None):
            row = tk.Frame(card, bg=CARD)
            row.pack(fill=X, padx=30, pady=8)
            tk.Label(
                row,
                text=label_text,
                bg=CARD,
                fg=TEXT,
                font=FONT_BODY,
                width=18,
                anchor="w",
            ).pack(side=LEFT)
            entry = ttk.Entry(row, show=show)
            entry.pack(side=LEFT, fill=X, expand=True)
            fields[key] = entry
            return entry

        add_field("Full name *", "name")
        add_field("Phone number *", "phone")
        add_field("Username *", "username")
        add_field("Password *", "password", "•")
        add_field("Confirm password *", "confirm", "•")

        error_var = tk.StringVar(value="")

        tk.Label(
            card,
            textvariable=error_var,
            bg=CARD,
            fg="#ff6b6b",
            font=("Segoe UI", 10, "bold"),
            wraplength=650,
            justify=LEFT,
        ).pack(anchor="w", padx=30, pady=(5, 8))

        def register():
            error_var.set("")

            name = fields["name"].get()
            phone = fields["phone"].get()
            username = fields["username"].get()
            password = fields["password"].get()
            confirm = fields["confirm"].get()

            ok, msg = validate_name(name)
            if not ok:
                error_var.set(msg)
                return

            ok, msg = validate_phone(phone)
            if not ok:
                error_var.set(msg)
                return

            ok, msg = validate_username(username)
            if not ok:
                error_var.set(msg)
                return

            if username.lower() == DEFAULT_ADMIN_USERNAME:
                error_var.set("INVALID: that username is reserved.")
                return

            ok, msg = validate_password(password)
            if not ok:
                error_var.set(msg)
                return

            if password != confirm:
                error_var.set("INVALID: passwords do not match.")
                return

            try:
                self.db.create_user(name, phone, username, password)
            except sqlite3.IntegrityError:
                error_var.set("INVALID: that username already exists.")
                return
            except Exception as exc:
                error_var.set(f"Could not create account: {exc}")
                return

            self.db.log(username, "Created user account")
            messagebox.showinfo(
                "Account Created",
                "Your user account was created successfully.\n\nYou can now log in.",
            )
            self.show_login()

        buttons = tk.Frame(card, bg=CARD)
        buttons.pack(fill=X, padx=30, pady=22)

        self.button(
            buttons,
            "CREATE ACCOUNT",
            register,
            "success",
        ).pack(side=LEFT, padx=(0, 10))

        self.button(
            buttons,
            "BACK",
            self.show_welcome,
            "accent",
        ).pack(side=LEFT)

    # ========================================================
    # 058 - USER LOGIN
    # ========================================================

    def show_login(self):
        frame = self.make_frame()
        self.add_title(
            frame,
            "User Login",
            "Sign in with your registered account.",
        )

        card = tk.Frame(frame, bg=CARD)
        card.pack(anchor="n", fill=X, padx=250, pady=25)

        username_var = tk.StringVar()
        password_var = tk.StringVar()
        message_var = tk.StringVar()

        tk.Label(
            card,
            text="Username",
            bg=CARD,
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=30, pady=(25, 6))

        username_entry = ttk.Entry(card, textvariable=username_var)
        username_entry.pack(fill=X, padx=30)

        tk.Label(
            card,
            text="Password",
            bg=CARD,
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=30, pady=(18, 6))

        password_entry = ttk.Entry(
            card,
            textvariable=password_var,
            show="•",
        )
        password_entry.pack(fill=X, padx=30)

        tk.Label(
            card,
            textvariable=message_var,
            bg=CARD,
            fg="#ff6b6b",
            font=FONT_BODY,
        ).pack(anchor="w", padx=30, pady=12)

        def login():
            username = clean_text(username_var.get())
            password = password_var.get()

            if not username or not password:
                message_var.set("INVALID: username and password are required.")
                return

            user = self.db.authenticate(username, password)
            if user is None or user["role"] != "user":
                message_var.set("INVALID: incorrect user login information.")
                return

            self.current_user = user
            self.db.log(username, "User login")
            self.show_user_dashboard()

        self.button(
            card,
            "LOGIN",
            login,
            "accent",
        ).pack(fill=X, padx=30, pady=(8, 10))

        self.button(
            card,
            "CREATE NEW ACCOUNT",
            self.show_register,
            "success",
        ).pack(fill=X, padx=30, pady=5)

        self.button(
            card,
            "BACK",
            self.show_welcome,
            "danger",
        ).pack(fill=X, padx=30, pady=(5, 28))

        username_entry.focus_set()
        password_entry.bind("<Return>", lambda _event: login())

    # ========================================================
    # 059 - ADMIN LOGIN
    # ========================================================

    def show_admin_login(self):
        frame = self.make_frame()
        self.add_title(
            frame,
            "Administrator Login",
            "Authorized administrators only.",
        )

        card = tk.Frame(frame, bg=CARD)
        card.pack(anchor="n", fill=X, padx=250, pady=25)

        username_var = tk.StringVar()
        password_var = tk.StringVar()
        message_var = tk.StringVar()

        tk.Label(
            card,
            text="Administrator username",
            bg=CARD,
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=30, pady=(25, 6))

        user_entry = ttk.Entry(card, textvariable=username_var)
        user_entry.pack(fill=X, padx=30)

        tk.Label(
            card,
            text="Administrator password",
            bg=CARD,
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=30, pady=(18, 6))

        pass_entry = ttk.Entry(
            card,
            textvariable=password_var,
            show="•",
        )
        pass_entry.pack(fill=X, padx=30)

        # Deliberately no label, hint, placeholder or text reveals 102030.
        tk.Label(
            card,
            textvariable=message_var,
            bg=CARD,
            fg="#ff6b6b",
            font=FONT_BODY,
        ).pack(anchor="w", padx=30, pady=12)

        def login():
            username = clean_text(username_var.get())
            password = password_var.get()
            if not username or not password:
                message_var.set("INVALID: administrator credentials are required.")
                return

            user = self.db.authenticate(username, password)
            if user is None or user["role"] != "admin":
                message_var.set("INVALID: incorrect administrator credentials.")
                return

            self.current_user = user
            self.db.log(username, "Administrator login")
            self.show_admin_dashboard()

        self.button(
            card,
            "ADMIN SIGN IN",
            login,
            "danger",
        ).pack(fill=X, padx=30, pady=(8, 10))

        self.button(
            card,
            "BACK",
            self.show_welcome,
            "accent",
        ).pack(fill=X, padx=30, pady=(5, 28))

        user_entry.focus_set()
        pass_entry.bind("<Return>", lambda _event: login())

    # ========================================================
    # 060 - USER DASHBOARD
    # ========================================================

    def show_user_dashboard(self):
        frame = self.make_frame()

        top = tk.Frame(frame, bg=BG)
        top.pack(fill=X, padx=25, pady=(18, 8))

        tk.Label(
            top,
            text=f"Welcome, {self.current_user['full_name']}",
            bg=BG,
            fg=TEXT,
            font=FONT_HEADING,
        ).pack(side=LEFT)

        self.button(
            top,
            "LOG OUT",
            self.logout,
            "danger",
        ).pack(side=RIGHT)

        content = tk.Frame(frame, bg=BG)
        content.pack(fill=BOTH, expand=True, padx=25, pady=10)

        cards = tk.Frame(content, bg=BG)
        cards.pack(fill=X)

        self.make_stat_card(
            cards,
            "📞",
            "EMERGENCY HELP",
            "Numbers & safety instructions",
            self.show_help,
        ).pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        self.make_stat_card(
            cards,
            "🚨",
            "REPORT EMERGENCY",
            "Send a new emergency report",
            self.show_report_form,
        ).pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        self.make_stat_card(
            cards,
            "📋",
            "MY REPORTS",
            "View your submitted reports",
            self.show_user_reports,
        ).pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        self.make_stat_card(
            cards,
            "📷",
            "PHOTO GALLERY",
            "Real emergency reference photos",
            self.show_photo_gallery,
        ).pack(side=LEFT, fill=BOTH, expand=True, padx=5)

        panel = tk.Frame(content, bg=PANEL)
        panel.pack(fill=BOTH, expand=True, pady=15)

        tk.Label(
            panel,
            text="Quick Safety Reminder",
            bg=PANEL,
            fg=TEXT,
            font=FONT_HEADING,
        ).pack(anchor="w", padx=20, pady=(18, 5))

        tk.Label(
            panel,
            text=(
                "For immediate danger, do not wait for the application. "
                "Call emergency services and clearly state your location."
            ),
            bg=PANEL,
            fg=MUTED,
            font=FONT_BODY,
            wraplength=800,
            justify=LEFT,
        ).pack(anchor="w", padx=20, pady=(0, 15))

        numbers = tk.Frame(panel, bg=PANEL)
        numbers.pack(fill=X, padx=15, pady=10)

        for contact in EMERGENCY_CONTACTS[:4]:
            box = tk.Frame(numbers, bg=CARD)
            box.pack(side=LEFT, fill=BOTH, expand=True, padx=5)
            tk.Label(
                box,
                text=contact["service"],
                bg=CARD,
                fg=TEXT,
                font=FONT_CARD,
            ).pack(pady=(12, 2))
            tk.Label(
                box,
                text=contact["number"],
                bg=CARD,
                fg=RED if contact["service"] == "General Emergency" else GREEN,
                font=FONT_BIG_NUMBER,
            ).pack(pady=2)
            tk.Label(
                box,
                text=contact["location"],
                bg=CARD,
                fg=MUTED,
                font=FONT_SMALL,
            ).pack(pady=(0, 12))

    # ========================================================
    # 061 - STAT CARD
    # ========================================================

    def make_stat_card(self, parent, icon, title, subtitle, command):
        card = tk.Frame(
            parent,
            bg=CARD,
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        tk.Label(
            card,
            text=icon,
            bg=CARD,
            fg=WHITE,
            font=("Segoe UI Emoji", 27),
        ).pack(pady=(16, 5))
        tk.Label(
            card,
            text=title,
            bg=CARD,
            fg=TEXT,
            font=FONT_CARD,
        ).pack()
        tk.Label(
            card,
            text=subtitle,
            bg=CARD,
            fg=MUTED,
            font=FONT_SMALL,
            wraplength=180,
            justify=CENTER,
        ).pack(pady=(4, 15))

        def clicked(_event=None):
            command()

        card.bind("<Button-1>", clicked)
        for child in card.winfo_children():
            child.bind("<Button-1>", clicked)
        return card

    # ========================================================
    # 062 - HELP PAGE
    # ========================================================

    def show_help(self):
        frame = self.make_frame()
        self.add_title(
            frame,
            "Emergency Help & Ethiopian Emergency Numbers",
            "Use these contacts for immediate assistance. Verify local availability.",
        )

        body = self.scrollable(frame)

        emergency_box = tk.Frame(body, bg="#2a1717")
        emergency_box.pack(fill=X, padx=30, pady=10)

        tk.Label(
            emergency_box,
            text="🚨 IMMEDIATE DANGER",
            bg="#2a1717",
            fg=YELLOW,
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))

        tk.Label(
            emergency_box,
            text=(
                "If someone is in immediate danger, call the appropriate service "
                "now. Give your city, exact location, nearby landmark and callback number."
            ),
            bg="#2a1717",
            fg=TEXT,
            font=FONT_BODY,
            wraplength=900,
            justify=LEFT,
        ).pack(anchor="w", padx=20, pady=(0, 18))

        contacts = tk.Frame(body, bg=BG)
        contacts.pack(fill=X, padx=30, pady=10)

        for index, contact in enumerate(EMERGENCY_CONTACTS):
            card = tk.Frame(
                contacts,
                bg=CARD,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            card.grid(
                row=index // 3,
                column=index % 3,
                sticky="nsew",
                padx=5,
                pady=5,
            )
            contacts.grid_columnconfigure(index % 3, weight=1)

            tk.Label(
                card,
                text=contact["service"],
                bg=CARD,
                fg=TEXT,
                font=FONT_CARD,
            ).pack(anchor="w", padx=16, pady=(15, 5))

            tk.Label(
                card,
                text=contact["number"],
                bg=CARD,
                fg=GREEN,
                font=("Segoe UI", 23, "bold"),
            ).pack(anchor="w", padx=16)

            tk.Label(
                card,
                text=contact["description"],
                bg=CARD,
                fg=MUTED,
                font=FONT_SMALL,
                wraplength=260,
                justify=LEFT,
            ).pack(anchor="w", padx=16, pady=(5, 15))

        help_header = tk.Label(
            body,
            text="Emergency Safety Information",
            bg=BG,
            fg=TEXT,
            font=FONT_HEADING,
        )
        help_header.pack(anchor="w", padx=30, pady=(25, 8))

        for title, information in HELP_INFORMATION:
            card = tk.Frame(body, bg=CARD)
            card.pack(fill=X, padx=30, pady=5)

            tk.Label(
                card,
                text=title,
                bg=CARD,
                fg=ORANGE,
                font=FONT_CARD,
                width=24,
                anchor="w",
            ).pack(side=LEFT, padx=15, pady=15)

            tk.Label(
                card,
                text=information,
                bg=CARD,
                fg=TEXT,
                font=FONT_BODY,
                wraplength=800,
                justify=LEFT,
            ).pack(side=LEFT, fill=X, expand=True, padx=10, pady=15)

        bottom = tk.Frame(frame, bg=BG)
        bottom.pack(fill=X, padx=30, pady=10)

        back_command = self.show_welcome
        if self.current_user:
            if self.current_user["role"] == "user":
                back_command = self.show_user_dashboard
            elif self.current_user["role"] == "admin":
                back_command = self.show_admin_dashboard

        self.button(
            bottom,
            "BACK",
            back_command,
            "accent",
        ).pack(side=LEFT)

    # ========================================================
    # 063 - REPORT FORM
    # ========================================================

    def show_report_form(self):
        if not self.current_user or self.current_user["role"] != "user":
            self.show_login()
            return

        frame = self.make_frame()
        self.add_title(
            frame,
            "Report an Emergency",
            "All fields marked * are required. False reports can delay real assistance.",
        )

        body = self.scrollable(frame)

        card = tk.Frame(
            body,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.pack(fill=X, padx=80, pady=10)

        variables = {
            "name": tk.StringVar(value=self.current_user["full_name"]),
            "location": tk.StringVar(),
            "phone": tk.StringVar(value=self.current_user["phone"]),
            "type": tk.StringVar(value=EMERGENCY_TYPES[0]),
        }

        entries = {}

        def row(label, key):
            line = tk.Frame(card, bg=CARD)
            line.pack(fill=X, padx=25, pady=8)
            tk.Label(
                line,
                text=label,
                bg=CARD,
                fg=TEXT,
                font=FONT_BODY,
                width=20,
                anchor="w",
            ).pack(side=LEFT)
            entry = ttk.Entry(line, textvariable=variables[key])
            entry.pack(side=LEFT, fill=X, expand=True)
            entries[key] = entry

        row("Your name *", "name")
        row("Location *", "location")
        row("Phone number *", "phone")

        type_line = tk.Frame(card, bg=CARD)
        type_line.pack(fill=X, padx=25, pady=8)

        tk.Label(
            type_line,
            text="Emergency type *",
            bg=CARD,
            fg=TEXT,
            font=FONT_BODY,
            width=20,
            anchor="w",
        ).pack(side=LEFT)

        combo = ttk.Combobox(
            type_line,
            textvariable=variables["type"],
            values=EMERGENCY_TYPES,
            state="readonly",
        )
        combo.pack(side=LEFT, fill=X, expand=True)

        tk.Label(
            card,
            text="Description *",
            bg=CARD,
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=25, pady=(14, 6))

        description = tk.Text(
            card,
            height=8,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            wrap="word",
            font=FONT_BODY,
        )
        description.pack(fill=X, padx=25)

        error_var = tk.StringVar()

        tk.Label(
            card,
            textvariable=error_var,
            bg=CARD,
            fg="#ff6b6b",
            font=("Segoe UI", 10, "bold"),
            wraplength=850,
            justify=LEFT,
        ).pack(anchor="w", padx=25, pady=10)

        def submit():
            error_var.set("")

            name = variables["name"].get()
            location = variables["location"].get()
            phone = variables["phone"].get()
            emergency_type = variables["type"].get()
            details = description.get("1.0", END).strip()

            ok, msg = validate_name(name)
            if not ok:
                error_var.set(msg)
                entries["name"].focus_set()
                return

            ok, msg = validate_location(location)
            if not ok:
                error_var.set(msg)
                entries["location"].focus_set()
                return

            ok, msg = validate_phone(phone)
            if not ok:
                error_var.set(msg)
                entries["phone"].focus_set()
                return

            if emergency_type not in EMERGENCY_TYPES:
                error_var.set("INVALID: choose a valid emergency type.")
                return

            ok, msg = validate_description(details)
            if not ok:
                error_var.set(msg)
                description.focus_set()
                return

            confirmed = messagebox.askyesno(
                "Confirm Emergency Report",
                (
                    "Are you sure you want to submit this emergency report?\n\n"
                    "Make sure the location and phone number are correct."
                ),
            )
            if not confirmed:
                return

            try:
                report_id = self.db.create_emergency(
                    self.current_user["id"],
                    name,
                    location,
                    phone,
                    emergency_type,
                    details,
                )
                self.db.log(
                    self.current_user["username"],
                    f"Created emergency report #{report_id}",
                )
            except Exception as exc:
                error_var.set(f"Could not save report: {exc}")
                return

            messagebox.showinfo(
                "Emergency Report Submitted",
                (
                    f"Report #{report_id} was submitted successfully.\n\n"
                    "Status: Pending\n"
                    "An administrator can now review and update its status."
                ),
            )
            self.show_user_reports()

        actions = tk.Frame(card, bg=CARD)
        actions.pack(fill=X, padx=25, pady=20)

        self.button(
            actions,
            "SUBMIT EMERGENCY REPORT",
            submit,
            "danger",
        ).pack(side=LEFT, padx=(0, 10))

        self.button(
            actions,
            "CANCEL",
            self.show_user_dashboard,
            "accent",
        ).pack(side=LEFT)

    # ========================================================
    # 064 - USER REPORTS
    # ========================================================

    def show_user_reports(self):
        if not self.current_user:
            self.show_login()
            return

        frame = self.make_frame()
        self.add_title(
            frame,
            "My Emergency Reports",
            "Track the status of reports submitted from your account.",
        )

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill=X, padx=30, pady=8)

        self.button(
            toolbar,
            "NEW REPORT",
            self.show_report_form,
            "danger",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            toolbar,
            "REFRESH",
            self.show_user_reports,
            "accent",
        ).pack(side=LEFT)

        body = tk.Frame(frame, bg=BG)
        body.pack(fill=BOTH, expand=True, padx=30, pady=10)

        columns = (
            "id",
            "type",
            "location",
            "status",
            "created",
            "updated",
        )

        tree = ttk.Treeview(
            body,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "ID",
            "type": "Emergency Type",
            "location": "Location",
            "status": "Status",
            "created": "Created",
            "updated": "Updated",
        }

        widths = {
            "id": 70,
            "type": 180,
            "location": 240,
            "status": 150,
            "created": 155,
            "updated": 155,
        }

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")

        scroll = ttk.Scrollbar(
            body,
            orient=VERTICAL,
            command=tree.yview,
        )
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=RIGHT, fill=Y)

        reports = self.db.get_user_reports(self.current_user["id"])
        for report in reports:
            tree.insert(
                "",
                END,
                values=(
                    report["id"],
                    report["emergency_type"],
                    report["location"],
                    report["status"],
                    report["created_at"],
                    report["updated_at"],
                ),
            )

        def open_selected(_event=None):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            if not values:
                return
            self.show_report_detail(int(values[0]), user_view=True)

        tree.bind("<Double-1>", open_selected)

        tk.Label(
            frame,
            text="Double-click a report to see details and status history.",
            bg=BG,
            fg=MUTED,
            font=FONT_SMALL,
        ).pack(anchor="w", padx=30, pady=5)

    # ========================================================
    # 065 - REPORT DETAIL
    # ========================================================

    def show_report_detail(self, report_id, user_view=False):
        report = self.db.get_report(report_id)
        if report is None:
            messagebox.showerror("Not Found", "The selected report no longer exists.")
            return

        frame = self.make_frame()
        self.add_title(
            frame,
            f"Emergency Report #{report_id}",
            "Report details and response history.",
        )

        body = self.scrollable(frame)

        card = tk.Frame(body, bg=CARD)
        card.pack(fill=X, padx=60, pady=10)

        details = [
            ("Reporter", report["name"]),
            ("Phone", report["phone"]),
            ("Emergency Type", report["emergency_type"]),
            ("Location", report["location"]),
            ("Status", report["status"]),
            ("Created", report["created_at"]),
            ("Last Updated", report["updated_at"]),
            ("Admin Note", report["admin_note"] or "No administrator note."),
            ("Description", report["description"]),
        ]

        for label, value in details:
            row = tk.Frame(card, bg=CARD)
            row.pack(fill=X, padx=20, pady=7)

            tk.Label(
                row,
                text=label,
                bg=CARD,
                fg=MUTED,
                font=FONT_BODY,
                width=18,
                anchor="nw",
            ).pack(side=LEFT)

            tk.Label(
                row,
                text=value,
                bg=CARD,
                fg=TEXT,
                font=FONT_BODY,
                wraplength=750,
                justify=LEFT,
                anchor="w",
            ).pack(side=LEFT, fill=X, expand=True)

        tk.Label(
            body,
            text="Status History",
            bg=BG,
            fg=TEXT,
            font=FONT_HEADING,
        ).pack(anchor="w", padx=60, pady=(20, 8))

        history = self.db.get_history(report_id)

        for item in history:
            box = tk.Frame(body, bg=PANEL)
            box.pack(fill=X, padx=60, pady=4)

            tk.Label(
                box,
                text=item["new_status"],
                bg=PANEL,
                fg=GREEN if item["new_status"] == STATUS_RESOLVED else YELLOW,
                font=FONT_CARD,
                width=18,
                anchor="w",
            ).pack(side=LEFT, padx=15, pady=12)

            note = item["note"] or "No note."
            tk.Label(
                box,
                text=f"{item['changed_at']} • {item['changed_by']}\n{note}",
                bg=PANEL,
                fg=TEXT,
                font=FONT_SMALL,
                justify=LEFT,
                anchor="w",
            ).pack(side=LEFT, fill=X, expand=True, padx=10, pady=12)

        bottom = tk.Frame(frame, bg=BG)
        bottom.pack(fill=X, padx=60, pady=12)

        if user_view:
            command = self.show_user_reports
        else:
            command = self.show_admin_reports

        self.button(
            bottom,
            "BACK",
            command,
            "accent",
        ).pack(side=LEFT)

    # ========================================================
    # 066 - PHOTO GALLERY
    # ========================================================

    def show_photo_gallery(self):
        frame = self.make_frame()
        self.add_title(
            frame,
            "Real Emergency Photo Gallery",
            "Reference photographs downloaded from Wikimedia Commons when internet is available. The app does not require Pillow or any other package.",
        )

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill=X, padx=30, pady=8)

        self.button(
            toolbar,
            "DOWNLOAD / REFRESH PHOTOS",
            lambda: self.photo_manager.download_all(
                callback=lambda _results: self.root.after(
                    0,
                    self.show_photo_gallery,
                )
            ),
            "accent",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            toolbar,
            "BACK",
            self.go_back_from_gallery,
            "danger",
        ).pack(side=LEFT)

        body = self.scrollable(frame)

        local = self.photo_manager.local_paths()

        if not local:
            empty = tk.Frame(body, bg=CARD)
            empty.pack(fill=X, padx=30, pady=25)

            tk.Label(
                empty,
                text="No photos are cached yet.",
                bg=CARD,
                fg=TEXT,
                font=FONT_HEADING,
            ).pack(pady=(25, 8))

            tk.Label(
                empty,
                text=(
                    "Press DOWNLOAD / REFRESH PHOTOS while connected to the internet. "
                    "The application will save the photos locally."
                ),
                bg=CARD,
                fg=MUTED,
                font=FONT_BODY,
                wraplength=700,
                justify=CENTER,
            ).pack(pady=(0, 25))

        for index, (source, path) in enumerate(local):
            card = tk.Frame(body, bg=CARD)
            card.pack(fill=X, padx=30, pady=8)

            photo = self.photo_manager.thumbnail(path, 320, 200)
            if photo:
                self.images.append(photo)
                tk.Label(
                    card,
                    image=photo,
                    bg=CARD,
                ).pack(side=LEFT, padx=12, pady=12)

            info = tk.Frame(card, bg=CARD)
            info.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=15)

            tk.Label(
                info,
                text=source["title"],
                bg=CARD,
                fg=TEXT,
                font=FONT_HEADING,
            ).pack(anchor="w")

            tk.Label(
                info,
                text=source["credit"],
                bg=CARD,
                fg=MUTED,
                font=FONT_SMALL,
                wraplength=650,
                justify=LEFT,
            ).pack(anchor="w", pady=(8, 5))

            tk.Label(
                info,
                text=source["source_page"],
                bg=CARD,
                fg=BLUE,
                font=FONT_SMALL,
                wraplength=650,
                justify=LEFT,
            ).pack(anchor="w")

    # ========================================================
    # 067 - GALLERY BACK
    # ========================================================

    def go_back_from_gallery(self):
        if not self.current_user:
            self.show_welcome()
        elif self.current_user["role"] == "admin":
            self.show_admin_dashboard()
        else:
            self.show_user_dashboard()

    # ========================================================
    # 068 - ADMIN DASHBOARD
    # ========================================================

    def show_admin_dashboard(self):
        if not self.current_user or self.current_user["role"] != "admin":
            self.show_admin_login()
            return

        frame = self.make_frame()

        top = tk.Frame(frame, bg=BG)
        top.pack(fill=X, padx=25, pady=(18, 8))

        left = tk.Frame(top, bg=BG)
        left.pack(side=LEFT)

        tk.Label(
            left,
            text="ADMIN CONTROL CENTER",
            bg=BG,
            fg=TEXT,
            font=FONT_HEADING,
        ).pack(anchor="w")

        tk.Label(
            left,
            text="Monitor reports and update emergency response status.",
            bg=BG,
            fg=MUTED,
            font=FONT_SMALL,
        ).pack(anchor="w")

        self.button(
            top,
            "LOG OUT",
            self.logout,
            "danger",
        ).pack(side=RIGHT)

        stats = tk.Frame(frame, bg=BG)
        stats.pack(fill=X, padx=25, pady=8)

        stats_data = [
            ("TOTAL REPORTS", self.db.count_reports(), RED),
            ("PENDING", self.db.count_status(STATUS_PENDING), YELLOW),
            ("IN PROGRESS", self.db.count_status(STATUS_IN_PROGRESS), BLUE),
            ("RESOLVED", self.db.count_status(STATUS_RESOLVED), GREEN),
            ("USERS", self.db.count_users(), WHITE),
        ]

        for title, value, fg in stats_data:
            card = tk.Frame(stats, bg=CARD)
            card.pack(side=LEFT, fill=BOTH, expand=True, padx=4)
            tk.Label(
                card,
                text=title,
                bg=CARD,
                fg=MUTED,
                font=FONT_SMALL,
            ).pack(pady=(12, 2))
            tk.Label(
                card,
                text=str(value),
                bg=CARD,
                fg=fg,
                font=FONT_BIG_NUMBER,
            ).pack(pady=(0, 12))

        actions = tk.Frame(frame, bg=BG)
        actions.pack(fill=X, padx=25, pady=8)

        self.button(
            actions,
            "VIEW / UPDATE REPORTS",
            self.show_admin_reports,
            "danger",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            actions,
            "EMERGENCY HELP",
            self.show_help,
            "accent",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            actions,
            "PHOTO GALLERY",
            self.show_photo_gallery,
            "accent",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            actions,
            "EXPORT CSV",
            self.export_reports,
            "success",
        ).pack(side=LEFT)

        info = tk.Frame(frame, bg=PANEL)
        info.pack(fill=BOTH, expand=True, padx=25, pady=12)

        tk.Label(
            info,
            text="Administrator responsibilities",
            bg=PANEL,
            fg=TEXT,
            font=FONT_HEADING,
        ).pack(anchor="w", padx=20, pady=(20, 8))

        responsibilities = [
            "Review new reports promptly.",
            "Verify information before dispatching responders.",
            "Update the status as the response progresses.",
            "Add useful notes that explain the latest action.",
            "Use emergency phone numbers for immediate real-world emergencies.",
            "Do not expose administrator credentials to ordinary users.",
        ]

        for item in responsibilities:
            tk.Label(
                info,
                text="• " + item,
                bg=PANEL,
                fg=MUTED,
                font=FONT_BODY,
                anchor="w",
            ).pack(fill=X, padx=25, pady=4)

    # ========================================================
    # 069 - ADMIN REPORTS
    # ========================================================

    def show_admin_reports(self):
        if not self.current_user or self.current_user["role"] != "admin":
            self.show_admin_login()
            return

        frame = self.make_frame()
        self.add_title(
            frame,
            "Emergency Reports Management",
            "Select a report to inspect it and change its response status.",
        )

        toolbar = tk.Frame(frame, bg=BG)
        toolbar.pack(fill=X, padx=25, pady=8)

        search_var = tk.StringVar()
        status_var = tk.StringVar(value="All")

        tk.Label(
            toolbar,
            text="Search:",
            bg=BG,
            fg=MUTED,
            font=FONT_BODY,
        ).pack(side=LEFT, padx=(0, 6))

        search_entry = ttk.Entry(toolbar, textvariable=search_var, width=28)
        search_entry.pack(side=LEFT, padx=(0, 8))

        tk.Label(
            toolbar,
            text="Status:",
            bg=BG,
            fg=MUTED,
            font=FONT_BODY,
        ).pack(side=LEFT, padx=(8, 6))

        status_combo = ttk.Combobox(
            toolbar,
            textvariable=status_var,
            values=["All"] + STATUS_VALUES,
            state="readonly",
            width=18,
        )
        status_combo.pack(side=LEFT, padx=(0, 8))

        tree_frame = tk.Frame(frame, bg=BG)
        tree_frame.pack(fill=BOTH, expand=True, padx=25, pady=8)

        columns = (
            "id",
            "name",
            "type",
            "location",
            "phone",
            "status",
            "created",
        )

        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = {
            "id": "ID",
            "name": "Reporter",
            "type": "Type",
            "location": "Location",
            "phone": "Phone",
            "status": "Status",
            "created": "Created",
        }

        widths = {
            "id": 60,
            "name": 150,
            "type": 150,
            "location": 220,
            "phone": 130,
            "status": 140,
            "created": 155,
        }

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w")

        scroll_y = ttk.Scrollbar(
            tree_frame,
            orient=VERTICAL,
            command=tree.yview,
        )
        tree.configure(yscrollcommand=scroll_y.set)

        tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll_y.pack(side=RIGHT, fill=Y)

        def load_rows():
            for item in tree.get_children():
                tree.delete(item)

            reports = self.db.search_reports(
                search_var.get(),
                status_var.get(),
            )

            for report in reports:
                tree.insert(
                    "",
                    END,
                    values=(
                        report["id"],
                        report["name"],
                        report["emergency_type"],
                        report["location"],
                        report["phone"],
                        report["status"],
                        report["created_at"],
                    ),
                )

        self.button(
            toolbar,
            "SEARCH",
            load_rows,
            "accent",
        ).pack(side=LEFT)

        self.button(
            toolbar,
            "RESET",
            lambda: (
                search_var.set(""),
                status_var.set("All"),
                load_rows(),
            ),
            "accent",
        ).pack(side=LEFT, padx=5)

        self.button(
            toolbar,
            "DASHBOARD",
            self.show_admin_dashboard,
            "success",
        ).pack(side=RIGHT)

        def open_selected(_event=None):
            selected = tree.selection()
            if not selected:
                return
            values = tree.item(selected[0], "values")
            if values:
                self.show_admin_report_editor(int(values[0]))

        tree.bind("<Double-1>", open_selected)
        status_combo.bind("<<ComboboxSelected>>", lambda _event: load_rows())
        search_entry.bind("<Return>", lambda _event: load_rows())

        load_rows()

        tk.Label(
            frame,
            text="Double-click a row to change the report status.",
            bg=BG,
            fg=MUTED,
            font=FONT_SMALL,
        ).pack(anchor="w", padx=25, pady=4)

    # ========================================================
    # 070 - ADMIN REPORT EDITOR
    # ========================================================

    def show_admin_report_editor(self, report_id):
        report = self.db.get_report(report_id)
        if report is None:
            messagebox.showerror("Not Found", "Report not found.")
            return

        frame = self.make_frame()
        self.add_title(
            frame,
            f"Manage Report #{report_id}",
            "Authorized administrators can update the response status and note.",
        )

        body = self.scrollable(frame)

        detail_card = tk.Frame(body, bg=CARD)
        detail_card.pack(fill=X, padx=60, pady=10)

        fields = [
            ("Reporter", report["name"]),
            ("Phone", report["phone"]),
            ("Emergency type", report["emergency_type"]),
            ("Location", report["location"]),
            ("Current status", report["status"]),
            ("Created", report["created_at"]),
            ("Description", report["description"]),
        ]

        for label, value in fields:
            row = tk.Frame(detail_card, bg=CARD)
            row.pack(fill=X, padx=20, pady=7)

            tk.Label(
                row,
                text=label,
                bg=CARD,
                fg=MUTED,
                font=FONT_BODY,
                width=18,
                anchor="nw",
            ).pack(side=LEFT)

            tk.Label(
                row,
                text=value,
                bg=CARD,
                fg=TEXT,
                font=FONT_BODY,
                wraplength=780,
                justify=LEFT,
                anchor="w",
            ).pack(side=LEFT, fill=X, expand=True)

        editor = tk.Frame(body, bg=PANEL)
        editor.pack(fill=X, padx=60, pady=15)

        tk.Label(
            editor,
            text="Update Response",
            bg=PANEL,
            fg=TEXT,
            font=FONT_HEADING,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        status_var = tk.StringVar(value=report["status"])

        status_row = tk.Frame(editor, bg=PANEL)
        status_row.pack(fill=X, padx=20, pady=6)

        tk.Label(
            status_row,
            text="New status",
            bg=PANEL,
            fg=TEXT,
            font=FONT_BODY,
            width=18,
            anchor="w",
        ).pack(side=LEFT)

        status_combo = ttk.Combobox(
            status_row,
            textvariable=status_var,
            values=STATUS_VALUES,
            state="readonly",
        )
        status_combo.pack(side=LEFT, fill=X, expand=True)

        tk.Label(
            editor,
            text="Administrator note",
            bg=PANEL,
            fg=TEXT,
            font=FONT_BODY,
        ).pack(anchor="w", padx=20, pady=(15, 5))

        note = tk.Text(
            editor,
            height=6,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            wrap="word",
            font=FONT_BODY,
        )
        note.pack(fill=X, padx=20)

        if report["admin_note"]:
            note.insert("1.0", report["admin_note"])

        def save():
            new_status = status_var.get()
            admin_note = note.get("1.0", END).strip()

            if new_status not in STATUS_VALUES:
                messagebox.showerror(
                    "INVALID",
                    "INVALID: choose a valid response status.",
                )
                return

            if len(admin_note) > 1000:
                messagebox.showerror(
                    "INVALID",
                    "INVALID: administrator note cannot exceed 1000 characters.",
                )
                return

            if new_status == report["status"] and admin_note == (report["admin_note"] or ""):
                messagebox.showinfo(
                    "No Changes",
                    "No changes were made.",
                )
                return

            confirm = messagebox.askyesno(
                "Confirm Status Change",
                (
                    f"Change report #{report_id} status from "
                    f"'{report['status']}' to '{new_status}'?"
                ),
            )
            if not confirm:
                return

            success = self.db.update_status(
                report_id,
                new_status,
                admin_note,
                self.current_user["username"],
            )

            if not success:
                messagebox.showerror(
                    "Error",
                    "The report could not be updated.",
                )
                return

            self.db.log(
                self.current_user["username"],
                f"Updated emergency report #{report_id} to {new_status}",
            )

            messagebox.showinfo(
                "Updated",
                f"Report #{report_id} has been updated.",
            )
            self.show_admin_reports()

        buttons = tk.Frame(editor, bg=PANEL)
        buttons.pack(fill=X, padx=20, pady=18)

        self.button(
            buttons,
            "SAVE STATUS CHANGE",
            save,
            "success",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            buttons,
            "VIEW FULL HISTORY",
            lambda: self.show_admin_history(report_id),
            "accent",
        ).pack(side=LEFT, padx=(0, 8))

        self.button(
            buttons,
            "BACK",
            self.show_admin_reports,
            "danger",
        ).pack(side=LEFT)

    # ========================================================
    # 071 - ADMIN HISTORY
    # ========================================================

    def show_admin_history(self, report_id):
        report = self.db.get_report(report_id)
        if not report:
            messagebox.showerror("Not Found", "Report not found.")
            return

        frame = self.make_frame()
        self.add_title(
            frame,
            f"Response History • Report #{report_id}",
            "Every status change is recorded in the local database.",
        )

        body = self.scrollable(frame)
        history = self.db.get_history(report_id)

        if not history:
            tk.Label(
                body,
                text="No history available.",
                bg=BG,
                fg=MUTED,
                font=FONT_BODY,
            ).pack(pady=40)
        else:
            for item in history:
                card = tk.Frame(body, bg=CARD)
                card.pack(fill=X, padx=60, pady=6)

                tk.Label(
                    card,
                    text=item["new_status"],
                    bg=CARD,
                    fg=GREEN if item["new_status"] == STATUS_RESOLVED else YELLOW,
                    font=FONT_CARD,
                    width=18,
                    anchor="w",
                ).pack(side=LEFT, padx=15, pady=15)

                information = (
                    f"Changed by: {item['changed_by']}\n"
                    f"Time: {item['changed_at']}\n"
                    f"Previous status: {item['old_status'] or 'None'}\n"
                    f"Note: {item['note'] or 'No note'}"
                )

                tk.Label(
                    card,
                    text=information,
                    bg=CARD,
                    fg=TEXT,
                    font=FONT_SMALL,
                    justify=LEFT,
                    anchor="w",
                ).pack(side=LEFT, fill=X, expand=True, padx=10, pady=15)

        bottom = tk.Frame(frame, bg=BG)
        bottom.pack(fill=X, padx=60, pady=12)

        self.button(
            bottom,
            "BACK TO REPORT",
            lambda: self.show_admin_report_editor(report_id),
            "accent",
        ).pack(side=LEFT)

    # ========================================================
    # 072 - EXPORT REPORTS
    # ========================================================

    def export_reports(self):
        if not self.current_user or self.current_user["role"] != "admin":
            self.show_admin_login()
            return

        reports = self.db.get_all_reports()
        if not reports:
            messagebox.showinfo(
                "Export",
                "There are no reports to export.",
            )
            return

        ensure_directories()

        default_name = (
            f"emergency_reports_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        path = filedialog.asksaveasfilename(
            title="Export emergency reports",
            initialdir=str(EXPORT_DIR),
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )

        if not path:
            return

        fields = [
            "id",
            "account_username",
            "name",
            "location",
            "phone",
            "emergency_type",
            "description",
            "status",
            "admin_note",
            "created_at",
            "updated_at",
        ]

        try:
            with open(
                path,
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for report in reports:
                    writer.writerow(
                        {field: report.get(field, "") for field in fields}
                    )

            self.db.log(
                self.current_user["username"],
                f"Exported {len(reports)} reports to CSV",
            )

            messagebox.showinfo(
                "Export Complete",
                f"{len(reports)} reports were exported successfully.",
            )
        except Exception as exc:
            messagebox.showerror(
                "Export Error",
                f"Could not export reports:\n{exc}",
            )

    # ========================================================
    # 073 - LOGOUT
    # ========================================================

    def logout(self):
        if self.current_user:
            self.db.log(
                self.current_user["username"],
                "Logged out",
            )
        self.current_user = None
        self.show_welcome()

    # ========================================================
    # 074 - CLOSE
    # ========================================================

    def on_close(self):
        try:
            self.root.destroy()
        except Exception:
            pass


# ============================================================
# 075 - EXTRA VALIDATION HELPERS
# ============================================================

def is_reasonable_text(value, minimum=1, maximum=500):
    value = clean_text(value)
    if not value:
        return False
    if len(value) < minimum:
        return False
    if len(value) > maximum:
        return False
    return bool(re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", value))


# ============================================================
# 076 - PHONE DISPLAY HELPER
# ============================================================

def display_phone(value):
    value = normalize_phone(value)
    if value.startswith("+251"):
        return value
    if value.startswith("251"):
        return "+" + value
    return value


# ============================================================
# 077 - STATUS COLOR HELPER
# ============================================================

def status_color(status):
    mapping = {
        STATUS_PENDING: YELLOW,
        STATUS_REVIEWING: ORANGE,
        STATUS_DISPATCHED: BLUE,
        STATUS_IN_PROGRESS: BLUE,
        STATUS_RESOLVED: GREEN,
        STATUS_CANCELLED: "#888888",
    }
    return mapping.get(status, TEXT)


# ============================================================
# 078 - DATABASE BACKUP HELPER
# ============================================================

def backup_database():
    """Create a timestamped SQLite backup file."""
    ensure_directories()
    backup_name = (
        f"emergency_backup_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    )
    destination = DATA_DIR / backup_name

    source = sqlite3.connect(str(DB_FILE))
    target = sqlite3.connect(str(destination))

    try:
        source.backup(target)
    finally:
        target.close()
        source.close()

    return destination


# ============================================================
# 079 - DATABASE INTEGRITY HELPER
# ============================================================

def check_database_integrity():
    """Return True when SQLite reports a healthy database."""
    try:
        with sqlite3.connect(str(DB_FILE)) as connection:
            row = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()
            return bool(row and row[0] == "ok")
    except Exception:
        return False


# ============================================================
# 080 - CREATE SAMPLE DATA OPTION
# ============================================================

def create_sample_data_if_requested(db):
    """
    Deliberately disabled by default.
    Keeping sample reports out of the database avoids fake emergency reports.
    """
    return False


# ============================================================
# 081 - APPLICATION START
# ============================================================

def main():
    ensure_directories()

    root = tk.Tk()
    app = EmergencyApp(root)

    # Keep a reference so some Python environments do not optimize it away.
    root.emergency_app = app

    root.mainloop()


# ============================================================
# 082 - SAFE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()


# ============================================================
# 083 - PROJECT NOTES
# ============================================================
#
# The following documentation is intentionally included in the source file
# so that the project remains easy to understand when it is submitted as
# a school or college programming project.
#
# RUNNING
# -------
# 1. Install/use Python 3 with Tkinter (Tkinter is normally included with
#    the standard Windows Python installer).
# 2. Save this file as:
#       emergency_management_system.py
# 3. Open it in VS Code.
# 4. Run:
#       python emergency_management_system.py
#
# NO pip install is required. No third-party Python package is used.
# The photo gallery uses GIF/PNG images directly through Tkinter.
#
# DATABASE
# --------
# The SQLite database is created automatically in the user-writable folder:
#       ~/EthiopianEmergencySystem/emergency_system.db
#
# PHOTO CACHE
# -----------
# Downloaded photographs are stored at:
#       ~/EthiopianEmergencySystem/emergency_photos/
#
# CSV EXPORTS
# -----------
# Exported CSV files can be stored at:
#       emergency_data/exports/
#
# ADMIN
# -----
# The initial administrator username is:
#       admin
#
# The administrator password is configured internally as:
#       102030
#
# The password is intentionally not printed, displayed, hinted at, or placed
# on the public front page. The admin login screen uses a masked password box.
#
# SECURITY
# --------
# This is an educational local application. SHA-256 is used here to avoid
# storing ordinary user passwords as readable text. For production systems,
# use a password hashing algorithm designed for passwords such as Argon2,
# bcrypt or scrypt, add account lockout, use TLS, and place the database
# behind an authenticated server.
#
# EMERGENCY REPORT VALIDATION
# ---------------------------
# The system checks:
#       - Name
#       - Location
#       - Ethiopian-style phone number
#       - Emergency type
#       - Description
#
# Invalid input is rejected before the database insert.
#
# ADMIN STATUS WORKFLOW
# ---------------------
# Pending
#     -> Under Review
#     -> Dispatched
#     -> In Progress
#     -> Resolved
#
# Cancellation is also available when appropriate.
#
# Every status update creates a row in status_history.
#
# REAL PHOTO SOURCES
# ------------------
# The gallery uses Wikimedia Commons source pages listed in PHOTO_SOURCES.
# These photographs are real photographs, not AI-generated illustrations.
# Their credits are displayed in the gallery.
#
# FRONT PAGE
# ----------
# The front page is designed to resemble the emergency/fire visual style
# shown in the reference screenshot: dark background, emergency-red accents,
# large emergency messaging and a large photo area.
#
# The application does not copy the Google interface and does not expose
# unrelated search results.
#
# ETHIOPIAN EMERGENCY CONTACTS
# ----------------------------
# General emergency: 911
# Police: 991
# Ambulance: 907
# Fire & Rescue: 939
# Traffic Police: 945
# Federal Police: 916
#
# These values should be reviewed locally before deployment because emergency
# contact arrangements can vary by location and can change.
#
# IMPORTANT USER EXPERIENCE RULE
# ------------------------------
# An application report is NOT a replacement for calling emergency services.
# The report feature is intended for emergency-management workflow, tracking,
# and educational demonstration.
#
# END OF DOCUMENTATION
# ============================================================


# ============================================================
# 084 - EXTENDED PROJECT DOCUMENTATION
# ============================================================
#
# TABLE OF CONTENTS
# -----------------
# A. Project purpose
# B. User workflow
# C. Administrator workflow
# D. Data model
# E. Validation model
# F. Photo model
# G. Safety considerations
# H. Testing checklist
#
# A. PROJECT PURPOSE
# ------------------
# This program demonstrates how a desktop application can combine a graphical
# user interface, authentication, persistent storage, validation and an
# administrator workflow into one coherent emergency-management project.
#
# The system intentionally keeps the public interface simple. A new visitor
# sees the application title, emergency visual, user-account controls and
# emergency-help entry point. Administrator credentials are not printed on
# that page.
#
# B. USER WORKFLOW
# ----------------
# Step 1:
#     Open the application.
#
# Step 2:
#     Select CREATE USER ACCOUNT.
#
# Step 3:
#     Enter full name, phone, username and password.
#
# Step 4:
#     The program validates each field.
#
# Step 5:
#     After successful registration, return to USER LOGIN.
#
# Step 6:
#     Sign in.
#
# Step 7:
#     The user dashboard provides:
#         Emergency Help
#         Report Emergency
#         My Reports
#         Photo Gallery
#
# Step 8:
#     The report form requests:
#         Name
#         Location
#         Phone number
#         Emergency type
#         Description
#
# Step 9:
#     If information is inappropriate, the program displays INVALID and
#     refuses to save the report.
#
# Step 10:
#     A valid report is inserted into SQLite with Pending status.
#
# C. ADMINISTRATOR WORKFLOW
# -------------------------
# Step 1:
#     Select ADMIN LOGIN.
#
# Step 2:
#     Enter authorized administrator credentials.
#
# Step 3:
#     The administrator sees dashboard statistics.
#
# Step 4:
#     Open VIEW / UPDATE REPORTS.
#
# Step 5:
#     Search or filter emergency reports.
#
# Step 6:
#     Double-click a report.
#
# Step 7:
#     Choose a new status.
#
# Step 8:
#     Add an optional administrator note.
#
# Step 9:
#     Save the change.
#
# Step 10:
#     The system writes the status change to status_history.
#
# D. DATA MODEL
# -------------
# users
#     id
#     full_name
#     phone
#     username
#     password_hash
#     role
#     created_at
#
# emergencies
#     id
#     user_id
#     name
#     location
#     phone
#     emergency_type
#     description
#     status
#     admin_note
#     created_at
#     updated_at
#
# status_history
#     id
#     emergency_id
#     old_status
#     new_status
#     note
#     changed_by
#     changed_at
#
# app_logs
#     id
#     username
#     action
#     created_at
#
# E. VALIDATION MODEL
# -------------------
# The application should reject:
#     Empty required fields.
#     Very short names.
#     Names containing numbers.
#     Phone numbers with an unsupported structure.
#     Invalid usernames.
#     Weakly sized passwords.
#     Password confirmation mismatches.
#     Empty locations.
#     Symbol-only locations.
#     Very short descriptions.
#     Symbol-only descriptions.
#     Unknown emergency types.
#     Unknown status values.
#
# The validation is performed before database writes.
#
# F. PHOTO MODEL
# --------------
# The application does not package copyrighted web images into the Python
# source. Instead, it downloads selected Wikimedia Commons photographs at
# runtime and stores them in the local photo cache.
#
# This makes the source code easier to copy and keeps attribution information
# beside each image source.
#
# The application should have internet access the first time the gallery is
# opened if the user wants fresh photographs.
#
# G. SAFETY CONSIDERATIONS
# ------------------------
# Never use a demonstration emergency number as a substitute for local
# emergency guidance without checking current official information.
#
# Do not submit fake reports to emergency services.
#
# Do not enter another person's private information without permission.
#
# Do not use this educational prototype as a dispatch system for real-world
# emergency operations without professional security, availability,
# authentication, auditing, redundancy, encryption and legal review.
#
# H. TESTING CHECKLIST
# --------------------
# Test 1:
#     Start application with an empty data directory.
#
# Expected:
#     Database and folders are created automatically.
#
# Test 2:
#     Open front page.
#
# Expected:
#     Administrator password is not shown.
#
# Test 3:
#     Register with a number in the name.
#
# Expected:
#     INVALID message.
#
# Test 4:
#     Register with an invalid phone number.
#
# Expected:
#     INVALID message.
#
# Test 5:
#     Register with mismatched passwords.
#
# Expected:
#     INVALID message.
#
# Test 6:
#     Register correctly.
#
# Expected:
#     Account is saved.
#
# Test 7:
#     Login using correct user account.
#
# Expected:
#     User dashboard opens.
#
# Test 8:
#     Submit a short description such as "x".
#
# Expected:
#     INVALID message.
#
# Test 9:
#     Submit a valid emergency report.
#
# Expected:
#     New Pending report is created.
#
# Test 10:
#     Login as administrator.
#
# Expected:
#     Admin dashboard opens.
#
# Test 11:
#     Open report manager.
#
# Expected:
#     Submitted report appears.
#
# Test 12:
#     Change Pending to In Progress.
#
# Expected:
#     Status changes and history is recorded.
#
# Test 13:
#     Change status to Resolved.
#
# Expected:
#     Status changes and user can see the update.
#
# Test 14:
#     Export reports.
#
# Expected:
#     CSV file is created.
#
# Test 15:
#     Open photo gallery without internet.
#
# Expected:
#     Application stays usable and shows an empty cached-photo message.
#
# END EXTENDED DOCUMENTATION
# ============================================================


# ============================================================
# 085 - FUTURE DEVELOPMENT NOTES
# ============================================================
#
# Possible production improvements:
#
# 1. Use a server-side database such as PostgreSQL.
# 2. Add secure HTTPS API communication.
# 3. Add Argon2 password hashing.
# 4. Add email/SMS notifications.
# 5. Add map/GPS support.
# 6. Add role-based permissions beyond user/admin.
# 7. Add responder accounts.
# 8. Add image uploads for reports.
# 9. Add encrypted sensitive fields.
# 10. Add automatic database backups.
# 11. Add audit log viewer.
# 12. Add Amharic and Afaan Oromo localization.
# 13. Add accessibility features.
# 14. Add automated tests.
# 15. Add structured API validation.
# 16. Add offline-first synchronization.
# 17. Add duplicate-report detection.
# 18. Add report priority scoring.
# 19. Add regional emergency contact profiles.
# 20. Add professional dispatch integration.
#
# The current version deliberately focuses on a clean, understandable
# educational implementation that can be run locally with Python.
# ============================================================


# ============================================================
# 086 - EDUCATIONAL DISCLAIMER
# ============================================================
#
# This software is provided for educational and demonstration purposes.
# It is not certified emergency dispatch software.
#
# The author/operator should verify emergency contact information for the
# intended Ethiopian city or region before using this application in a real
# emergency workflow.
#
# In a life-threatening situation, call the appropriate emergency service.
#
# ============================================================


# ============================================================
# 087 - END
# ============================================================
#
# Thank you for using the Ethiopian Emergency Management & Response System.
#
# ============================================================
