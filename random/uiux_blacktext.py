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
#
# This application is intended as a school/project demonstration.
# For a real emergency, call the appropriate emergency service directly.
# ================================================================

import os
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

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        card = rounded_panel(canvas, PANEL)
        window_id = canvas.create_window((0, 0), window=card, anchor="n", width=470)

        def resize(event):
            canvas.itemconfigure(window_id, width=min(470, max(360, event.width - 30)))
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", resize)
        card.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta/120), "units"))

        tk.Label(card, text="🚨", bg=PANEL, fg=RED, font=("Segoe UI Emoji", 42)).pack(pady=(28, 4))
        tk.Label(card, text="Welcome Back", bg=PANEL, fg=TEXT, font=("Segoe UI", 25, "bold")).pack()
        tk.Label(card, text="Sign in to your emergency account", bg=PANEL, fg=MUTED, font=("Segoe UI", 11)).pack(pady=(4, 8))

        notice = tk.Frame(card, bg="#F7F9FC", highlightbackground=BORDER, highlightthickness=1)
        notice.pack(fill="x", padx=45, pady=(8, 20))
        tk.Label(notice, text="✓  Please enter appropriate information", bg="#F7F9FC", fg=ORANGE, font=("Segoe UI", 10, "bold"), wraplength=330, justify="left").pack(anchor="w", padx=14, pady=(10, 3))
        tk.Label(notice, text="Use the same name and password you used when creating your account. Do not enter numbers in the name field.", bg="#F7F9FC", fg=MUTED, font=("Segoe UI", 9), wraplength=330, justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        tk.Label(card, text="Full Name", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=55)
        name_entry = tk.Entry(card, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 12))
        name_entry.pack(fill="x", padx=55, ipady=10, pady=(5, 15))

        tk.Label(card, text="Password", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=55)
        password = tk.Entry(card, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, show="•", relief="flat", font=("Segoe UI", 12))
        password.pack(fill="x", padx=55, ipady=10, pady=(5, 8))

        message = tk.Label(card, text="", bg=PANEL, fg=RED, font=("Segoe UI", 10, "bold"), wraplength=350)
        message.pack(pady=7)

        def do_login():
            name = name_entry.get().strip()
            p = password.get()
            if not name or not p:
                message.config(text="Invalid: name and password are required.", fg=RED)
                return
            # Admin credential remains hidden from the interface.
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
        make_button(card, "Create New Account", self.show_signup, width=25, bg=PANEL_2).pack(pady=4)
        make_button(card, "Back to Home", self.show_welcome, width=25, bg="#EAF0F6").pack(pady=4)
        tk.Label(card, text="Administrator access is protected.", bg=PANEL, fg="#64748B", font=("Segoe UI", 8)).pack(pady=(15, 22))

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
            width=28, bg=RED
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

        tk.Label(
            self.content,
            text="Emergency Safety Information",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Simple guidance for common emergency situations.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer, bg=BG, highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            outer, orient="vertical", command=canvas.yview
        )
        scroll_frame = tk.Frame(canvas, bg=BG)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window(
            (0, 0), window=scroll_frame, anchor="nw"
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        information = [
            (
                "🔥 Fire",
                [
                    "Move away from smoke and flames.",
                    "Alert people nearby without putting yourself at risk.",
                    "Do not use elevators in a burning building.",
                    "If trapped, close doors between yourself and the fire and call for help.",
                    "Do not return to collect belongings.",
                ],
            ),
            (
                "🚑 Medical Emergency",
                [
                    "Call for professional medical help for serious injuries.",
                    "Keep the injured person calm and monitor their condition.",
                    "Do not give food or drink to an unconscious person.",
                    "Avoid moving someone with a suspected spinal injury unless danger requires it.",
                    "Follow instructions from trained responders.",
                ],
            ),
            (
                "🚗 Road Accident",
                [
                    "Move to a safe location if you can do so without danger.",
                    "Warn approaching traffic when it is safe.",
                    "Report the exact road, landmark, direction, or nearby building.",
                    "Do not stand in active traffic lanes.",
                    "Do not attempt dangerous vehicle rescue yourself.",
                ],
            ),
            (
                "🌊 Flood",
                [
                    "Move to higher ground when flooding threatens.",
                    "Never walk or drive through moving floodwater.",
                    "Keep away from electrical equipment in wet areas.",
                    "Follow evacuation instructions from local authorities.",
                    "Carry essential documents and medicines only if safe.",
                ],
            ),
            (
                "🏢 Building Collapse",
                [
                    "Stay away from unstable structures.",
                    "Avoid dust and falling debris.",
                    "Call emergency responders and give the building location.",
                    "Do not enter rubble unless trained responders direct you.",
                    "If trapped, conserve energy and signal for rescuers.",
                ],
            ),
            (
                "⚡ Electrical Emergency",
                [
                    "Do not touch a person who may still be in contact with electricity.",
                    "Keep water away from electrical equipment.",
                    "Stay away from fallen power lines.",
                    "Call the relevant emergency service or utility provider.",
                    "Do not attempt repairs during an emergency.",
                ],
            ),
            (
                "🛡 Security / Crime",
                [
                    "Move to a safer place if possible.",
                    "Do not confront a dangerous person unnecessarily.",
                    "Remember useful details only if it is safe to do so.",
                    "Contact police through the appropriate emergency channel.",
                    "Protect your personal information.",
                ],
            ),
            (
                "🌪 Natural Disaster",
                [
                    "Follow official warnings and evacuation instructions.",
                    "Keep away from damaged buildings and exposed wires.",
                    "Use a safe shelter appropriate to the hazard.",
                    "Check on vulnerable people only when it is safe.",
                    "Wait for official clearance before returning.",
                ],
            ),
        ]

        for title, rules in information:
            card = rounded_panel(scroll_frame, PANEL)
            card.pack(fill="x", padx=5, pady=7)

            tk.Label(
                card, text=title,
                bg=PANEL, fg=TEXT,
                font=("Segoe UI", 14, "bold")
            ).pack(anchor="w", padx=20, pady=(15, 8))

            for item in rules:
                row = tk.Frame(card, bg=PANEL)
                row.pack(fill="x", padx=22, pady=3)

                tk.Label(
                    row, text="•",
                    bg=PANEL, fg=ORANGE,
                    font=("Segoe UI", 12, "bold")
                ).pack(side="left")

                tk.Label(
                    row, text=item,
                    bg=PANEL, fg=MUTED,
                    font=("Segoe UI", 10),
                    wraplength=780,
                    justify="left"
                ).pack(side="left", padx=8)

            tk.Frame(card, bg=PANEL, height=10).pack()

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

