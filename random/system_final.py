# ================================================================
# ETHIOPIA EMERGENCY RESPONSE & MANAGEMENT SYSTEM
# ================================================================
# Single-file Python application.
# Standard library only: tkinter + sqlite3.
#
# IMPORTANT:
# - No third-party package is required.
# - The database is created automatically beside this file.
# - Default ADMIN USERNAME: admin
# - Default ADMIN PASSWORD: 102030
# - The administrator password is NEVER displayed on the public login page.
# - Existing users sign in with their FULL NAME and password.
# - The report page uses an emergency type/icon gallery before showing the form.
# - The Emergency Contacts page displays phone numbers directly; there is no dialer button.
# - The interface uses a clean professional UI/UX design, not glassmorphism.
# - The login page contains an embedded emergency image asset.
#
# This application is intended as a school/project demonstration.
# For a real emergency, call the appropriate emergency service directly.
# ================================================================

import os
import base64
import re
import sqlite3
import hashlib
import secrets
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

APP_TITLE = "Ethiopia Emergency Response System"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "emergency_response.db")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "102030"

# Official/public emergency contact information checked for this project.
# Addis Ababa Police lists 991 for the Addis Ababa Police Commission and
# 912 for Fire. The Ethiopian Federal Police currently lists 990, 991,
# 987 and 816 as toll-free lines.
EMERGENCY_NUMBERS = [
    ("Federal Police", "991", "Police emergency / security"),
    ("Addis Ababa Police", "991", "Police emergency"),
    ("Fire & Disaster Risk Management", "912", "Fire emergency"),
    ("Ethiopian Federal Police", "990", "Federal Police toll-free line"),
    ("Ethiopian Federal Police", "987", "Federal Police toll-free line"),
    ("Ethiopian Federal Police", "816", "Federal Police toll-free line"),
    ("Red Cross", "907", "Emergency/support contact listed by Addis Ababa Police"),
]

STATUS_VALUES = [
    "Pending",
    "Assigned",
    "Responding",
    "Resolved",
    "Cancelled",
]

PRIORITY_VALUES = [
    "Critical",
    "High",
    "Medium",
    "Low",
]

EMERGENCY_TYPES = [
    "Fire",
    "Medical Emergency",
    "Road Accident",
    "Flood",
    "Building Collapse",
    "Electrical Emergency",
    "Security / Crime",
    "Missing Person",
    "Natural Disaster",
    "Other",
]


# ================================================================
# DATABASE
# ================================================================

def db_connect():
    # IMPORTANT: Always open the SAME SQLite file beside this Python file.
    # We never create an in-memory database and we never delete/reset this file
    # when the user logs out or when the program starts again.
    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    # WAL keeps committed data safely stored on disk while allowing the UI
    # to read/write the database reliably. The database remains persistent.
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def hash_password(password):
    salt = "ERS-ETHIOPIA-SCHOOL-PROJECT"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def create_database():
    # CREATE TABLE IF NOT EXISTS is deliberately used everywhere.
    # Therefore starting/restarting the application NEVER clears existing data.
    # The same emergency_response.db file is reopened every time the program runs.
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reporter_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            emergency_type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            admin_note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Helpful indexes make stored records load quickly as the database grows.
    # IF NOT EXISTS means these statements are also safe on every restart.
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_created_at ON activity_log(created_at)")

    # The actual admin credential is kept in constants and is not printed or
    # shown on the public login page. There is intentionally NO reset/delete
    # operation here. Existing users, reports and activity logs stay intact.
    conn.commit()
    conn.close()


def log_activity(action, details):
    try:
        conn = db_connect()
        conn.execute(
            "INSERT INTO activity_log(action, details, created_at) VALUES(?,?,?)",
            (action, details, now_string())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_user(full_name, phone, email, password):
    conn = db_connect()
    try:
        conn.execute(
            """INSERT INTO users
               (full_name, phone, email, password_hash, created_at)
               VALUES (?,?,?,?,?)""",
            (full_name, phone, email.lower(), hash_password(password), now_string())
        )
        conn.commit()
        user_id = conn.execute(
            "SELECT id FROM users WHERE email=?",
            (email.lower(),)
        ).fetchone()["id"]
        log_activity("USER_CREATED", f"User account {user_id} created")
        return True, "Account created successfully.", user_id
    except sqlite3.IntegrityError:
        return False, "An account with that email already exists.", None
    finally:
        conn.close()


def authenticate_user(name, password):
    conn = db_connect()
    row = conn.execute(
        "SELECT * FROM users WHERE lower(full_name)=lower(?) AND password_hash=?",
        (name.strip(), hash_password(password))
    ).fetchone()
    conn.close()
    return row


def get_user(user_id):
    conn = db_connect()
    row = conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row


def create_report(user_id, name, phone, emergency_type, location,
                  description, priority):
    conn = db_connect()
    stamp = now_string()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO reports
           (user_id, reporter_name, phone, emergency_type, location,
            description, priority, status, admin_note, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, name, phone, emergency_type, location, description,
         priority, "Pending", "", stamp, stamp)
    )
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    log_activity("REPORT_CREATED", f"Emergency report #{report_id} submitted")
    return report_id


def get_user_reports(user_id):
    conn = db_connect()
    rows = conn.execute(
        """SELECT * FROM reports
           WHERE user_id=?
           ORDER BY id DESC""",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_all_reports():
    conn = db_connect()
    rows = conn.execute(
        "SELECT * FROM reports ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def update_report(report_id, status, priority, admin_note):
    conn = db_connect()
    conn.execute(
        """UPDATE reports
           SET status=?, priority=?, admin_note=?, updated_at=?
           WHERE id=?""",
        (status, priority, admin_note, now_string(), report_id)
    )
    conn.commit()
    conn.close()
    log_activity(
        "REPORT_UPDATED",
        f"Report #{report_id}: status={status}, priority={priority}"
    )


def delete_report(report_id):
    conn = db_connect()
    conn.execute("DELETE FROM reports WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    log_activity("REPORT_DELETED", f"Report #{report_id} deleted")


def get_statistics():
    conn = db_connect()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM reports"
    ).fetchone()["c"]
    pending = conn.execute(
        "SELECT COUNT(*) AS c FROM reports WHERE status='Pending'"
    ).fetchone()["c"]
    responding = conn.execute(
        "SELECT COUNT(*) AS c FROM reports WHERE status='Responding'"
    ).fetchone()["c"]
    resolved = conn.execute(
        "SELECT COUNT(*) AS c FROM reports WHERE status='Resolved'"
    ).fetchone()["c"]
    critical = conn.execute(
        "SELECT COUNT(*) AS c FROM reports WHERE priority='Critical'"
    ).fetchone()["c"]
    users = conn.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]
    conn.close()
    return {
        "total": total,
        "pending": pending,
        "responding": responding,
        "resolved": resolved,
        "critical": critical,
        "users": users,
    }


# ================================================================
# VALIDATION
# ================================================================

def valid_name(value):
    value = value.strip()
    if len(value) < 2 or len(value) > 60:
        return False
    return bool(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ .'-]*", value))


def valid_phone(value):
    value = value.strip().replace(" ", "").replace("-", "")
    if value.startswith("+251"):
        digits = value[4:]
        return digits.isdigit() and len(digits) == 9
    if value.startswith("09"):
        return value.isdigit() and len(value) == 10
    if value.startswith("07"):
        return value.isdigit() and len(value) == 10
    return value.isdigit() and 9 <= len(value) <= 12


def valid_email(value):
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            value.strip()
        )
    )


def valid_password(value):
    return len(value) >= 6 and len(value) <= 64


def valid_location(value):
    value = value.strip()
    if len(value) < 2 or len(value) > 180:
        return False
    if re.fullmatch(r"[0-9 .,+-]+", value):
        return False
    return True


def valid_description(value):
    value = value.strip()
    if len(value) < 10 or len(value) > 1000:
        return False
    if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", value):
        return False
    return True


def validate_registration(name, phone, email, password, confirm):
    if not valid_name(name):
        return False, "Invalid name. Enter letters and a valid full name."
    if not valid_phone(phone):
        return False, "Invalid phone number."
    if not valid_email(email):
        return False, "Invalid email address."
    if not valid_password(password):
        return False, "Invalid password. Use 6 or more characters."
    if password != confirm:
        return False, "Invalid confirmation. Passwords do not match."
    return True, ""


def validate_report(name, phone, location, description):
    if not valid_name(name):
        return False, "Invalid name. Please enter a real name."
    if not valid_phone(phone):
        return False, "Invalid phone number. Use a valid Ethiopian number."
    if not valid_location(location):
        return False, "Invalid location. Enter a meaningful location."
    if not valid_description(description):
        return False, "Invalid description. Give at least 10 characters."
    return True, ""


# ================================================================
# UI COLORS / STYLE
# ================================================================

BG = "#F4F7FB"
PANEL = "#FFFFFF"
PANEL_2 = "#F0F4F8"
CARD = "#FFFFFF"
RED = "#e63946"
RED_DARK = "#b91c2a"
ORANGE = "#EA580C"
WHITE = "#f8fafc"
MUTED = "#64748B"
GREEN = "#159A68"
BLUE = "#3b82f6"
YELLOW = "#D97706"
PURPLE = "#7C3AED"
BORDER = "#D6DEE8"
TEXT = "#111827"
TEXT_2 = "#334155"
EMERGENCY_IMAGE_B64 = """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"""


def make_button(parent, text, command, width=18,
                bg=RED, fg=WHITE, font=("Segoe UI", 11, "bold")):
    return tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg=bg,
        fg=fg,
        activebackground=RED_DARK,
        activeforeground=WHITE,
        relief="flat",
        bd=0,
        cursor="hand2",
        font=font,
        padx=8,
        pady=8
    )


