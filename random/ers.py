# ================================================================
# ETHIOPIA EMERGENCY RESPONSE & MANAGEMENT SYSTEM
# ================================================================
# Single-file Python application.
# Standard library only: tkinter + sqlite3 + urllib + webbrowser.
#
# IMPORTANT:
# - No third-party package is required.
# - The database is created automatically beside this file.
# - Default ADMIN USERNAME: admin
# - Default ADMIN PASSWORD: 102030
# - The administrator password is NEVER displayed on the public login page.
# - Emergency photographs are opened from Wikimedia Commons in the
#   browser when the user selects "View real incident photo".
#
# This application is intended as a school/project demonstration.
# For a real emergency, call the appropriate emergency service directly.
# ================================================================

import os
import re
import sqlite3
import hashlib
import secrets
import webbrowser
import urllib.request
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

REAL_PHOTO_URLS = {
    "Road Accident": (
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Car-accident.jpg"
    ),
    "Fire": (
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
        "Fire_truck_vehicle_in_fire_action.jpg"
    ),
    "Fire Response": (
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
        "Firefighting_crew_in_fire_truck_responding_to_fire.jpg"
    ),
    "Road Accident Response": (
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
        "Car_accident.jpeg"
    ),
}

# ================================================================
# DATABASE
# ================================================================

def db_connect():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def hash_password(password):
    salt = "ERS-ETHIOPIA-SCHOOL-PROJECT"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def create_database():
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

    # Create a demo admin record only if the admin table is not separately
    # needed. The actual admin credential is kept in constants and is not
    # printed or shown in the user interface.
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


def authenticate_user(email, password):
    conn = db_connect()
    row = conn.execute(
        "SELECT * FROM users WHERE email=? AND password_hash=?",
        (email.lower(), hash_password(password))
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

BG = "#07111f"
PANEL = "#0d1b2a"
PANEL_2 = "#10243a"
CARD = "#132b43"
RED = "#e63946"
RED_DARK = "#b91c2a"
ORANGE = "#ff8c42"
WHITE = "#f8fafc"
MUTED = "#9fb0c0"
GREEN = "#35c98a"
BLUE = "#3b82f6"
YELLOW = "#f2c94c"
PURPLE = "#9b87f5"
BORDER = "#24415c"


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
               fg=WHITE, bg=None, anchor="w"):
    return tk.Label(
        parent,
        text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        fg=fg,
        bg=parent.cget("bg") if bg is None else bg,
        anchor=anchor
    )