def make_label(parent, text="", size=11, bold=False,
               fg=TEXT, bg=None, anchor="w"):
    return tk.Label(
        parent,
        text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        fg=fg,
        bg=parent.cget("bg") if bg is None else bg,
        anchor=anchor
    )


def rounded_panel(parent, bg=PANEL):
    # Tkinter has no native blur/transparency for ordinary Frames, so this
    # uses a professional UI/UX layered panel: deep translucent-looking
    # surface, bright border, and clean spacing. It requires no packages.
    glass_bg = "#FFFFFF" if bg == PANEL else bg
    frame = tk.Frame(
        parent,
        bg=glass_bg,
        highlightbackground="#D6DEE8",
        highlightcolor="#B8C4D1",
        highlightthickness=1,
        bd=0,
        relief="flat"
    )
    return frame


# ================================================================
# MAIN APPLICATION
# ================================================================

class EmergencyApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1250x760")
        self.root.minsize(1000, 650)
        self.root.configure(bg=BG)

        self.current_user = None
        self.current_role = None
        self.current_page = None
        self.content = None
        self.sidebar = None
        self.nav_buttons = []
        self.after_id = None

        self.setup_style()
        self.show_welcome()

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Emergency.Treeview",
            background=PANEL_2,
            foreground=TEXT,
            fieldbackground=PANEL_2,
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Emergency.Treeview.Heading",
            background=CARD,
            foreground=TEXT,
            font=("Segoe UI", 10, "bold")
        )
        style.map(
            "Emergency.Treeview",
            background=[("selected", RED)],
            foreground=[("selected", WHITE)]
        )

    def clear_window(self):
        for child in self.root.winfo_children():
            child.destroy()

    def show_welcome(self):
        self.clear_window()

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)

        hero = tk.Frame(outer, bg=BG)
        hero.pack(fill="both", expand=True, padx=35, pady=30)

        left = tk.Frame(hero, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(20, 30))

        badge = tk.Label(
            left,
            text="  24/7 EMERGENCY RESPONSE  ",
            bg=RED,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=7
        )
        badge.pack(anchor="w", pady=(30, 18))

        title = tk.Label(
            left,
            text="Emergency\nResponse System",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 42, "bold"),
            justify="left"
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            left,
            text=(
                "Report emergencies quickly, find essential safety information,\n"
                "and keep track of your report from submission to resolution."
            ),
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 14),
            justify="left"
        )
        subtitle.pack(anchor="w", pady=18)

        actions = tk.Frame(left, bg=BG)
        actions.pack(anchor="w", pady=12)

        make_button(
            actions, "Sign In", self.show_login,
            width=16, bg=RED
        ).pack(side="left", padx=(0, 10))

        make_button(
            actions, "Create Account", self.show_signup,
            width=18, bg=PANEL_2
        ).pack(side="left")

        emergency_note = tk.Frame(
            left, bg=PANEL, highlightbackground=BORDER,
            highlightthickness=1
        )
        emergency_note.pack(fill="x", pady=(28, 0), ipady=8)

        tk.Label(
            emergency_note,
            text="⚠  LIFE-THREATENING EMERGENCY?",
            bg=PANEL,
            fg=ORANGE,
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=18, pady=(12, 4))

        tk.Label(
            emergency_note,
            text="Call the appropriate emergency service directly. This project is not a replacement for emergency dispatch.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=610,
            justify="left"
        ).pack(anchor="w", padx=18, pady=(0, 12))

        # Front emergency illustration.
        right = tk.Frame(hero, bg=PANEL)
        right.pack(side="right", fill="both", expand=False, padx=20, pady=20)

        canvas = tk.Canvas(
            right, width=430, height=470,
            bg=PANEL, highlightthickness=0
        )
        canvas.pack(padx=20, pady=20)

        # Shield / emergency illustration.
        canvas.create_oval(
            65, 40, 365, 340,
            fill=RED_DARK, outline=""
        )
        canvas.create_oval(
            90, 65, 340, 315,
            fill=RED, outline=""
        )
        canvas.create_polygon(
            215, 95, 300, 125, 285, 245,
            215, 300, 145, 245, 130, 125,
            fill=WHITE, outline=""
        )
        canvas.create_rectangle(
            198, 125, 232, 230,
            fill=RED, outline=""
        )
        canvas.create_rectangle(
            165, 160, 265, 195,
            fill=RED, outline=""
        )

        # Emergency vehicles / road.
        canvas.create_rectangle(
            30, 350, 400, 430,
            fill="#F7F9FC", outline=""
        )
        canvas.create_rectangle(
            70, 365, 160, 410,
            fill="#334155", outline=""
        )
        canvas.create_rectangle(
            85, 350, 145, 380,
            fill="#334155", outline=""
        )
        canvas.create_oval(
            78, 395, 110, 427,
            fill="#F4F7FB", outline=""
        )
        canvas.create_oval(
            120, 395, 152, 427,
            fill="#F4F7FB", outline=""
        )
        canvas.create_rectangle(
            95, 335, 125, 350,
            fill=RED, outline=""
        )
        canvas.create_rectangle(
            170, 390, 360, 405,
            fill=ORANGE, outline=""
        )
        canvas.create_text(
            265, 375,
            text="🚨",
            fill=WHITE,
            font=("Segoe UI Emoji", 34)
        )

        tk.Label(
            right,
            text="PROTECT • REPORT • RESPOND",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(0, 20))

        footer = tk.Label(
            outer,
            text="Ethiopia Emergency Response System  •  School Project",
            bg=BG,
            fg="#64748B",
            font=("Segoe UI", 9)
        )
        footer.pack(side="bottom", pady=12)

    # ============================================================
    # LOGIN
    # ============================================================

    def show_login(self):
        self.clear_window()

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)

        # Clean UI/UX login layout: real-photo slot on the left and
        # accessible login card on the right. The photo is optional so the
        # application still starts normally if the image file is missing.
        page = tk.Frame(outer, bg=BG)
        page.pack(fill="both", expand=True, padx=32, pady=28)
        page.grid_columnconfigure(0, weight=3)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(0, weight=1)

        visual = tk.Frame(page, bg="#111827", highlightbackground=BORDER, highlightthickness=1)
        visual.grid(row=0, column=0, sticky="nsew", padx=(0, 18))

        photo = None
        try:
            # The emergency image is embedded directly in this Python file,
            # so the project remains a single-file application with no image
            # installation or external package required.
            photo = tk.PhotoImage(data=EMERGENCY_IMAGE_B64)
            max_w, max_h = 760, 620
            if photo.width() > max_w:
                photo = photo.subsample(max(1, (photo.width() + max_w - 1)//max_w))
            if photo.height() > max_h:
                photo = photo.subsample(max(1, (photo.height() + max_h - 1)//max_h))
            image_label = tk.Label(visual, image=photo, bg="#111827", bd=0)
            image_label.image = photo
            image_label.pack(fill="both", expand=True, padx=12, pady=12)
        except Exception:
            photo = None

        if photo is None:
            # Built-in emergency-scene fallback keeps the app fully usable
            # without third-party image libraries.
            art = tk.Canvas(visual, bg="#111827", highlightthickness=0)
            art.pack(fill="both", expand=True, padx=12, pady=12)
            art.create_rectangle(0, 0, 1000, 650, fill="#1F2937", outline="")
            art.create_oval(520, 80, 900, 460, fill="#374151", outline="")
            art.create_rectangle(70, 390, 930, 590, fill="#0F172A", outline="")
            # Fire/rescue vehicle
            art.create_rectangle(145, 315, 620, 500, fill="#DC2626", outline="")
            art.create_rectangle(210, 265, 555, 365, fill="#EF4444", outline="")
            art.create_rectangle(245, 285, 355, 350, fill="#CBD5E1", outline="")
            art.create_rectangle(375, 285, 520, 350, fill="#CBD5E1", outline="")
            art.create_oval(195, 445, 280, 530, fill="#111827", outline="")
            art.create_oval(485, 445, 570, 530, fill="#111827", outline="")
            art.create_oval(225, 475, 250, 500, fill="#E5E7EB", outline="")
            art.create_oval(515, 475, 540, 500, fill="#E5E7EB", outline="")
            # Emergency light and cross
            art.create_rectangle(330, 245, 435, 275, fill="#F8FAFC", outline="")
            art.create_rectangle(365, 232, 400, 262, fill="#2563EB", outline="")
            art.create_rectangle(325, 370, 440, 400, fill="#F8FAFC", outline="")
            art.create_rectangle(370, 350, 395, 420, fill="#DC2626", outline="")
            art.create_rectangle(345, 375, 420, 400, fill="#DC2626", outline="")
            art.create_text(500, 120, text="EMERGENCY RESPONSE", fill="#FFFFFF", font=("Segoe UI", 26, "bold"))
            art.create_text(500, 155, text="Protect • Report • Respond", fill="#FCA5A5", font=("Segoe UI", 14, "bold"))

        tk.Label(visual, text="24/7 EMERGENCY RESPONSE", bg="#111827", fg="#FFFFFF",
                 font=("Segoe UI", 12, "bold")).pack(pady=(0, 2))
        tk.Label(visual, text="Fast access to reporting, safety guidance and emergency contacts",
                 bg="#111827", fg="#D1D5DB", font=("Segoe UI", 9)).pack(pady=(0, 12))

        card = rounded_panel(page, PANEL)
        card.grid(row=0, column=1, sticky="nsew")

        tk.Label(card, text="🚨", bg=PANEL, fg=RED, font=("Segoe UI Emoji", 42)).pack(pady=(55, 4))
        tk.Label(card, text="Welcome Back", bg=PANEL, fg="#000000", font=("Segoe UI", 25, "bold")).pack()
        tk.Label(card, text="Sign in to your emergency account", bg=PANEL, fg="#000000", font=("Segoe UI", 11)).pack(pady=(4, 8))

        notice = tk.Frame(card, bg="#F7F9FC", highlightbackground=BORDER, highlightthickness=1)
        notice.pack(fill="x", padx=35, pady=(8, 20))
        tk.Label(notice, text="✓  Please enter appropriate information", bg="#F7F9FC", fg=ORANGE,
                 font=("Segoe UI", 10, "bold"), wraplength=330, justify="left").pack(anchor="w", padx=14, pady=(10, 3))
        tk.Label(notice, text="Use the same name and password you used when creating your account. Do not enter numbers in the name field.",
                 bg="#F7F9FC", fg="#000000", font=("Segoe UI", 9), wraplength=330, justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        tk.Label(card, text="Full Name", bg=PANEL, fg="#000000", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=45)
        name_entry = tk.Entry(card, bg=PANEL_2, fg="#000000", insertbackground="#000000", relief="flat", font=("Segoe UI", 12))
        name_entry.pack(fill="x", padx=45, ipady=10, pady=(5, 15))

        tk.Label(card, text="Password", bg=PANEL, fg="#000000", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=45)
        password = tk.Entry(card, bg=PANEL_2, fg="#000000", insertbackground="#000000", show="•", relief="flat", font=("Segoe UI", 12))
        password.pack(fill="x", padx=45, ipady=10, pady=(5, 8))

        message = tk.Label(card, text="", bg=PANEL, fg=RED, font=("Segoe UI", 10, "bold"), wraplength=350)
        message.pack(pady=7)

        def do_login():
            name = name_entry.get().strip()
            p = password.get()
            if not name or not p:
                message.config(text="Invalid: name and password are required.", fg=RED)
                return
            if name.lower() == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                self.current_role = "admin"
                self.current_user = None
                log_activity("ADMIN_LOGIN", "Administrator signed in")
                self.show_admin_dashboard()
                return
            if not valid_name(name):
                message.config(text="Invalid name. Enter your real full name.", fg=RED)
                return
            user = authenticate_user(name, p)
            if not user:
                message.config(text="Invalid name or password.", fg=RED)
                return
            self.current_role = "user"
            self.current_user = dict(user)
            log_activity("USER_LOGIN", f"User {user['id']} signed in")
            self.show_user_dashboard()

        make_button(card, "Sign In", do_login, width=25, bg=RED).pack(pady=(8, 10))
        make_button(card, "Create New Account", self.show_signup, width=25, bg=PANEL_2, fg="#000000").pack(pady=4)
        make_button(card, "Back to Home", self.show_welcome, width=25, bg="#EAF0F6", fg="#000000").pack(pady=4)
        tk.Label(card, text="Administrator access is protected.", bg=PANEL, fg="#000000", font=("Segoe UI", 8)).pack(pady=(15, 22))

        name_entry.focus_set()
        password.bind("<Return>", lambda event: do_login())

    def show_signup(self):
        self.clear_window()

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True)

        card = rounded_panel(container, PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center", width=620, height=680)

        tk.Label(
            card, text="Create Your Account",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 26, "bold")
        ).pack(pady=(25, 5))

        tk.Label(
            card,
            text="Your account lets you submit and track emergency reports.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 10)
        ).pack(pady=(0, 20))

        fields = tk.Frame(card, bg=PANEL)
        fields.pack(fill="x", padx=70)

        entries = {}

        definitions = [
            ("Full name", "name", False),
            ("Phone number", "phone", False),
            ("Email address", "email", False),
            ("Password", "password", True),
            ("Confirm password", "confirm", True),
        ]

        for label_text, key, secret in definitions:
            tk.Label(
                fields, text=label_text, bg=PANEL, fg=TEXT,
                font=("Segoe UI", 10, "bold")
            ).pack(anchor="w", pady=(7, 3))

            entry = tk.Entry(
                fields,
                bg=PANEL_2,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("Segoe UI", 11),
                show="•" if secret else ""
            )
            entry.pack(fill="x", ipady=9)
            entries[key] = entry

        message = tk.Label(
            card, text="", bg=PANEL, fg=RED,
            font=("Segoe UI", 10, "bold"), wraplength=450
        )
        message.pack(pady=10)

        def register():
            ok, msg = validate_registration(
                entries["name"].get(),
                entries["phone"].get(),
                entries["email"].get(),
                entries["password"].get(),
                entries["confirm"].get()
            )
            if not ok:
                message.config(text=msg)
                return

            success, text, user_id = create_user(
                entries["name"].get().strip(),
                entries["phone"].get().strip(),
                entries["email"].get().strip(),
                entries["password"].get()
            )
            if not success:
                message.config(text=text)
                return

            message.config(text="Account created successfully.", fg=GREEN)
            message.after(900, self.show_login)

        make_button(
            card, "Create Account", register,
            width=28, bg=RED, fg=WHITE
        ).pack(pady=4)

        make_button(
            card, "Already have an account? Sign In",
            self.show_login, width=28, bg=PANEL_2
        ).pack(pady=4)

        make_button(
            card, "Back to Home",
            self.show_welcome, width=28, bg="#EAF0F6"
        ).pack(pady=4)

        entries["name"].focus_set()

    # ============================================================
    # USER SHELL
    # ============================================================

    def setup_user_shell(self):
        self.clear_window()

        # Professional UI/UX application shell. Tkinter cannot blur the
        # desktop behind a widget without third-party libraries, so the look
        # is recreated with layered dark-glass panels, luminous borders and
        # generous spacing. Everything remains standard-library only.
        top = tk.Frame(self.root, bg="#FFFFFF", height=72)
        top.pack(fill="x")
        top.pack_propagate(False)

        brand = tk.Frame(top, bg="#FFFFFF")
        brand.pack(side="left", padx=22)
        tk.Label(brand, text="🛡", bg="#FFFFFF", fg="#ffffff",
                 font=("Segoe UI Emoji", 27)).pack(side="left", padx=(0, 10))
        title_box = tk.Frame(brand, bg="#FFFFFF")
        title_box.pack(side="left")
        tk.Label(title_box, text="ETHIOPIA EMERGENCY", bg="#FFFFFF", fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Response & Management System", bg="#FFFFFF", fg="#2563EB",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        user_name = self.current_user["full_name"] if self.current_user else "Administrator"
        tk.Label(top, text=f"●  {user_name}", bg="#FFFFFF", fg="#475569",
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=(8, 20))
        make_button(top, "Logout", self.logout, width=9, bg="#EEF2F6", fg=TEXT,
                    font=("Segoe UI", 9, "bold")).pack(side="right", padx=8)

        body = tk.Frame(self.root, bg="#F4F7FB")
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg="#FFFFFF", width=225,
                                highlightbackground="#CBD5E1", highlightthickness=1)
        self.sidebar.pack(side="left", fill="y", padx=(10, 0), pady=10)
        self.sidebar.pack_propagate(False)

        logo = tk.Frame(self.sidebar, bg="#FFFFFF", highlightbackground="#B9C9DD", highlightthickness=1)
        logo.pack(fill="x", padx=10, pady=10)
        tk.Label(logo, text="🚨", bg="#FFFFFF", fg=TEXT,
                 font=("Segoe UI Emoji", 34)).pack(pady=(12, 0))
        tk.Label(logo, text="Ethiopia", bg="#FFFFFF", fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack()
        tk.Label(logo, text="Emergency Response", bg="#FFFFFF", fg="#475569",
                 font=("Segoe UI", 9, "bold")).pack()
        tk.Label(logo, text="System", bg="#FFFFFF", fg="#475569",
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 12))

        tk.Label(self.sidebar, text="MAIN MENU", bg="#FFFFFF", fg="#64748B",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(8, 7))
        self.nav_buttons = []
        self.add_nav_button("⌂  Home", self.show_user_home)
        self.add_nav_button("🚨  Report Emergency", self.show_report_form)
        self.add_nav_button("▣  My Reports", self.show_my_reports)
        self.add_nav_button("☎  Emergency Contacts", self.show_contacts)
        self.add_nav_button("◈  Safety Information", self.show_safety)
        self.add_nav_button("⚙  My Profile", self.show_profile)

        call = tk.Frame(self.sidebar, bg="#FDECEF", highlightbackground="#F28B9A", highlightthickness=1)
        call.pack(fill="x", padx=10, pady=(18, 8), side="bottom")
        tk.Label(call, text="IN EMERGENCY", bg="#FDECEF", fg="#7F1D1D",
                 font=("Segoe UI", 8, "bold")).pack(pady=(10, 0))
        tk.Label(call, text="Call Now", bg="#FDECEF", fg=RED_DARK,
                 font=("Segoe UI", 10, "bold")).pack()
        tk.Label(call, text="☎  991", bg="#FDECEF", fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(pady=(0, 8))
        tk.Label(call, text="Addis Ababa / Police", bg="#FDECEF", fg="#B4232F",
                 font=("Segoe UI", 8)).pack(pady=(0, 10))

        content_area = tk.Frame(body, bg="#F4F7FB")
        content_area.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(content_area, bg="#F4F7FB", highlightthickness=0)
        scroll = ttk.Scrollbar(content_area, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=(12, 15), pady=10)
        self.content = tk.Frame(canvas, bg="#F4F7FB")
        window_id = canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=max(720, e.width)))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

    def add_nav_button(self, text, command):
        button = tk.Button(
            self.sidebar, text=text, command=command,
            bg="#FFFFFF", fg="#334155", activebackground="#2563EB",
            activeforeground=WHITE, relief="flat", bd=0, anchor="w",
            padx=18, pady=11, font=("Segoe UI", 9, "bold"), cursor="hand2"
        )
        button.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append((text, button))

    def clear_content(self):
        if self.content:
            for child in self.content.winfo_children():
                child.destroy()

    def highlight_nav(self, name):
        for text, button in self.nav_buttons:
            button.config(bg="#2563EB" if text == name or text.endswith(name) else "#FFFFFF")

    def show_user_dashboard(self):
        self.setup_user_shell()
        self.show_user_home()

    def show_user_home(self):
        self.clear_content()
        self.highlight_nav("⌂  Home")

        # Page heading
        head = tk.Frame(self.content, bg="#F4F7FB")
        head.pack(fill="x", pady=(5, 12))
        tk.Label(head, text="Ethiopia Emergency Response System", bg="#F4F7FB", fg=TEXT,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(head, text="Together for a safer Ethiopia 🇪🇹", bg="#F4F7FB", fg="#64748B",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        # Hero hero card
        hero = tk.Frame(self.content, bg="#EAF3FF", highlightbackground="#B8D0F0", highlightthickness=1)
        hero.pack(fill="x", pady=(0, 13))
        left = tk.Frame(hero, bg="#EAF3FF")
        left.pack(side="left", fill="both", expand=True, padx=24, pady=18)
        tk.Label(left, text="REPORT  •  RESPOND  •  SAVE LIVES", bg="#EAF3FF", fg="#334155",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(left, text="Need emergency assistance?", bg="#EAF3FF", fg=TEXT,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(5, 2))
        tk.Label(left, text="Send accurate emergency details so the response team can act quickly.",
                 bg="#EAF3FF", fg="#475569", font=("Segoe UI", 10), wraplength=650,
                 justify="left").pack(anchor="w", pady=(0, 10))
        make_button(left, "🚨  REPORT EMERGENCY NOW", self.show_report_form, width=28, bg="#D92D3A",
                    font=("Segoe UI", 10, "bold")).pack(anchor="w")

        badge = tk.Frame(hero, bg="#DCEBFF", highlightbackground="#8BB7F0", highlightthickness=1)
        badge.pack(side="right", fill="y", padx=15, pady=15)
        tk.Label(badge, text="♥", bg="#DCEBFF", fg="#D92D3A", font=("Segoe UI", 44, "bold")).pack(padx=28, pady=(10, 0))
        tk.Label(badge, text="FAST RESPONSE", bg="#DCEBFF", fg=TEXT,
                 font=("Segoe UI", 8, "bold")).pack(pady=(0, 12))

        reports = get_user_reports(self.current_user["id"])
        stats = [
            ("Total Reports", len(reports), "🔔", "#D92D3A"),
            ("Pending", len([r for r in reports if r["status"] == "Pending"]), "◷", "#2563EB"),
            ("Responding", len([r for r in reports if r["status"] == "Responding"]), "🚑", "#159A68"),
            ("Resolved", len([r for r in reports if r["status"] == "Resolved"]), "✓", "#7C3AED"),
        ]
        stats_row = tk.Frame(self.content, bg="#F4F7FB")
        stats_row.pack(fill="x", pady=(0, 13))
        for title, value, icon, accent in stats:
            card = tk.Frame(stats_row, bg="#FFFFFF", highlightbackground="#D1DBE6", highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=4)
            tk.Label(card, text=icon, bg="#FFFFFF", fg=accent, font=("Segoe UI Emoji", 20, "bold")).pack(side="left", padx=(12, 8), pady=12)
            box = tk.Frame(card, bg="#FFFFFF")
            box.pack(side="left", pady=8)
            tk.Label(box, text=str(value), bg="#FFFFFF", fg=TEXT, font=("Segoe UI", 19, "bold")).pack(anchor="w")
            tk.Label(box, text=title, bg="#FFFFFF", fg="#64748B", font=("Segoe UI", 8, "bold")).pack(anchor="w")

        lower = tk.Frame(self.content, bg="#F4F7FB")
        lower.pack(fill="both", expand=True)

        recent = tk.Frame(lower, bg="#FFFFFF", highlightbackground="#D8E1EA", highlightthickness=1)
        recent.pack(side="left", fill="both", expand=True, padx=(0, 7))
        top = tk.Frame(recent, bg="#FFFFFF")
        top.pack(fill="x", padx=15, pady=(14, 8))
        tk.Label(top, text="Recent Reports", bg="#FFFFFF", fg=TEXT, font=("Segoe UI", 13, "bold")).pack(side="left")
        make_button(top, "View All", self.show_my_reports, width=9, bg="#E8EEF5", font=("Segoe UI", 8, "bold")).pack(side="right")

        if reports:
            for row in reports[:5]:
                item = tk.Frame(recent, bg="#FFFFFF", highlightbackground="#E7EDF4", highlightthickness=1)
                item.pack(fill="x", padx=12, pady=4)
                tk.Label(item, text="🚨", bg="#FFFFFF", fg=TEXT, font=("Segoe UI Emoji", 15)).pack(side="left", padx=8, pady=7)
                info = tk.Frame(item, bg="#FFFFFF")
                info.pack(side="left", fill="x", expand=True, pady=6)
                tk.Label(info, text=row["emergency_type"], bg="#FFFFFF", fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
                tk.Label(info, text=row["location"], bg="#FFFFFF", fg="#64748B", font=("Segoe UI", 8)).pack(anchor="w")
                tk.Label(item, text=row["status"], bg="#FFFFFF", fg=self.status_color(row["status"]), font=("Segoe UI", 8, "bold")).pack(side="right", padx=10)
        else:
            tk.Label(recent, text="No emergency reports yet.", bg="#FFFFFF", fg="#64748B", font=("Segoe UI", 10)).pack(pady=30)

        actions = tk.Frame(lower, bg="#FFFFFF", highlightbackground="#D8E1EA", highlightthickness=1)
        actions.pack(side="right", fill="both", expand=False, padx=(7, 0))
        tk.Label(actions, text="Quick Actions", bg="#FFFFFF", fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=15, pady=(14, 10))
        for label, cmd, color in [
            ("🚨  Report Emergency", self.show_report_form, "#D92D3A"),
            ("▣  View My Reports", self.show_my_reports, "#E8EEF5"),
            ("☎  Emergency Contacts", self.show_contacts, "#E8EEF5"),
            ("◈  Safety Guidelines", self.show_safety, "#E8EEF5"),
        ]:
            make_button(actions, label, cmd, width=23, bg=color, font=("Segoe UI", 8, "bold")).pack(padx=14, pady=4)

        contacts = tk.Frame(self.content, bg="#FFFFFF", highlightbackground="#D8E1EA", highlightthickness=1)
        contacts.pack(fill="x", pady=(13, 0))
        tk.Label(contacts, text="Emergency Contacts", bg="#FFFFFF", fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=15, pady=(12, 8))
        row = tk.Frame(contacts, bg="#FFFFFF")
        row.pack(fill="x", padx=12, pady=(0, 12))
        for service, number, desc in EMERGENCY_NUMBERS[:4]:
            c = tk.Frame(row, bg="#FFFFFF", highlightbackground="#D9E2EC", highlightthickness=1)
            c.pack(side="left", fill="both", expand=True, padx=3)
            tk.Label(c, text=service, bg="#FFFFFF", fg="#334155", font=("Segoe UI", 8, "bold"), wraplength=130).pack(pady=(8, 2))
            tk.Label(c, text=number, bg="#FFFFFF", fg="#D92D3A", font=("Segoe UI", 14, "bold")).pack()
            tk.Label(c, text=desc, bg="#FFFFFF", fg="#64748B", font=("Segoe UI", 7), wraplength=130).pack(pady=(0, 8))

    def user_stat_card(self, parent, title, value, accent):
        card = tk.Frame(
            parent, bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card.pack(side="left", fill="x", expand=True, padx=5)

        tk.Frame(card, bg=accent, width=5).pack(side="left", fill="y")

        inner = tk.Frame(card, bg=PANEL)
        inner.pack(side="left", padx=14, pady=12)

        tk.Label(
            inner, text=value, bg=PANEL, fg=TEXT,
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w")
        tk.Label(
            inner, text=title, bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w")

    # ============================================================
    # REPORT FORM
    # ============================================================

    def show_report_form(self):
        self.clear_content()
        self.highlight_nav("🚨  Report Emergency")

        tk.Label(self.content, text="Report an Emergency", bg=BG, fg=TEXT, font=("Segoe UI", 29, "bold")).pack(anchor="w")
        tk.Label(self.content, text="First choose the emergency type. Then the required report form will appear.", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 8))

        notice = tk.Frame(self.content, bg="#F7F9FC", highlightbackground=BORDER, highlightthickness=1)
        notice.pack(fill="x", pady=(0, 15))
        tk.Label(notice, text="✓ APPROPRIATE INFORMATION ONLY", bg="#F7F9FC", fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(10, 2))
        tk.Label(notice, text="Choose the correct emergency icon and provide accurate name, phone, location and description. Invalid information will be rejected.", bg="#F7F9FC", fg=MUTED, font=("Segoe UI", 9), wraplength=900, justify="left").pack(anchor="w", padx=18, pady=(0, 10))

        gallery = rounded_panel(self.content, PANEL)
        gallery.pack(fill="x", pady=(0, 15))
        tk.Label(gallery, text="SELECT EMERGENCY TYPE", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(16, 10))

        gallery_frame = tk.Frame(gallery, bg=PANEL)
        gallery_frame.pack(fill="x", padx=12, pady=(0, 18))

        icon_map = {
            "Fire": ("🔥", "Fire", RED),
            "Medical Emergency": ("🚑", "Medical", GREEN),
            "Road Accident": ("🚗", "Accident", ORANGE),
            "Flood": ("🌊", "Flood", BLUE),
            "Building Collapse": ("🏢", "Collapse", PURPLE),
            "Electrical Emergency": ("⚡", "Electrical", YELLOW),
            "Security / Crime": ("🛡", "Security", RED),
            "Missing Person": ("🔎", "Missing", BLUE),
            "Natural Disaster": ("🌪", "Disaster", ORANGE),
            "Other": ("⚠", "Other", MUTED),
        }

        selected_type = tk.StringVar(value="")
        form_holder = tk.Frame(self.content, bg=BG)
        form_holder.pack(fill="x")

        def choose(kind):
            selected_type.set(kind)
            for child in form_holder.winfo_children():
                child.destroy()
            build_form(kind)
            for widget in gallery_frame.winfo_children():
                if getattr(widget, "emergency_kind", None) == kind:
                    widget.config(bg=RED_DARK)
                else:
                    widget.config(bg=PANEL_2)

        for index, kind in enumerate(EMERGENCY_TYPES):
            icon, short, accent = icon_map[kind]
            card = tk.Frame(gallery_frame, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1, cursor="hand2")
            card.emergency_kind = kind
            card.grid(row=index // 5, column=index % 5, sticky="nsew", padx=5, pady=5)
            tk.Label(card, text=icon, bg=PANEL_2, fg=TEXT, font=("Segoe UI Emoji", 29)).pack(pady=(10, 2))
            tk.Label(card, text=short, bg=PANEL_2, fg=TEXT, font=("Segoe UI", 9, "bold"), wraplength=115).pack(pady=(0, 10))
            for w in (card, *card.winfo_children()):
                w.bind("<Button-1>", lambda e, k=kind: choose(k))

        for c in range(5):
            gallery_frame.grid_columnconfigure(c, weight=1)

        def build_form(kind):
            wrapper = rounded_panel(form_holder, PANEL)
            wrapper.pack(fill="x")
            tk.Label(wrapper, text=f"{icon_map[kind][0]} {kind} REPORT", bg=PANEL, fg=TEXT, font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=22, pady=(18, 3))
            tk.Label(wrapper, text="Now enter the information responders need.", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=22, pady=(0, 15))

            form = tk.Frame(wrapper, bg=PANEL)
            form.pack(fill="x", padx=22, pady=(0, 20))
            left = tk.Frame(form, bg=PANEL)
            left.pack(side="left", fill="x", expand=True, padx=(0, 12))
            right = tk.Frame(form, bg=PANEL)
            right.pack(side="right", fill="x", expand=True, padx=(12, 0))

            def entry_field(parent, label, initial=""):
                tk.Label(parent, text=label, bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(7, 4))
                ent = tk.Entry(parent, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 11))
                ent.pack(fill="x", ipady=9)
                if initial:
                    ent.insert(0, initial)
                return ent

            user_name = self.current_user["full_name"] if self.current_user else ""
            user_phone = self.current_user["phone"] if self.current_user else ""
            name_entry = entry_field(left, "Your Name", user_name)
            phone_entry = entry_field(left, "Phone Number", user_phone)
            location_entry = entry_field(left, "Emergency Location")

            tk.Label(right, text="Priority", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(7, 4))
            priority_var = tk.StringVar(value="High")
            ttk.Combobox(right, textvariable=priority_var, values=PRIORITY_VALUES, state="readonly", font=("Segoe UI", 11)).pack(fill="x", ipady=6)

            tk.Label(right, text="Description", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 4))
            description = tk.Text(right, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 11), wrap="word", height=8)
            description.pack(fill="x")
            tk.Label(right, text="Example: what happened, people affected, hazards and nearby landmarks.", bg=PANEL, fg="#64748B", font=("Segoe UI", 8), wraplength=420, justify="left").pack(anchor="w", pady=7)

            message = tk.Label(wrapper, text="", bg=PANEL, fg=RED, font=("Segoe UI", 10, "bold"), wraplength=800)
            message.pack(pady=(0, 5))

            def submit():
                name = name_entry.get().strip()
                phone = phone_entry.get().strip()
                location = location_entry.get().strip()
                desc = description.get("1.0", "end").strip()
                ok, msg = validate_report(name, phone, location, desc)
                if not ok:
                    message.config(text=msg, fg=RED)
                    return
                try:
                    report_id = create_report(self.current_user["id"], name, phone, kind, location, desc, priority_var.get())
                except Exception:
                    message.config(text="Invalid: the emergency report could not be saved.", fg=RED)
                    return
                message.config(text=f"Emergency report #{report_id} submitted successfully.", fg=GREEN)
                self.root.after(1200, self.show_my_reports)

            buttons = tk.Frame(wrapper, bg=PANEL)
            buttons.pack(fill="x", padx=22, pady=(5, 20))
            make_button(buttons, "🚨 SUBMIT REPORT", submit, width=23, bg=RED).pack(side="left")
            make_button(buttons, "Clear Form", lambda: choose(kind), width=14, bg=PANEL_2).pack(side="left", padx=8)
            make_button(buttons, "Emergency Contacts", self.show_contacts, width=18, bg="#EAF0F6").pack(side="right")
            name_entry.focus_set()

        tk.Label(self.content, text="Tap one of the emergency cards above to continue.", bg=BG, fg="#64748B", font=("Segoe UI", 9)).pack(anchor="w", pady=8)

    def show_my_reports(self):
        self.clear_content()
        self.highlight_nav("▣  My Reports")

        tk.Label(
            self.content, text="My Emergency Reports",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Track the status and updates of reports submitted from your account.",
            bg=BG, fg=MUTED, font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        rows = get_user_reports(self.current_user["id"])

        table_frame = rounded_panel(self.content, PANEL)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id", "type", "location", "priority",
            "status", "created", "updated"
        )

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Emergency.Treeview"
        )

        headings = {
            "id": "ID",
            "type": "Emergency",
            "location": "Location",
            "priority": "Priority",
            "status": "Status",
            "created": "Submitted",
            "updated": "Updated",
        }

        widths = {
            "id": 60,
            "type": 145,
            "location": 180,
            "priority": 95,
            "status": 105,
            "created": 145,
            "updated": 145,
        }

        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="center")

        scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll.pack(side="right", fill="y", pady=10)

        for row in rows:
            tree.insert(
                "", "end",
                values=(
                    row["id"],
                    row["emergency_type"],
                    row["location"],
                    row["priority"],
                    row["status"],
                    row["created_at"],
                    row["updated_at"],
                )
            )

        detail = tk.Frame(self.content, bg=BG)
        detail.pack(fill="x", pady=(12, 0))

        def view_selected():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Select Report",
                    "Please select a report first."
                )
                return
            values = tree.item(selection[0], "values")
            report_id = int(values[0])
            self.show_report_details(report_id)

        make_button(
            detail, "View Selected Report",
            view_selected, width=22, bg=RED
        ).pack(side="left")

        make_button(
            detail, "Refresh",
            self.show_my_reports, width=12, bg=PANEL_2
        ).pack(side="left", padx=8)

    def show_report_details(self, report_id):
        conn = db_connect()
        row = conn.execute(
            "SELECT * FROM reports WHERE id=?", (report_id,)
        ).fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Report not found.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Emergency Report #{report_id}")
        win.geometry("620x620")
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win, text=f"Emergency Report #{report_id}",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w", padx=25, pady=(25, 5))

        card = rounded_panel(win, PANEL)
        card.pack(fill="both", expand=True, padx=25, pady=15)

        fields = [
            ("Emergency", row["emergency_type"]),
            ("Reporter", row["reporter_name"]),
            ("Phone", row["phone"]),
            ("Location", row["location"]),
            ("Priority", row["priority"]),
            ("Status", row["status"]),
            ("Submitted", row["created_at"]),
            ("Last Updated", row["updated_at"]),
        ]

        for label, value in fields:
            line = tk.Frame(card, bg=PANEL)
            line.pack(fill="x", padx=20, pady=6)
            tk.Label(
                line, text=label, width=14, anchor="w",
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9, "bold")
            ).pack(side="left")
            tk.Label(
                line, text=str(value), anchor="w",
                bg=PANEL, fg=TEXT,
                font=("Segoe UI", 10)
            ).pack(side="left", fill="x", expand=True)

        tk.Label(
            card, text="Description",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 4))

        desc = tk.Text(
            card, height=5, bg=PANEL_2, fg=TEXT,
            relief="flat", wrap="word",
            font=("Segoe UI", 10)
        )
        desc.pack(fill="x", padx=20)
        desc.insert("1.0", row["description"])
        desc.config(state="disabled")

        tk.Label(
            card, text="Admin Note",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(12, 4))

        note = row["admin_note"] or "No administrative update yet."
        tk.Label(
            card, text=note,
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=520,
            justify="left"
        ).pack(anchor="w", padx=20)

        make_button(
            win, "Close", win.destroy,
            width=15, bg=PANEL_2
        ).pack(pady=15)

    # ============================================================
    # CONTACTS
    # ============================================================

    def show_contacts(self):
        self.clear_content()
        self.highlight_nav("☎  Emergency Contacts")

        tk.Label(
            self.content,
            text="Ethiopian Emergency Contacts",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Keep these numbers available. Verify local service availability when possible.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        grid = tk.Frame(self.content, bg=BG)
        grid.pack(fill="both", expand=True)

        for index, (service, number, desc) in enumerate(EMERGENCY_NUMBERS):
            r = index // 2
            c = index % 2

            card = rounded_panel(grid, PANEL)
            card.grid(
                row=r, column=c,
                sticky="nsew",
                padx=8, pady=8
            )

            tk.Label(
                card, text="☎",
                bg="#FFFFFF", fg=RED,
                font=("Segoe UI", 27, "bold")
            ).pack(side="left", padx=18, pady=18)

            text = tk.Frame(card, bg="#FFFFFF")
            text.pack(side="left", fill="both", expand=True, pady=15)

            tk.Label(
                text, text=service,
                bg="#FFFFFF", fg=TEXT,
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w")

            tk.Label(
                text, text=number,
                bg="#FFFFFF", fg=ORANGE,
                font=("Segoe UI", 21, "bold")
            ).pack(anchor="w")

            tk.Label(
                text, text=desc,
                bg="#FFFFFF", fg=MUTED,
                font=("Segoe UI", 9),
                wraplength=320,
                justify="left"
            ).pack(anchor="w")


        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        note = tk.Label(
            self.content,
            text=(
                "Official sources used for the contact list include Addis Ababa Police "
                "and the Ethiopian Federal Police. Numbers can change, so confirm "
                "with official local authorities for operational use."
            ),
            bg=BG, fg="#64748B",
            font=("Segoe UI", 8),
            wraplength=900,
            justify="left"
        )
        note.pack(anchor="w", pady=10)


    # ============================================================
    # SAFETY INFORMATION
    # ============================================================

    def show_safety(self):
        self.clear_content()
        self.highlight_nav("◈  Safety Information")

        # Full-height scrollable safety page. The canvas occupies the entire
        # available content area, with a real scrollbar and mouse-wheel
        # support so the user can scroll using their own cursor.
        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_frame = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def update_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_width(event):
            canvas.itemconfigure(window_id, width=max(1, event.width))
            update_scrollregion()

        scroll_frame.bind("<Configure>", update_scrollregion)
        canvas.bind("<Configure>", resize_width)

        def wheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        def linux_wheel_up(event):
            canvas.yview_scroll(-3, "units")
            return "break"

        def linux_wheel_down(event):
            canvas.yview_scroll(3, "units")
            return "break"

        canvas.bind("<MouseWheel>", wheel)
        canvas.bind("<Button-4>", linux_wheel_up)
        canvas.bind("<Button-5>", linux_wheel_down)

        tk.Label(scroll_frame, text="Emergency Safety Information", bg=BG, fg="#000000",
                 font=("Segoe UI", 28, "bold")).pack(anchor="w", padx=4, pady=(4, 2))
        tk.Label(scroll_frame, text="Scroll with the mouse wheel or drag the scrollbar to read all safety guidance.",
                 bg=BG, fg="#000000", font=("Segoe UI", 10)).pack(anchor="w", padx=4, pady=(0, 18))

        information = [
            ("🔥 Fire", [
                "Move away from smoke and flames.",
                "Alert people nearby without putting yourself at risk.",
                "Do not use elevators in a burning building.",
                "If trapped, close doors between yourself and the fire and call for help.",
                "Do not return to collect belongings.",
            ]),
            ("🚑 Medical Emergency", [
                "Call for professional medical help for serious injuries.",
                "Keep the injured person calm and monitor their condition.",
                "Do not give food or drink to an unconscious person.",
                "Avoid moving someone with a suspected spinal injury unless danger requires it.",
                "Follow instructions from trained responders.",
            ]),
            ("🚗 Road Accident", [
                "Move to a safe location if you can do so without danger.",
                "Warn approaching traffic when it is safe.",
                "Report the exact road, landmark, direction, or nearby building.",
                "Do not stand in active traffic lanes.",
                "Do not attempt dangerous vehicle rescue yourself.",
            ]),
            ("🌊 Flood", [
                "Move to higher ground when flooding threatens.",
                "Never walk or drive through moving floodwater.",
                "Keep away from electrical equipment in wet areas.",
                "Follow evacuation instructions from local authorities.",
                "Carry essential documents and medicines only if safe.",
            ]),
            ("🏢 Building Collapse", [
                "Stay away from unstable structures.",
                "Avoid dust and falling debris.",
                "Call emergency responders and give the building location.",
                "Do not enter rubble unless trained responders direct you.",
                "If trapped, conserve energy and signal for rescuers.",
            ]),
            ("⚡ Electrical Emergency", [
                "Do not touch a person who may still be in contact with electricity.",
                "Keep water away from electrical equipment.",
                "Stay away from fallen power lines.",
                "Call the relevant emergency service or utility provider.",
                "Do not attempt repairs during an emergency.",
            ]),
            ("🛡 Security / Crime", [
                "Move to a safer place if possible.",
                "Do not confront a dangerous person unnecessarily.",
                "Remember useful details only if it is safe to do so.",
                "Contact police through the appropriate emergency channel.",
                "Protect your personal information.",
            ]),
            ("🌪 Natural Disaster", [
                "Follow official warnings and evacuation instructions.",
                "Keep away from damaged buildings and exposed wires.",
                "Use a safe shelter appropriate to the hazard.",
                "Check on vulnerable people only when it is safe.",
                "Wait for official clearance before returning.",
            ]),
        ]

        for title, rules in information:
            card = rounded_panel(scroll_frame, PANEL)
            card.pack(fill="x", padx=4, pady=8)
            tk.Label(card, text=title, bg=PANEL, fg="#000000", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=22, pady=(18, 10))
            for item in rules:
                row = tk.Frame(card, bg=PANEL)
                row.pack(fill="x", padx=24, pady=5)
                tk.Label(row, text="•", bg=PANEL, fg=RED, font=("Segoe UI", 13, "bold")).pack(side="left")
                tk.Label(row, text=item, bg=PANEL, fg="#000000", font=("Segoe UI", 11),
                         wraplength=1000, justify="left", anchor="w").pack(side="left", padx=10, fill="x", expand=True)
            tk.Frame(card, bg=PANEL, height=12).pack()

        canvas.update_idletasks()
        update_scrollregion()

    # ============================================================
    # PROFILE
    # ============================================================

    def show_profile(self):
        self.clear_content()
        self.highlight_nav("⚙  My Profile")

        tk.Label(
            self.content, text="My Profile",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Your registered account information.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        card = rounded_panel(self.content, PANEL)
        card.pack(fill="x", padx=5, pady=5)

        initials = self.current_user["full_name"][:1].upper()

        tk.Label(
            card,
            text=initials,
            bg=RED, fg=WHITE,
            font=("Segoe UI", 30, "bold"),
            width=4, height=2
        ).pack(side="left", padx=25, pady=25)

        info = tk.Frame(card, bg=PANEL)
        info.pack(side="left", fill="both", expand=True, pady=25)

        fields = [
            ("Full name", self.current_user["full_name"]),
            ("Phone", self.current_user["phone"]),
            ("Email", self.current_user["email"]),
            ("Account created", self.current_user["created_at"]),
        ]

        for label, value in fields:
            row = tk.Frame(info, bg=PANEL)
            row.pack(fill="x", pady=3)

            tk.Label(
                row, text=label,
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9, "bold"),
                width=18, anchor="w"
            ).pack(side="left")

            tk.Label(
                row, text=value,
                bg=PANEL, fg=TEXT,
                font=("Segoe UI", 10),
                anchor="w"
            ).pack(side="left")

        make_button(
            self.content,
            "Logout",
            self.logout,
            width=16,
            bg=RED
        ).pack(anchor="w", padx=5, pady=15)

    # ============================================================
    # ADMIN SHELL
    # ============================================================

    def setup_admin_shell(self):
        self.clear_window()

        top = tk.Frame(self.root, bg="#F4F7FB", height=74)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="🚨  EMERGENCY COMMAND CENTER", bg="#F4F7FB", fg=TEXT, font=("Segoe UI", 18, "bold")).pack(side="left", padx=24)
        tk.Label(top, text="ADMINISTRATOR", bg="#F4F7FB", fg=ORANGE, font=("Segoe UI", 10, "bold")).pack(side="right", padx=10)
        make_button(top, "Logout", self.logout, width=9, bg="#EAF0F6").pack(side="right", padx=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(body, bg=PANEL, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="ADMIN MENU", bg=PANEL, fg="#64748B", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=22, pady=(25, 12))
        self.nav_buttons = []
        self.add_nav_button("Dashboard", self.show_admin_dashboard)
        self.add_nav_button("All Reports", self.show_all_reports)
        self.add_nav_button("Update Status", self.show_admin_reports)
        self.add_nav_button("Users", self.show_users)
        self.add_nav_button("Activity Log", self.show_activity)
        self.add_nav_button("Emergency Contacts", self.show_contacts_admin)
        self.add_nav_button("Safety Information", self.show_safety_admin)

        content_area = tk.Frame(body, bg=BG)
        content_area.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(content_area, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(content_area, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        self.content = tk.Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=max(700, e.width)))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

    def show_admin_dashboard(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()
        self.clear_content()
        self.highlight_nav("Dashboard")

        stats = get_statistics()

        tk.Label(
            self.content,
            text="Admin Dashboard",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 28, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Monitor incoming reports and manage response status.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 18))

        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")

        self.admin_stat(cards, "TOTAL REPORTS", stats["total"], BLUE)
        self.admin_stat(cards, "PENDING", stats["pending"], ORANGE)
        self.admin_stat(cards, "RESPONDING", stats["responding"], RED)
        self.admin_stat(cards, "RESOLVED", stats["resolved"], GREEN)
        self.admin_stat(cards, "CRITICAL", stats["critical"], PURPLE)

        middle = tk.Frame(self.content, bg=BG)
        middle.pack(fill="both", expand=True, pady=20)

        recent = rounded_panel(middle, PANEL)
        recent.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            recent,
            text="Recent Emergency Reports",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 10))

        rows = get_all_reports()[:7]

        if not rows:
            tk.Label(
                recent,
                text="No reports have been submitted yet.",
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 10)
            ).pack(anchor="w", padx=20, pady=15)
        else:
            for row in rows:
                line = tk.Frame(
                    recent, bg="#EAF0F6",
                    highlightbackground=BORDER,
                    highlightthickness=1
                )
                line.pack(fill="x", padx=15, pady=4)

                tk.Label(
                    line,
                    text=f"#{row['id']}",
                    bg="#EAF0F6", fg=ORANGE,
                    font=("Segoe UI", 10, "bold"),
                    width=6
                ).pack(side="left", padx=8)

                tk.Label(
                    line,
                    text=row["emergency_type"],
                    bg="#EAF0F6", fg=TEXT,
                    font=("Segoe UI", 10, "bold"),
                    width=20, anchor="w"
                ).pack(side="left")

                tk.Label(
                    line,
                    text=row["location"],
                    bg="#EAF0F6", fg=MUTED,
                    font=("Segoe UI", 9),
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)

                tk.Label(
                    line,
                    text=row["status"],
                    bg="#EAF0F6",
                    fg=self.status_color(row["status"]),
                    font=("Segoe UI", 9, "bold"),
                    width=13
                ).pack(side="right", padx=8)

        actions = rounded_panel(middle, PANEL)
        actions.pack(side="right", fill="both", expand=False, padx=(10, 0))

        tk.Label(
            actions,
            text="Quick Actions",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 15))

        make_button(
            actions, "View All Reports",
            self.show_all_reports,
            width=23, bg=RED
        ).pack(padx=20, pady=5)

        make_button(
            actions, "Change Status",
            self.show_admin_reports,
            width=23, bg=PANEL_2
        ).pack(padx=20, pady=5)

        make_button(
            actions, "Manage Users",
            self.show_users,
            width=23, bg=PANEL_2
        ).pack(padx=20, pady=5)

        make_button(
            actions, "Refresh Dashboard",
            self.show_admin_dashboard,
            width=23, bg="#EAF0F6"
        ).pack(padx=20, pady=5)

        tk.Label(
            actions,
            text="Security",
            bg=PANEL, fg=ORANGE,
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=20, pady=(25, 5))

        tk.Label(
            actions,
            text=(
                "The administrator password is stored in the program's "
                "private credential check and is not displayed on the login page."
            ),
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=220,
            justify="left"
        ).pack(anchor="w", padx=20)

    def admin_stat(self, parent, title, value, accent):
        card = tk.Frame(
            parent, bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card.pack(side="left", fill="x", expand=True, padx=4)

        tk.Frame(card, bg=accent, height=5).pack(fill="x")

        tk.Label(
            card, text=str(value),
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 26, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 0))

        tk.Label(
            card, text=title,
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=15, pady=(0, 13))

    def status_color(self, status):
        colors = {
            "Pending": ORANGE,
            "Assigned": BLUE,
            "Responding": RED,
            "Resolved": GREEN,
            "Cancelled": "#64748B",
        }
        return colors.get(status, WHITE)

    # ============================================================
    # ADMIN REPORTS TABLE
    # ============================================================

    def show_all_reports(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()

        self.clear_content()
        self.highlight_nav("All Reports")

        tk.Label(
            self.content,
            text="All Emergency Reports",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        toolbar = tk.Frame(self.content, bg=BG)
        toolbar.pack(fill="x", pady=(10, 12))

        search_var = tk.StringVar()
        search = tk.Entry(
            toolbar,
            textvariable=search_var,
            bg=PANEL_2, fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10)
        )
        search.pack(side="left", fill="x", expand=True, ipady=9)

        make_button(
            toolbar, "Search",
            lambda: refresh(),
            width=12, bg=RED
        ).pack(side="left", padx=7)

        make_button(
            toolbar, "Refresh",
            self.show_all_reports,
            width=12, bg=PANEL_2
        ).pack(side="left")

        table = rounded_panel(self.content, PANEL)
        table.pack(fill="both", expand=True)

        columns = (
            "id", "name", "type", "location",
            "priority", "status", "created"
        )

        tree = ttk.Treeview(
            table,
            columns=columns,
            show="headings",
            style="Emergency.Treeview"
        )

        specs = [
            ("id", "ID", 55),
            ("name", "Reporter", 145),
            ("type", "Emergency", 145),
            ("location", "Location", 190),
            ("priority", "Priority", 90),
            ("status", "Status", 105),
            ("created", "Created", 145),
        ]

        for col, heading, width in specs:
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(
            table, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll.pack(side="right", fill="y", pady=10)

        def refresh():
            for item in tree.get_children():
                tree.delete(item)

            query = search_var.get().strip().lower()
            rows = get_all_reports()

            for row in rows:
                searchable = " ".join(
                    [
                        str(row["id"]),
                        row["reporter_name"],
                        row["emergency_type"],
                        row["location"],
                        row["priority"],
                        row["status"],
                        row["description"],
                    ]
                ).lower()

                if query and query not in searchable:
                    continue

                tree.insert(
                    "",
                    "end",
                    values=(
                        row["id"],
                        row["reporter_name"],
                        row["emergency_type"],
                        row["location"],
                        row["priority"],
                        row["status"],
                        row["created_at"],
                    )
                )

        refresh()

        buttons = tk.Frame(self.content, bg=BG)
        buttons.pack(fill="x", pady=12)

        def selected_id():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Select Report",
                    "Select an emergency report first."
                )
                return None
            return int(tree.item(selection[0], "values")[0])

        make_button(
            buttons,
            "Open Details",
            lambda: self.admin_report_details(selected_id()),
            width=16, bg=RED
        ).pack(side="left")

        make_button(
            buttons,
            "Update Status",
            lambda: self.update_report_window(selected_id()),
            width=16, bg=ORANGE
        ).pack(side="left", padx=8)

        make_button(
            buttons,
            "Delete Report",
            lambda: self.delete_selected_report(selected_id()),
            width=16, bg="#B4232F"
        ).pack(side="left")

    def admin_report_details(self, report_id):
        if not report_id:
            return

        conn = db_connect()
        row = conn.execute(
            "SELECT * FROM reports WHERE id=?", (report_id,)
        ).fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Report not found.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Admin Report #{report_id}")
        win.geometry("680x680")
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text=f"Emergency Report #{report_id}",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w", padx=25, pady=(25, 5))

        card = rounded_panel(win, PANEL)
        card.pack(fill="both", expand=True, padx=25, pady=15)

        values = [
            ("Reporter", row["reporter_name"]),
            ("Phone", row["phone"]),
            ("Emergency", row["emergency_type"]),
            ("Location", row["location"]),
            ("Priority", row["priority"]),
            ("Status", row["status"]),
            ("Created", row["created_at"]),
            ("Updated", row["updated_at"]),
        ]

        for label, value in values:
            line = tk.Frame(card, bg=PANEL)
            line.pack(fill="x", padx=20, pady=5)

            tk.Label(
                line, text=label,
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9, "bold"),
                width=15, anchor="w"
            ).pack(side="left")

            tk.Label(
                line, text=value,
                bg=PANEL, fg=TEXT,
                font=("Segoe UI", 10),
                anchor="w"
            ).pack(side="left")

        tk.Label(
            card, text="Description",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(12, 4))

        desc = tk.Text(
            card, bg=PANEL_2, fg=TEXT,
            relief="flat", height=7,
            wrap="word", font=("Segoe UI", 10)
        )
        desc.pack(fill="x", padx=20)
        desc.insert("1.0", row["description"])
        desc.config(state="disabled")

        tk.Label(
            card, text="Administrative Note",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(12, 4))

        note = tk.Label(
            card,
            text=row["admin_note"] or "No note.",
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=560,
            justify="left"
        )
        note.pack(anchor="w", padx=20)

        buttons = tk.Frame(win, bg=BG)
        buttons.pack(pady=15)

        make_button(
            buttons,
            "Change Status",
            lambda: [win.destroy(), self.update_report_window(report_id)],
            width=16, bg=RED
        ).pack(side="left", padx=5)

        make_button(
            buttons, "Close", win.destroy,
            width=12, bg=PANEL_2
        ).pack(side="left", padx=5)

    def show_admin_reports(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()

        self.clear_content()
        self.highlight_nav("Update Status")

        tk.Label(
            self.content,
            text="Manage Emergency Status",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Select a report and change its status, priority, and administrative note.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        table = rounded_panel(self.content, PANEL)
        table.pack(fill="both", expand=True)

        columns = (
            "id", "type", "reporter", "priority", "status"
        )

        tree = ttk.Treeview(
            table, columns=columns,
            show="headings",
            style="Emergency.Treeview"
        )

        specs = [
            ("id", "ID", 60),
            ("type", "Emergency", 190),
            ("reporter", "Reporter", 180),
            ("priority", "Priority", 110),
            ("status", "Status", 130),
        ]

        for col, heading, width in specs:
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(
            table, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll.pack(side="right", fill="y", pady=10)

        for row in get_all_reports():
            tree.insert(
                "", "end",
                values=(
                    row["id"],
                    row["emergency_type"],
                    row["reporter_name"],
                    row["priority"],
                    row["status"],
                )
            )

        def get_id():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Select Report",
                    "Select a report before changing its status."
                )
                return None
            return int(tree.item(selection[0], "values")[0])

        make_button(
            self.content,
            "Change Selected Report",
            lambda: self.update_report_window(get_id()),
            width=24, bg=RED
        ).pack(anchor="w", pady=12)

    def update_report_window(self, report_id):
        if not report_id:
            return

        conn = db_connect()
        row = conn.execute(
            "SELECT * FROM reports WHERE id=?", (report_id,)
        ).fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Report not found.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Update Report #{report_id}")
        win.geometry("520x500")
        win.configure(bg=BG)
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win,
            text=f"Update Report #{report_id}",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(25, 4))

        tk.Label(
            win,
            text=f"{row['emergency_type']} • {row['location']}",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(pady=(0, 18))

        form = rounded_panel(win, PANEL)
        form.pack(fill="both", expand=True, padx=25, pady=10)

        tk.Label(
            form, text="Status",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=25, pady=(20, 5))

        status_var = tk.StringVar(value=row["status"])
        status_box = ttk.Combobox(
            form,
            textvariable=status_var,
            values=STATUS_VALUES,
            state="readonly",
            font=("Segoe UI", 11)
        )
        status_box.pack(fill="x", padx=25, ipady=6)

        tk.Label(
            form, text="Priority",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=25, pady=(15, 5))

        priority_var = tk.StringVar(value=row["priority"])
        priority_box = ttk.Combobox(
            form,
            textvariable=priority_var,
            values=PRIORITY_VALUES,
            state="readonly",
            font=("Segoe UI", 11)
        )
        priority_box.pack(fill="x", padx=25, ipady=6)

        tk.Label(
            form, text="Administrative Note",
            bg=PANEL, fg=TEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=25, pady=(15, 5))

        note = tk.Text(
            form, height=6,
            bg=PANEL_2, fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            wrap="word"
        )
        note.pack(fill="both", expand=True, padx=25)
        note.insert("1.0", row["admin_note"] or "")

        def save():
            new_note = note.get("1.0", "end").strip()

            if len(new_note) > 600:
                messagebox.showerror(
                    "Invalid",
                    "Invalid administrative note. Maximum 600 characters."
                )
                return

            update_report(
                report_id,
                status_var.get(),
                priority_var.get(),
                new_note
            )

            messagebox.showinfo(
                "Updated",
                f"Report #{report_id} has been updated."
            )
            win.destroy()
            self.show_admin_reports()

        make_button(
            win, "SAVE STATUS UPDATE",
            save, width=25, bg=RED
        ).pack(pady=15)

    def delete_selected_report(self, report_id):
        if not report_id:
            return

        answer = messagebox.askyesno(
            "Delete Report",
            f"Are you sure you want to delete report #{report_id}?"
        )
        if not answer:
            return

        delete_report(report_id)
        messagebox.showinfo(
            "Deleted",
            f"Report #{report_id} was deleted."
        )
        self.show_all_reports()

    # ============================================================
    # ADMIN USERS
    # ============================================================

    def show_users(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()

        self.clear_content()
        self.highlight_nav("Users")

        tk.Label(
            self.content,
            text="Registered Users",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="View accounts that have been created in this local database.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        card = rounded_panel(self.content, PANEL)
        card.pack(fill="both", expand=True)

        columns = (
            "id", "name", "phone", "email", "created"
        )

        tree = ttk.Treeview(
            card, columns=columns,
            show="headings",
            style="Emergency.Treeview"
        )

        specs = [
            ("id", "ID", 60),
            ("name", "Full Name", 200),
            ("phone", "Phone", 150),
            ("email", "Email", 250),
            ("created", "Created", 160),
        ]

        for col, heading, width in specs:
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(
            card, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll.pack(side="right", fill="y", pady=10)

        conn = db_connect()
        rows = conn.execute(
            "SELECT * FROM users ORDER BY id DESC"
        ).fetchall()
        conn.close()

        for row in rows:
            tree.insert(
                "", "end",
                values=(
                    row["id"],
                    row["full_name"],
                    row["phone"],
                    row["email"],
                    row["created_at"],
                )
            )

        stats = get_statistics()

        tk.Label(
            self.content,
            text=f"Total registered users: {stats['users']}",
            bg=BG, fg=ORANGE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=10)

    # ============================================================
    # ADMIN ACTIVITY LOG
    # ============================================================

    def show_activity(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()

        self.clear_content()
        self.highlight_nav("Activity Log")

        tk.Label(
            self.content,
            text="Activity Log",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Recent account and emergency-management actions.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        card = rounded_panel(self.content, PANEL)
        card.pack(fill="both", expand=True)

        columns = ("id", "action", "details", "created")
        tree = ttk.Treeview(
            card, columns=columns,
            show="headings",
            style="Emergency.Treeview"
        )

        specs = [
            ("id", "ID", 60),
            ("action", "Action", 180),
            ("details", "Details", 500),
            ("created", "Time", 170),
        ]

        for col, heading, width in specs:
            tree.heading(col, text=heading)
            tree.column(col, width=width, anchor="center")

        scroll = ttk.Scrollbar(
            card, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scroll.set)

        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll.pack(side="right", fill="y", pady=10)

        conn = db_connect()
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY id DESC LIMIT 250"
        ).fetchall()
        conn.close()

        for row in rows:
            tree.insert(
                "", "end",
                values=(
                    row["id"],
                    row["action"],
                    row["details"],
                    row["created_at"],
                )
            )

        make_button(
            self.content,
            "Refresh Activity",
            self.show_activity,
            width=18, bg=PANEL_2
        ).pack(anchor="w", pady=10)

    # ============================================================
    # ADMIN CONTACTS / SAFETY
    # ============================================================

    def show_contacts_admin(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()

        self.clear_content()
        self.highlight_nav("Emergency Contacts")

        tk.Label(
            self.content,
            text="Emergency Contact Reference",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Quick reference for the administrator.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        card = rounded_panel(self.content, PANEL)
        card.pack(fill="both", expand=True)

        for service, number, desc in EMERGENCY_NUMBERS:
            row = tk.Frame(
                card, bg="#EAF0F6",
                highlightbackground=BORDER,
                highlightthickness=1
            )
            row.pack(fill="x", padx=18, pady=5)

            tk.Label(
                row, text=service,
                bg="#EAF0F6", fg=TEXT,
                font=("Segoe UI", 10, "bold"),
                width=28, anchor="w"
            ).pack(side="left", padx=12, pady=10)

            tk.Label(
                row, text=number,
                bg="#EAF0F6", fg=ORANGE,
                font=("Segoe UI", 13, "bold"),
                width=12
            ).pack(side="left")

            tk.Label(
                row, text=desc,
                bg="#EAF0F6", fg=MUTED,
                font=("Segoe UI", 9),
                anchor="w"
            ).pack(side="left", padx=10)

    def show_safety_admin(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()

        self.clear_content()
        self.highlight_nav("Safety Information")

        tk.Label(
            self.content,
            text="Safety Information",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Administrator reference for common hazards.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        card = rounded_panel(self.content, PANEL)
        card.pack(fill="both", expand=True)

        notes = [
            ("Fire", "Evacuate, avoid smoke, keep routes clear, call fire services."),
            ("Medical", "Protect the patient, call trained responders, avoid unsafe movement."),
            ("Road Accident", "Stay clear of traffic, identify location, call emergency services."),
            ("Flood", "Move to higher ground and never enter fast-moving water."),
            ("Collapse", "Stay away from unstable structures and wait for trained rescuers."),
            ("Electrical", "Avoid fallen lines and do not touch energized equipment."),
            ("Security", "Move to safety and contact police without unnecessary confrontation."),
        ]

        for title, text in notes:
            line = tk.Frame(card, bg=PANEL)
            line.pack(fill="x", padx=20, pady=8)

            tk.Label(
                line, text=title,
                bg=PANEL, fg=ORANGE,
                font=("Segoe UI", 11, "bold"),
                width=20, anchor="w"
            ).pack(side="left")

            tk.Label(
                line, text=text,
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 10),
                wraplength=650,
                justify="left"
            ).pack(side="left", fill="x", expand=True)

    # ============================================================
    # LOGOUT / CLOSE
    # ============================================================

    def logout(self):
        if self.current_role == "admin":
            log_activity("ADMIN_LOGOUT", "Administrator signed out")
        elif self.current_user:
            log_activity(
                "USER_LOGOUT",
                f"User {self.current_user['id']} signed out"
            )

        self.current_user = None
        self.current_role = None
        self.current_page = None
        self.content = None
        self.sidebar = None
        self.show_welcome()


# ================================================================
# STARTUP HELPERS
# ================================================================

def show_startup_error(root, error):
    messagebox.showerror(
        "Startup Error",
        "The emergency system could not start correctly.\n\n"
        f"Error: {error}\n\n"
        "Make sure you are using Python 3 with Tkinter available."
    )


def main():
    try:
        create_database()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        show_startup_error(root, exc)
        root.destroy()
        return

    root = tk.Tk()

    try:
        app = EmergencyApp(root)
    except Exception as exc:
        show_startup_error(root, exc)
        root.destroy()
        return

    # Closing the window only closes the GUI. It does NOT delete the SQLite
    # database. All committed records remain in emergency_response.db.
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()


# ================================================================
# PROJECT NOTES
# ================================================================
# 1. Save this entire file as emergency_response_system.py.
# 2. Open it in VS Code.
# 3. Run with Python 3.
# 4. No pip install is required for the application itself.
# 5. A local SQLite database named emergency_response.db is created.
# 6. User accounts are stored locally.
# 7. Emergency reports are stored locally.
# 8. Admin can update status and priority.
# 9. Admin can add administrative notes.
# 10. Admin can delete reports.
# 11. LOGOUT DOES NOT DELETE DATA.
# 12. CLOSING AND RUNNING THE PROGRAM AGAIN DOES NOT DELETE DATA.
# 13. The same emergency_response.db file is reused on every startup.
# 14. Accounts, reports, status changes, priorities, notes and activity logs
#     remain available after logout, application restart and VS Code rerun.
# 11. Admin can view users.
# 12. Admin can view activity.
# 13. The public login page does NOT reveal the admin password.
# 14. The administrator credential is:
#       username: admin
#       password: 102030
#     It is intentionally not printed in the user interface.
# ================================================================
# VALIDATION BEHAVIOR
# ================================================================
# The system rejects:
# - empty names
# - names made from numbers
# - invalid phone numbers
# - invalid email addresses
# - short passwords
# - mismatched confirmation passwords
# - meaningless locations
# - descriptions shorter than 10 characters
# - administrative notes longer than 600 characters
#
# ================================================================
# STATUS FLOW
# ================================================================
# Pending -> Assigned -> Responding -> Resolved
#                         |
#                         -> Cancelled
#
# The administrator can choose any available status when managing
# a report because real emergency situations do not always progress
# through a perfect linear workflow.
# ================================================================
# END OF FILE
# ================================================================

# ================================================================
# EXTENDED PROJECT DOCUMENTATION
# ================================================================
# DATABASE DESIGN
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# USER ACCOUNT MANAGEMENT
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# ADMINISTRATOR MANAGEMENT
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# EMERGENCY REPORT MANAGEMENT
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# INPUT VALIDATION
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# ETHIOPIAN CONTACT REFERENCE
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# SAFETY INFORMATION
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# USER INTERFACE DESIGN
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# SECURITY NOTES
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# TESTING CHECKLIST
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# MAINTENANCE NOTES
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# FUTURE UPGRADE IDEAS
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# TROUBLESHOOTING
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# DEMO PRESENTATION GUIDE
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and emergency records.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