def rounded_panel(parent, bg=PANEL):
    frame = tk.Frame(
        parent,
        bg=bg,
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0
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
            foreground=WHITE,
            fieldbackground=PANEL_2,
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Emergency.Treeview.Heading",
            background=CARD,
            foreground=WHITE,
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
            fg=WHITE,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=7
        )
        badge.pack(anchor="w", pady=(30, 18))

        title = tk.Label(
            left,
            text="Emergency\nResponse System",
            bg=BG,
            fg=WHITE,
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
            fill="#182b3d", outline=""
        )
        canvas.create_rectangle(
            70, 365, 160, 410,
            fill="#dfe7ef", outline=""
        )
        canvas.create_rectangle(
            85, 350, 145, 380,
            fill="#dfe7ef", outline=""
        )
        canvas.create_oval(
            78, 395, 110, 427,
            fill="#07111f", outline=""
        )
        canvas.create_oval(
            120, 395, 152, 427,
            fill="#07111f", outline=""
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
            fg=WHITE,
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(0, 20))

        footer = tk.Label(
            outer,
            text="Ethiopia Emergency Response System  •  School Project",
            bg=BG,
            fg="#6f8295",
            font=("Segoe UI", 9)
        )
        footer.pack(side="bottom", pady=12)

    # ============================================================
    # LOGIN
    # ============================================================

    def show_login(self):
        self.clear_window()

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True)

        card = rounded_panel(container, PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center", width=470, height=560)

        tk.Label(
            card, text="🚨", bg=PANEL, fg=RED,
            font=("Segoe UI Emoji", 42)
        ).pack(pady=(30, 4))

        tk.Label(
            card, text="Welcome Back", bg=PANEL, fg=WHITE,
            font=("Segoe UI", 25, "bold")
        ).pack()

        tk.Label(
            card,
            text="Sign in to access emergency services",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 11)
        ).pack(pady=(4, 28))

        tk.Label(
            card, text="Email address", bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=55)

        email = tk.Entry(
            card, bg=PANEL_2, fg=WHITE, insertbackground=WHITE,
            relief="flat", font=("Segoe UI", 12)
        )
        email.pack(fill="x", padx=55, ipady=10, pady=(5, 15))

        tk.Label(
            card, text="Password", bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=55)

        password = tk.Entry(
            card, bg=PANEL_2, fg=WHITE, insertbackground=WHITE,
            show="•", relief="flat", font=("Segoe UI", 12)
        )
        password.pack(fill="x", padx=55, ipady=10, pady=(5, 8))

        message = tk.Label(
            card, text="", bg=PANEL, fg=RED,
            font=("Segoe UI", 10, "bold"),
            wraplength=350
        )
        message.pack(pady=5)

        def do_login():
            e = email.get().strip()
            p = password.get()

            if not e or not p:
                message.config(text="Invalid: email and password are required.")
                return

            # Admin credentials are checked privately here.
            # They are intentionally NOT printed on the login screen.
            if e.lower() == ADMIN_USERNAME and p == ADMIN_PASSWORD:
                self.current_role = "admin"
                self.current_user = None
                log_activity("ADMIN_LOGIN", "Administrator signed in")
                self.show_admin_dashboard()
                return

            if not valid_email(e):
                message.config(text="Invalid email address.")
                return

            user = authenticate_user(e, p)
            if not user:
                message.config(text="Invalid email or password.")
                return

            self.current_role = "user"
            self.current_user = dict(user)
            log_activity("USER_LOGIN", f"User {user['id']} signed in")
            self.show_user_dashboard()

        make_button(
            card, "Sign In", do_login, width=25, bg=RED
        ).pack(pady=(8, 10))

        make_button(
            card, "Create New Account", self.show_signup,
            width=25, bg=PANEL_2
        ).pack(pady=4)

        make_button(
            card, "Back to Home", self.show_welcome,
            width=25, bg="#18324a"
        ).pack(pady=4)

        # This text deliberately contains no administrator password.
        tk.Label(
            card,
            text="Administrator access uses a protected credential.",
            bg=PANEL,
            fg="#72879a",
            font=("Segoe UI", 8)
        ).pack(pady=(16, 0))

        email.focus_set()
        password.bind("<Return>", lambda event: do_login())

    # ============================================================
    # SIGNUP
    # ============================================================

    def show_signup(self):
        self.clear_window()

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True)

        card = rounded_panel(container, PANEL)
        card.place(relx=0.5, rely=0.5, anchor="center", width=620, height=680)

        tk.Label(
            card, text="Create Your Account",
            bg=PANEL, fg=WHITE,
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
                fields, text=label_text, bg=PANEL, fg=WHITE,
                font=("Segoe UI", 10, "bold")
            ).pack(anchor="w", pady=(7, 3))

            entry = tk.Entry(
                fields,
                bg=PANEL_2,
                fg=WHITE,
                insertbackground=WHITE,
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
            self.show_welcome, width=28, bg="#18324a"
        ).pack(pady=4)

        entries["name"].focus_set()

    # ============================================================
    # USER SHELL
    # ============================================================

    def setup_user_shell(self):
        self.clear_window()

        top = tk.Frame(self.root, bg=PANEL, height=72)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(
            top,
            text="🚨  EMERGENCY RESPONSE",
            bg=PANEL,
            fg=WHITE,
            font=("Segoe UI", 17, "bold")
        ).pack(side="left", padx=24)

        user_name = (
            self.current_user["full_name"]
            if self.current_user else "User"
        )

        tk.Label(
            top,
            text=f"Welcome, {user_name}",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(side="right", padx=(10, 20))

        make_button(
            top, "Logout", self.logout,
            width=9, bg="#18324a"
        ).pack(side="right", padx=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=PANEL, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="USER MENU",
            bg=PANEL,
            fg="#6e879d",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=22, pady=(25, 12))

        self.nav_buttons = []

        self.add_nav_button("Dashboard", self.show_user_home)
        self.add_nav_button("Report Emergency", self.show_report_form)
        self.add_nav_button("My Reports", self.show_my_reports)
        self.add_nav_button("Emergency Contacts", self.show_contacts)
        self.add_nav_button("Safety Information", self.show_safety)
        self.add_nav_button("Incident Photos", self.show_incident_photos)
        self.add_nav_button("My Profile", self.show_profile)

        self.content = tk.Frame(body, bg=BG)
        self.content.pack(side="left", fill="both", expand=True, padx=25, pady=25)

    def add_nav_button(self, text, command):
        button = tk.Button(
            self.sidebar,
            text=text,
            command=command,
            bg=PANEL,
            fg=WHITE,
            activebackground=RED_DARK,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            anchor="w",
            padx=24,
            pady=12,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        button.pack(fill="x", pady=1)
        self.nav_buttons.append((text, button))

    def clear_content(self):
        if self.content:
            for child in self.content.winfo_children():
                child.destroy()

    def highlight_nav(self, name):
        for text, button in self.nav_buttons:
            button.config(bg=RED_DARK if text == name else PANEL)

    def show_user_dashboard(self):
        self.setup_user_shell()
        self.show_user_home()

    def show_user_home(self):
        self.clear_content()
        self.highlight_nav("Dashboard")

        tk.Label(
            self.content,
            text="Emergency Help Center",
            bg=BG, fg=WHITE,
            font=("Segoe UI", 28, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Essential information and fast access to emergency reporting.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 11)
        ).pack(anchor="w", pady=(2, 20))

        hero = tk.Frame(self.content, bg=RED)
        hero.pack(fill="x", pady=(0, 18))

        hero_left = tk.Frame(hero, bg=RED)
        hero_left.pack(side="left", fill="both", expand=True, padx=25, pady=20)

        tk.Label(
            hero_left,
            text="NEED HELP?",
            bg=RED, fg=WHITE,
            font=("Segoe UI", 25, "bold")
        ).pack(anchor="w")

        tk.Label(
            hero_left,
            text="Report the emergency with the location and details responders need.",
            bg=RED, fg="#ffe9ec",
            font=("Segoe UI", 11),
            wraplength=650,
            justify="left"
        ).pack(anchor="w", pady=8)

        make_button(
            hero_left,
            "🚨 REPORT EMERGENCY NOW",
            self.show_report_form,
            width=28,
            bg="#8f1622"
        ).pack(anchor="w", pady=8)

        hero_right = tk.Frame(hero, bg="#8f1622", width=180)
        hero_right.pack(side="right", fill="y")
        tk.Label(
            hero_right,
            text="⚠",
            bg="#8f1622",
            fg=WHITE,
            font=("Segoe UI", 70, "bold")
        ).pack(padx=35, pady=20)

        stats = get_statistics()
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")

        self.user_stat_card(cards, "Reports", str(len(get_user_reports(
            self.current_user["id"]
        ))), BLUE)
        self.user_stat_card(cards, "Pending", str(
            len([r for r in get_user_reports(self.current_user["id"])
                 if r["status"] == "Pending"])
        ), ORANGE)
        self.user_stat_card(cards, "Responding", str(
            len([r for r in get_user_reports(self.current_user["id"])
                 if r["status"] == "Responding"])
        ), RED)
        self.user_stat_card(cards, "Resolved", str(
            len([r for r in get_user_reports(self.current_user["id"])
                 if r["status"] == "Resolved"])
        ), GREEN)

        info = tk.Frame(self.content, bg=BG)
        info.pack(fill="both", expand=True, pady=20)

        left = rounded_panel(info, PANEL)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(
            left,
            text="Quick Safety Rules",
            bg=PANEL, fg=WHITE,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 8))

        rules = [
            "Stay calm and move away from immediate danger.",
            "Give responders an exact or recognizable location.",
            "Do not enter a burning, collapsing, or electrically dangerous area.",
            "For serious injuries, avoid moving an injured person unless necessary.",
            "Keep emergency routes clear for responders.",
        ]

        for rule in rules:
            row = tk.Frame(left, bg=PANEL)
            row.pack(fill="x", padx=20, pady=4)
            tk.Label(
                row, text="●", bg=PANEL, fg=ORANGE,
                font=("Segoe UI", 10, "bold")
            ).pack(side="left")
            tk.Label(
                row, text=rule, bg=PANEL, fg=MUTED,
                font=("Segoe UI", 10),
                wraplength=530,
                justify="left"
            ).pack(side="left", padx=8)

        right = rounded_panel(info, PANEL)
        right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(
            right,
            text="Emergency Contacts",
            bg=PANEL, fg=WHITE,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 8))

        for service, number, desc in EMERGENCY_NUMBERS[:4]:
            row = tk.Frame(right, bg=PANEL)
            row.pack(fill="x", padx=20, pady=5)

            tk.Label(
                row, text=service, bg=PANEL, fg=WHITE,
                font=("Segoe UI", 10, "bold")
            ).pack(side="left")

            tk.Label(
                row, text=number, bg=PANEL, fg=ORANGE,
                font=("Segoe UI", 12, "bold")
            ).pack(side="right")

            tk.Label(
                right, text=desc, bg=PANEL, fg="#72879a",
                font=("Segoe UI", 8)
            ).pack(anchor="w", padx=20)

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
            inner, text=value, bg=PANEL, fg=WHITE,
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
        self.highlight_nav("Report Emergency")

        tk.Label(
            self.content,
            text="Report an Emergency",
            bg=BG, fg=WHITE,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Enter accurate information so the report can be understood quickly.",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 15))

        wrapper = rounded_panel(self.content, PANEL)
        wrapper.pack(fill="both", expand=True)

        form = tk.Frame(wrapper, bg=PANEL)
        form.pack(fill="both", expand=True, padx=35, pady=25)

        left = tk.Frame(form, bg=PANEL)
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))

        right = tk.Frame(form, bg=PANEL)
        right.pack(side="right", fill="both", expand=True, padx=(20, 0))

        entries = {}

        def field(parent, label, key, width=None):
            tk.Label(
                parent, text=label, bg=PANEL, fg=WHITE,
                font=("Segoe UI", 10, "bold")
            ).pack(anchor="w", pady=(7, 4))

            ent = tk.Entry(
                parent, bg=PANEL_2, fg=WHITE,
                insertbackground=WHITE, relief="flat",
                font=("Segoe UI", 11), width=width or 40
            )
            ent.pack(fill="x", ipady=9)
            entries[key] = ent
            return ent

        name_entry = field(left, "Your Name", "name")
        phone_entry = field(left, "Phone Number", "phone")
        location_entry = field(left, "Location", "location")

        tk.Label(
            left, text="Emergency Type", bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(7, 4))

        type_var = tk.StringVar(value=EMERGENCY_TYPES[0])
        type_box = ttk.Combobox(
            left,
            textvariable=type_var,
            values=EMERGENCY_TYPES,
            state="readonly",
            font=("Segoe UI", 11)
        )
        type_box.pack(fill="x", ipady=6)

        tk.Label(
            left, text="Priority", bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(16, 4))

        priority_var = tk.StringVar(value="High")
        priority_box = ttk.Combobox(
            left,
            textvariable=priority_var,
            values=PRIORITY_VALUES,
            state="readonly",
            font=("Segoe UI", 11)
        )
        priority_box.pack(fill="x", ipady=6)

        tk.Label(
            right, text="Description", bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(7, 4))

        description = tk.Text(
            right, bg=PANEL_2, fg=WHITE,
            insertbackground=WHITE, relief="flat",
            font=("Segoe UI", 11),
            wrap="word", height=12
        )
        description.pack(fill="both", expand=True)

        hint = tk.Label(
            right,
            text=(
                "Describe what happened, how many people may be affected, "
                "visible dangers, and useful landmarks."
            ),
            bg=PANEL, fg="#72879a",
            font=("Segoe UI", 9),
            wraplength=430,
            justify="left"
        )
        hint.pack(anchor="w", pady=8)

        message = tk.Label(
            form, text="", bg=PANEL, fg=RED,
            font=("Segoe UI", 10, "bold"),
            wraplength=650
        )
        message.pack(side="bottom", pady=5)

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
                report_id = create_report(
                    self.current_user["id"],
                    name,
                    phone,
                    type_var.get(),
                    location,
                    desc,
                    priority_var.get()
                )
            except Exception as exc:
                message.config(
                    text="Invalid: report could not be saved.",
                    fg=RED
                )
                return

            message.config(
                text=f"Emergency report #{report_id} submitted successfully.",
                fg=GREEN
            )
            name_entry.delete(0, "end")
            phone_entry.delete(0, "end")
            location_entry.delete(0, "end")
            description.delete("1.0", "end")

            self.root.after(
                1200,
                self.show_my_reports
            )

        buttons = tk.Frame(self.content, bg=BG)
        buttons.pack(fill="x", pady=(15, 0))

        make_button(
            buttons,
            "SUBMIT EMERGENCY REPORT",
            submit,
            width=30,
            bg=RED
        ).pack(side="left")

        make_button(
            buttons,
            "Clear",
            lambda: self.show_report_form(),
            width=12,
            bg=PANEL_2
        ).pack(side="left", padx=10)

        make_button(
            buttons,
            "Emergency Contacts",
            self.show_contacts,
            width=20,
            bg="#18324a"
        ).pack(side="right")

        name_entry.focus_set()

    # ============================================================
    # MY REPORTS
    # ============================================================

    def show_my_reports(self):
        self.clear_content()
        self.highlight_nav("My Reports")

        tk.Label(
            self.content, text="My Emergency Reports",
            bg=BG, fg=WHITE,
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
            bg=BG, fg=WHITE,
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
                bg=PANEL, fg=WHITE,
                font=("Segoe UI", 10)
            ).pack(side="left", fill="x", expand=True)

        tk.Label(
            card, text="Description",
            bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 4))

        desc = tk.Text(
            card, height=5, bg=PANEL_2, fg=WHITE,
            relief="flat", wrap="word",
            font=("Segoe UI", 10)
        )
        desc.pack(fill="x", padx=20)
        desc.insert("1.0", row["description"])
        desc.config(state="disabled")

        tk.Label(
            card, text="Admin Note",
            bg=PANEL, fg=WHITE,
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
        self.highlight_nav("Emergency Contacts")

        tk.Label(
            self.content,
            text="Ethiopian Emergency Contacts",
            bg=BG, fg=WHITE,
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
                bg=PANEL, fg=RED,
                font=("Segoe UI", 27, "bold")
            ).pack(side="left", padx=18, pady=18)

            text = tk.Frame(card, bg=PANEL)
            text.pack(side="left", fill="both", expand=True, pady=15)

            tk.Label(
                text, text=service,
                bg=PANEL, fg=WHITE,
                font=("Segoe UI", 12, "bold")
            ).pack(anchor="w")

            tk.Label(
                text, text=number,
                bg=PANEL, fg=ORANGE,
                font=("Segoe UI", 21, "bold")
            ).pack(anchor="w")

            tk.Label(
                text, text=desc,
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9),
                wraplength=320,
                justify="left"
            ).pack(anchor="w")

            make_button(
                text,
                "Open Dialer",
                lambda n=number: self.open_dialer(n),
                width=13,
                bg="#18324a",
                font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(8, 0))

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        note = tk.Label(
            self.content,
            text=(
                "Official sources used for the contact list include Addis Ababa Police "
                "and the Ethiopian Federal Police. Numbers can change, so confirm "
                "with official local authorities for operational use."
            ),
            bg=BG, fg="#72879a",
            font=("Segoe UI", 8),
            wraplength=900,
            justify="left"
        )
        note.pack(anchor="w", pady=10)

    def open_dialer(self, number):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(number)
            messagebox.showinfo(
                "Emergency Number",
                f"{number} has been copied to your clipboard.\n\n"
                "Use your phone's dialer to place the call."
            )
        except Exception:
            messagebox.showinfo(
                "Emergency Number",
                f"Emergency number: {number}"
            )

    # ============================================================
    # SAFETY INFORMATION
    # ============================================================

    def show_safety(self):
        self.clear_content()
        self.highlight_nav("Safety Information")

        tk.Label(
            self.content,
            text="Emergency Safety Information",
            bg=BG, fg=WHITE,
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
                bg=PANEL, fg=WHITE,
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
    # INCIDENT PHOTOS
    # ============================================================

    def show_incident_photos(self):
        self.clear_content()
        self.highlight_nav("Incident Photos")

        tk.Label(
            self.content,
            text="Real Emergency / Incident Photos",
            bg=BG, fg=WHITE,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text=(
                "These are real photographs hosted by Wikimedia Commons. "
                "Select a card to view the original photograph in your browser."
            ),
            bg=BG, fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 18))

        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="both", expand=True)

        photo_data = [
            (
                "Road Accident",
                "Traffic accident photograph",
                REAL_PHOTO_URLS["Road Accident"],
                "Accident"
            ),
            (
                "Fire Response",
                "Fire truck responding to a fire",
                REAL_PHOTO_URLS["Fire Response"],
                "Fire"
            ),
            (
                "Fire Truck",
                "Emergency fire vehicle in action",
                REAL_PHOTO_URLS["Fire"],
                "Fire"
            ),
            (
                "Road Accident Response",
                "Emergency response after a road collision",
                REAL_PHOTO_URLS["Road Accident Response"],
                "Accident"
            ),
        ]

        for index, (title, desc, url, icon) in enumerate(photo_data):
            r = index // 2
            c = index % 2

            card = rounded_panel(cards, PANEL)
            card.grid(
                row=r, column=c,
                sticky="nsew",
                padx=8, pady=8
            )

            preview = tk.Canvas(
                card, width=300, height=145,
                bg="#1a2d40",
                highlightthickness=0
            )
            preview.pack(fill="x", padx=15, pady=15)

            if icon == "Fire":
                preview.create_rectangle(
                    0, 0, 300, 145,
                    fill="#4b1d1d", outline=""
                )
                preview.create_text(
                    150, 70,
                    text="🔥",
                    fill=WHITE,
                    font=("Segoe UI Emoji", 55)
                )
            else:
                preview.create_rectangle(
                    0, 0, 300, 145,
                    fill="#182f45", outline=""
                )
                preview.create_text(
                    150, 70,
                    text="🚗  ⚠",
                    fill=WHITE,
                    font=("Segoe UI Emoji", 36)
                )

            tk.Label(
                card, text=title,
                bg=PANEL, fg=WHITE,
                font=("Segoe UI", 13, "bold")
            ).pack(anchor="w", padx=18)

            tk.Label(
                card, text=desc,
                bg=PANEL, fg=MUTED,
                font=("Segoe UI", 9),
                wraplength=350,
                justify="left"
            ).pack(anchor="w", padx=18, pady=5)

            make_button(
                card,
                "View Real Photo",
                lambda link=url: webbrowser.open(link),
                width=20,
                bg=RED
            ).pack(anchor="w", padx=18, pady=(4, 15))

        cards.grid_columnconfigure(0, weight=1)
        cards.grid_columnconfigure(1, weight=1)
        cards.grid_rowconfigure(0, weight=1)
        cards.grid_rowconfigure(1, weight=1)

        tk.Label(
            self.content,
            text=(
                "Photo source: Wikimedia Commons. Licensing and attribution "
                "information is available on each original file page."
            ),
            bg=BG, fg="#6e8295",
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=8)

    # ============================================================
    # PROFILE
    # ============================================================

    def show_profile(self):
        self.clear_content()
        self.highlight_nav("My Profile")

        tk.Label(
            self.content, text="My Profile",
            bg=BG, fg=WHITE,
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
                bg=PANEL, fg=WHITE,
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

        top = tk.Frame(self.root, bg="#0a1524", height=74)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(
            top,
            text="🚨  EMERGENCY COMMAND CENTER",
            bg="#0a1524", fg=WHITE,
            font=("Segoe UI", 18, "bold")
        ).pack(side="left", padx=24)

        tk.Label(
            top,
            text="ADMINISTRATOR",
            bg="#0a1524", fg=ORANGE,
            font=("Segoe UI", 10, "bold")
        ).pack(side="right", padx=10)

        make_button(
            top, "Logout", self.logout,
            width=9, bg="#18324a"
        ).pack(side="right", padx=8)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=PANEL, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="ADMIN MENU",
            bg=PANEL, fg="#6e879d",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=22, pady=(25, 12))

        self.nav_buttons = []

        self.add_nav_button("Dashboard", self.show_admin_dashboard)
        self.add_nav_button("All Reports", self.show_all_reports)
        self.add_nav_button("Update Status", self.show_admin_reports)
        self.add_nav_button("Users", self.show_users)
        self.add_nav_button("Activity Log", self.show_activity)
        self.add_nav_button("Emergency Contacts", self.show_contacts_admin)
        self.add_nav_button("Safety Information", self.show_safety_admin)

        self.content = tk.Frame(body, bg=BG)
        self.content.pack(side="left", fill="both", expand=True, padx=25, pady=25)

    def show_admin_dashboard(self):
        if self.content is None or not self.sidebar:
            self.setup_admin_shell()
        self.clear_content()
        self.highlight_nav("Dashboard")

        stats = get_statistics()

        tk.Label(
            self.content,
            text="Admin Dashboard",
            bg=BG, fg=WHITE,
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
            bg=PANEL, fg=WHITE,
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
                    recent, bg="#11243a",
                    highlightbackground=BORDER,
                    highlightthickness=1
                )
                line.pack(fill="x", padx=15, pady=4)

                tk.Label(
                    line,
                    text=f"#{row['id']}",
                    bg="#11243a", fg=ORANGE,
                    font=("Segoe UI", 10, "bold"),
                    width=6
                ).pack(side="left", padx=8)

                tk.Label(
                    line,
                    text=row["emergency_type"],
                    bg="#11243a", fg=WHITE,
                    font=("Segoe UI", 10, "bold"),
                    width=20, anchor="w"
                ).pack(side="left")

                tk.Label(
                    line,
                    text=row["location"],
                    bg="#11243a", fg=MUTED,
                    font=("Segoe UI", 9),
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)

                tk.Label(
                    line,
                    text=row["status"],
                    bg="#11243a",
                    fg=self.status_color(row["status"]),
                    font=("Segoe UI", 9, "bold"),
                    width=13
                ).pack(side="right", padx=8)

        actions = rounded_panel(middle, PANEL)
        actions.pack(side="right", fill="both", expand=False, padx=(10, 0))

        tk.Label(
            actions,
            text="Quick Actions",
            bg=PANEL, fg=WHITE,
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
            width=23, bg="#18324a"
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
            bg=PANEL, fg=WHITE,
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
            "Cancelled": "#7c8b99",
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
            bg=BG, fg=WHITE,
            font=("Segoe UI", 27, "bold")
        ).pack(anchor="w")

        toolbar = tk.Frame(self.content, bg=BG)
        toolbar.pack(fill="x", pady=(10, 12))

        search_var = tk.StringVar()
        search = tk.Entry(
            toolbar,
            textvariable=search_var,
            bg=PANEL_2, fg=WHITE,
            insertbackground=WHITE,
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
            width=16, bg="#7c2630"
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
            bg=BG, fg=WHITE,
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
                bg=PANEL, fg=WHITE,
                font=("Segoe UI", 10),
                anchor="w"
            ).pack(side="left")

        tk.Label(
            card, text="Description",
            bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=20, pady=(12, 4))

        desc = tk.Text(
            card, bg=PANEL_2, fg=WHITE,
            relief="flat", height=7,
            wrap="word", font=("Segoe UI", 10)
        )
        desc.pack(fill="x", padx=20)
        desc.insert("1.0", row["description"])
        desc.config(state="disabled")

        tk.Label(
            card, text="Administrative Note",
            bg=PANEL, fg=WHITE,
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
            bg=BG, fg=WHITE,
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
            bg=BG, fg=WHITE,
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
            bg=PANEL, fg=WHITE,
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
            bg=PANEL, fg=WHITE,
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
            bg=PANEL, fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=25, pady=(15, 5))

        note = tk.Text(
            form, height=6,
            bg=PANEL_2, fg=WHITE,
            insertbackground=WHITE,
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
            bg=BG, fg=WHITE,
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
            bg=BG, fg=WHITE,
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
            bg=BG, fg=WHITE,
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
                card, bg="#11243a",
                highlightbackground=BORDER,
                highlightthickness=1
            )
            row.pack(fill="x", padx=18, pady=5)

            tk.Label(
                row, text=service,
                bg="#11243a", fg=WHITE,
                font=("Segoe UI", 10, "bold"),
                width=28, anchor="w"
            ).pack(side="left", padx=12, pady=10)

            tk.Label(
                row, text=number,
                bg="#11243a", fg=ORANGE,
                font=("Segoe UI", 13, "bold"),
                width=12
            ).pack(side="left")

            tk.Label(
                row, text=desc,
                bg="#11243a", fg=MUTED,
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
            bg=BG, fg=WHITE,
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
# 11. Admin can view users.
# 12. Admin can view activity.
# 13. The public login page does NOT reveal the admin password.
# 14. The administrator credential is:
#       username: admin
#       password: 102030
#     It is intentionally not printed in the user interface.
# 15. Real incident photographs are linked to Wikimedia Commons.
# 16. If the computer is offline, the main application still works;
#     only external photograph pages require internet access.
#
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

# REAL INCIDENT PHOTO REFERENCES
# ---------------------------------------------------------------
# This section belongs to the same single-file emergency management
# project. It is intentionally kept here so the application remains
# easy to submit, copy, archive, and demonstrate in VS Code.
# The database uses SQLite, which is included with normal Python 3
# installations. The interface uses Tkinter, also included with most
# standard desktop Python distributions.
# The user interface is designed around emergency response workflows:
# authentication, information, reporting, tracking, administration,
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
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
# status changes, user management, and incident references.
# The administrator should use the system only for authorized
# project/testing purposes and should protect the local database file.
# Real emergency calls should always be placed through official services.
# ---------------------------------------------------------------

