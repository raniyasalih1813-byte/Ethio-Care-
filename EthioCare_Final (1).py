import os
import sqlite3
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

# ============================================================
# OPTIONAL WINDOWS NOTIFICATIONS
# ============================================================

try:
    from winotify import Notification, audio
    WIN_NOTIFY_AVAILABLE = True
except ImportError:
    WIN_NOTIFY_AVAILABLE = False


# ============================================================
# APPLICATION SETTINGS
# ============================================================

APP_NAME = "EthioCare"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "ethiocare_hospital.db"
DB_PATH = os.path.join(BASE_DIR, DB_NAME)


# ============================================================
# COLORS
# ============================================================

LIGHT_BG = "#f5f5f7"
LIGHT_CARD = "#ffffff"
LIGHT_TEXT = "#172033"
LIGHT_MUTED = "#667085"
LIGHT_BORDER = "#e5e5ea"
LIGHT_PRIMARY = "#007aff"
LIGHT_PRIMARY_DARK = "#005ecb"

DARK_BG = "#000000"
DARK_CARD = "#1c1c1e"
DARK_TEXT = "#f9fafb"
DARK_MUTED = "#aab4c3"
DARK_BORDER = "#38383a"
DARK_PRIMARY = "#0a84ff"
DARK_PRIMARY_DARK = "#006ee6"

SUCCESS = "#16a34a"
DANGER = "#dc2626"
WARNING = "#d97706"
INFO = "#2563eb"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


def setup_database():

    conn = get_db()
    cur = conn.cursor()

    # --------------------------------------------------------
    # PATIENTS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # HOSPITALS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            password TEXT NOT NULL,
            achievements TEXT DEFAULT '',
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # HOSPITAL MIGRATION
    # --------------------------------------------------------
    hospital_columns = {
        row["name"]
        for row in cur.execute("PRAGMA table_info(hospitals)").fetchall()
    }

    if "achievements" not in hospital_columns:
        cur.execute("ALTER TABLE hospitals ADD COLUMN achievements TEXT DEFAULT ''")

    if "status" not in hospital_columns:
        cur.execute("ALTER TABLE hospitals ADD COLUMN status TEXT DEFAULT 'Pending'")
        # Existing hospitals were already usable before approval was added.
        cur.execute("UPDATE hospitals SET status = 'Approved' WHERE status IS NULL OR status = ''")

    # --------------------------------------------------------
    # DOCTORS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            hospital TEXT NOT NULL,
            password TEXT NOT NULL,
            available TEXT DEFAULT 'Yes',
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # APPOINTMENTS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL,

            FOREIGN KEY(patient_id)
                REFERENCES patients(patient_id)
                ON DELETE CASCADE,

            FOREIGN KEY(doctor_id)
                REFERENCES doctors(doctor_id)
                ON DELETE CASCADE
        )
    """)

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            appointment_id INTEGER,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            status TEXT DEFAULT 'Paid',
            transaction_id TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY(patient_id)
                REFERENCES patients(patient_id)
                ON DELETE CASCADE,

            FOREIGN KEY(appointment_id)
                REFERENCES appointments(id)
                ON DELETE SET NULL
        )
    """)

    # --------------------------------------------------------
    # ADMINS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # NOTIFICATION LOG
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL,
            sent_at TEXT NOT NULL,

            UNIQUE(
                appointment_id,
                notification_type
            )
        )
    """)

    # --------------------------------------------------------
    # DEFAULT ADMIN
    # --------------------------------------------------------

    admin = cur.execute("""
        SELECT username
        FROM admins
        WHERE username = ?
    """, ("admin",)).fetchone()

    if admin is None:

        cur.execute("""
            INSERT INTO admins
            (username, password)
            VALUES (?, ?)
        """, (
            "admin",
            hash_password("admin123")
        ))

    conn.commit()
    conn.close()



# ============================================================
# LANGUAGE SYSTEM
# ============================================================
#
# The original program had a language selector, but almost all
# interface text was hard-coded in English.  The selector therefore
# changed the selected language value without translating the screen.
#
# This language layer keeps all existing features and translates the
# visible interface whenever a language is selected.
#

LANGUAGE_NAMES = {
    "en": "English",
    "am": "አማርኛ",
    "om": "Afaan Oromoo",
    "ti": "ትግርኛ",
}

TRANSLATIONS = {
    "en": {
        'Language': 'Language',
        'Home': 'Home',
        'Back': 'Back',
        'Logout': 'Logout',
        'Light': 'Light',
        'Dark': 'Dark',
        'Patient Services': 'Patient Services',
        'Hospital Services': 'Hospital Services',
        'Doctor Services': 'Doctor Services',
        'Emergency': 'Emergency',
        'Emergency Help': 'Emergency Help',
        'Online Payment': 'Online Payment',
        'Available Doctors': 'Available Doctors',
        'Find Healthcare': 'Find Healthcare',
        'Find Doctors & Hospitals': 'Find Doctors & Hospitals',
        'Search': 'Search',
        'Search Type': 'Search Type',
        'All': 'All',
        'Doctors': 'Doctors',
        'Hospitals': 'Hospitals',
        'Create Patient Account': 'Create Patient Account',
        'Patient Login': 'Patient Login',
        'Patient Registration': 'Patient Registration',
        'Patient Dashboard': 'Patient Dashboard',
        'My Profile': 'My Profile',
        'Patient ID': 'Patient ID',
        'Full Name': 'Full Name',
        'Age': 'Age',
        'Gender': 'Gender',
        'Male': 'Male',
        'Female': 'Female',
        'Other': 'Other',
        'Phone': 'Phone',
        'Phone Number': 'Phone Number',
        'Email': 'Email',
        'Address': 'Address',
        'Address / Location': 'Address / Location',
        'Password': 'Password',
        'Confirm Password': 'Confirm Password',
        'Show': 'Show',
        'Hide': 'Hide',
        'Create Account': 'Create Account',
        'Login': 'Login',
        'Register Hospital': 'Register Hospital',
        'Hospital Registration': 'Hospital Registration',
        'Hospital Login': 'Hospital Login',
        'Hospital Dashboard': 'Hospital Dashboard',
        'Hospital Name': 'Hospital Name',
        'Location': 'Location',
        'Full Address': 'Full Address',
        'Hospital Email': 'Hospital Email',
        'Register Doctor': 'Register Doctor',
        'Doctor Registration': 'Doctor Registration',
        'Doctor Login': 'Doctor Login',
        'Doctor Dashboard': 'Doctor Dashboard',
        'Doctor Full Name': 'Doctor Full Name',
        'Specialization': 'Specialization',
        'Doctor Email': 'Doctor Email',
        'Hospital': 'Hospital',
        'Book Appointment': 'Book Appointment',
        'Book Doctor Appointment': 'Book Doctor Appointment',
        'My Appointments': 'My Appointments',
        'Doctor Appointments': 'Doctor Appointments',
        'Appointment Date': 'Appointment Date',
        'Appointment Time': 'Appointment Time',
        'Reason / Symptoms': 'Reason / Symptoms',
        'Appointment': 'Appointment',
        'Notifications': 'Notifications',
        'Payment History': 'Payment History',
        'Make Payment': 'Make Payment',
        'Payment Method': 'Payment Method',
        'Amount (ETB)': 'Amount (ETB)',
        'Pay Now': 'Pay Now',
        'Telebirr': 'Telebirr',
        'CBE Birr': 'CBE Birr',
        'Bank Transfer': 'Bank Transfer',
        'Debit Card': 'Debit Card',
        'Cash at Hospital': 'Cash at Hospital',
        'Transaction ID (optional)': 'Transaction ID (optional)',
        'Admin Login': 'Admin Login',
        'Administrator Login': 'Administrator Login',
        'Admin Dashboard': 'Admin Dashboard',
        'Administrator Dashboard': 'Administrator Dashboard',
        'System Administration': 'System Administration',
        'All Patients': 'All Patients',
        'All Doctors': 'All Doctors',
        'All Hospitals': 'All Hospitals',
        'All Appointments': 'All Appointments',
        'All Payments': 'All Payments',
        'View All Patients': 'View All Patients',
        'View All Doctors': 'View All Doctors',
        'View All Hospitals': 'View All Hospitals',
        'View All Appointments': 'View All Appointments',
        'View All Payments': 'View All Payments',
        'Delete Patient': 'Delete Patient',
        'Delete Doctor': 'Delete Doctor',
        'Confirm': 'Confirm',
        'Cancel': 'Cancel',
        'Delete': 'Delete',
        'Pending': 'Pending',
        'Confirmed': 'Confirmed',
        'Cancelled': 'Cancelled',
        'Registered': 'Registered',
        'Our Services': 'Our Services',
        'Why EthioCare?': 'Why EthioCare?',
        'Emergency Safety Tips': 'Emergency Safety Tips',
        'Username': 'Username',
        'Status:': 'Status:',
        'Date:': 'Date:',
        'Time:': 'Time:',
        'Reason:': 'Reason:',
        'Patient:': 'Patient:',
        'Doctor:': 'Doctor:',
        'Specialization:': 'Specialization:',
        'Hospital:': 'Hospital:',
        'Phone:': 'Phone:',
        'Email:': 'Email:',
        'Address:': 'Address:',
        'Available:': 'Available:',
        'Method:': 'Method:',
        'Amount:': 'Amount:',
        'Transaction ID:': 'Transaction ID:',
        'Total Payments:': 'Total Payments:',
        'No results found.': 'No results found.',
        'No doctors are registered yet.': 'No doctors are registered yet.',
        'No doctors registered.': 'No doctors registered.',
        'No hospitals registered.': 'No hospitals registered.',
        'No patients registered.': 'No patients registered.',
        'No appointments.': 'No appointments.',
        'No appointments found.': 'No appointments found.',
        'No payments recorded.': 'No payments recorded.',
        'No payment history available.': 'No payment history available.',
        'No doctors are currently available.': 'No doctors are currently available.',
        'Call 911 / 907 / 991 for immediate emergency assistance.': 'Call 911 / 907 / 991 for immediate emergency assistance.',
    },
    "am": {
        "Language":"ቋንቋ","Home":"መነሻ","Back":"ተመለስ","Logout":"ውጣ",
        "Light":"ብርሃን","Dark":"ጨለማ","Patient Services":"የታካሚ አገልግሎቶች",
        "Hospital Services":"የሆስፒታል አገልግሎቶች","Doctor Services":"የዶክተር አገልግሎቶች",
        "Emergency":"አደጋ","Emergency Help":"የአደጋ እርዳታ","Online Payment":"የመስመር ላይ ክፍያ",
        "Available Doctors":"የሚገኙ ዶክተሮች","Find Healthcare":"የጤና አገልግሎት ፈልግ",
        "Find Doctors & Hospitals":"ዶክተሮችን እና ሆስፒታሎችን ፈልግ",
        "Search":"ፈልግ","Search Type":"የፍለጋ አይነት","All":"ሁሉም","Doctors":"ዶክተሮች","Hospitals":"ሆስፒታሎች",
        "Create Patient Account":"የታካሚ መለያ ፍጠር","Patient Login":"የታካሚ መግቢያ",
        "Patient Registration":"የታካሚ ምዝገባ","Patient Dashboard":"የታካሚ ዳሽቦርድ",
        "My Profile":"የእኔ መገለጫ","Patient ID":"የታካሚ መለያ","Full Name":"ሙሉ ስም","Age":"ዕድሜ",
        "Gender":"ጾታ","Male":"ወንድ","Female":"ሴት","Other":"ሌላ","Phone":"ስልክ","Phone Number":"የስልክ ቁጥር",
        "Email":"ኢሜይል","Address":"አድራሻ","Address / Location":"አድራሻ / አካባቢ",
        "Password":"የይለፍ ቃል","Confirm Password":"የይለፍ ቃል ያረጋግጡ","Show":"አሳይ","Hide":"ደብቅ",
        "Create Account":"መለያ ፍጠር","Login":"ግባ","Register Hospital":"ሆስፒታል መዝግብ",
        "Hospital Registration":"የሆስፒታል ምዝገባ","Hospital Login":"የሆስፒታል መግቢያ",
        "Hospital Dashboard":"የሆስፒታል ዳሽቦርድ","Hospital Name":"የሆስፒታል ስም",
        "Location":"አካባቢ","Full Address":"ሙሉ አድራሻ","Hospital Email":"የሆስፒታል ኢሜይል",
        "Register Doctor":"ዶክተር መዝግብ","Doctor Registration":"የዶክተር ምዝገባ","Doctor Login":"የዶክተር መግቢያ",
        "Doctor Dashboard":"የዶክተር ዳሽቦርድ","Doctor Full Name":"የዶክተሩ ሙሉ ስም",
        "Specialization":"ልዩ ሙያ","Doctor Email":"የዶክተር ኢሜይል","Hospital":"ሆስፒታል",
        "Book Appointment":"ቀጠሮ ያዝ","Book Doctor Appointment":"የዶክተር ቀጠሮ ያዝ",
        "My Appointments":"የእኔ ቀጠሮዎች","Doctor Appointments":"የዶክተር ቀጠሮዎች",
        "Appointment Date":"የቀጠሮ ቀን","Appointment Time":"የቀጠሮ ሰዓት","Reason / Symptoms":"ምክንያት / ምልክቶች",
        "Appointment":"ቀጠሮ","Notifications":"ማሳወቂያዎች","Payment History":"የክፍያ ታሪክ",
        "Make Payment":"ክፍያ ፈጽም","Payment Method":"የክፍያ ዘዴ","Amount (ETB)":"መጠን (ብር)",
        "Pay Now":"አሁን ክፈል","Telebirr":"ቴሌብር","CBE Birr":"ሲቢኢ ብር","Bank Transfer":"የባንክ ማስተላለፍ",
        "Debit Card":"ዴቢት ካርድ","Cash at Hospital":"በሆስፒታል ጥሬ ገንዘብ",
        "Transaction ID (optional)":"የግብይት መለያ (አማራጭ)","Admin Login":"የአስተዳዳሪ መግቢያ",
        "Administrator Login":"የአስተዳዳሪ መግቢያ","Admin Dashboard":"የአስተዳዳሪ ዳሽቦርድ",
        "Administrator Dashboard":"የአስተዳዳሪ ዳሽቦርድ","System Administration":"የስርዓት አስተዳደር",
        "All Patients":"ሁሉም ታካሚዎች","All Doctors":"ሁሉም ዶክተሮች","All Hospitals":"ሁሉም ሆስፒታሎች",
        "All Appointments":"ሁሉም ቀጠሮዎች","All Payments":"ሁሉም ክፍያዎች",
        "View All Patients":"ሁሉንም ታካሚዎች ይመልከቱ","View All Doctors":"ሁሉንም ዶክተሮች ይመልከቱ",
        "View All Hospitals":"ሁሉንም ሆስፒታሎች ይመልከቱ","View All Appointments":"ሁሉንም ቀጠሮዎች ይመልከቱ",
        "View All Payments":"ሁሉንም ክፍያዎች ይመልከቱ","Delete Patient":"ታካሚ ሰርዝ","Delete Doctor":"ዶክተር ሰርዝ",
        "Confirm":"አረጋግጥ","Cancel":"ሰርዝ","Delete":"ሰርዝ","Pending":"በመጠባበቅ ላይ",
        "Confirmed":"ተረጋግጧል","Cancelled":"ተሰርዟል","Registered":"የተመዘገበ",
        "Our Services":"አገልግሎቶቻችን","Why EthioCare?":"ለምን EthioCare?","Emergency Safety Tips":"የአደጋ ደህንነት ምክሮች",
        "Username":"የተጠቃሚ ስም","Status:":"ሁኔታ:","Date:":"ቀን:","Time:":"ሰዓት:","Reason:":"ምክንያት:",
        "Patient:":"ታካሚ:","Doctor:":"ዶክተር:","Specialization:":"ልዩ ሙያ:","Hospital:":"ሆስፒታል:",
        "Phone:":"ስልክ:","Email:":"ኢሜይል:","Address:":"አድራሻ:","Available:":"የሚገኝ:",
        "Method:":"ዘዴ:","Amount:":"መጠን:","Transaction ID:":"የግብይት መለያ:","Total Payments:":"ጠቅላላ ክፍያ:",
        "No results found.":"ውጤት አልተገኘም።","No doctors are registered yet.":"እስካሁን ምንም ዶክተር አልተመዘገበም።",
        "No doctors registered.":"ምንም ዶክተር አልተመዘገበም።","No hospitals registered.":"ምንም ሆስፒታል አልተመዘገበም።",
        "No patients registered.":"ምንም ታካሚ አልተመዘገበም።","No appointments.":"ምንም ቀጠሮ የለም።",
        "No appointments found.":"ምንም ቀጠሮ አልተገኘም።","No payments recorded.":"ምንም ክፍያ አልተመዘገበም።",
        "No payment history available.":"የክፍያ ታሪክ የለም።","No doctors are currently available.":"በአሁኑ ጊዜ ምንም የሚገኝ ዶክተር የለም።",
        "Show":"አሳይ","Hide":"ደብቅ",
        "Call 911 / 907 / 991 for immediate emergency assistance.":"ለአስቸኳይ እርዳታ 911 / 907 / 991 ይደውሉ።",
    },
    "om": {
        "Language":"Afaan","Home":"Mana","Back":"Deebi'i","Logout":"Ba'i","Light":"Ifa","Dark":"Dukkana",
        "Patient Services":"Tajaajila Dhukkubsataa","Hospital Services":"Tajaajila Hospitaalaa","Doctor Services":"Tajaajila Doktoraa",
        "Emergency":"Hatattamaa","Emergency Help":"Gargaarsa Hatattamaa","Online Payment":"Kaffaltii Toora Interneetii",
        "Available Doctors":"Doktoroota Argaman","Find Healthcare":"Tajaajila Fayyaa Barbaadi","Find Doctors & Hospitals":"Doktorootaa fi Hospitaalota Barbaadi",
        "Search":"Barbaadi","Search Type":"Gosa Barbaachaa","All":"Hunda","Doctors":"Doktoroota","Hospitals":"Hospitaalota",
        "Create Patient Account":"Herrega Dhukkubsataa Uumi","Patient Login":"Seensa Dhukkubsataa","Patient Registration":"Galmee Dhukkubsataa",
        "Patient Dashboard":"Daashboordii Dhukkubsataa","My Profile":"Piroofaayila Koo","Patient ID":"ID Dhukkubsataa",
        "Full Name":"Maqaa Guutuu","Age":"Umurii","Gender":"Saala","Male":"Dhiira","Female":"Dhalaa","Other":"Kan Biraa",
        "Phone":"Bilbila","Phone Number":"Lakkoofsa Bilbilaa","Email":"Imeelii","Address":"Teessoo","Address / Location":"Teessoo / Bakka",
        "Password":"Jecha Darbii","Confirm Password":"Jecha Darbii Mirkaneessi","Show":"Agarsiisi","Hide":"Dhoksi",
        "Create Account":"Herrega Uumi","Login":"Seeni","Register Hospital":"Hospitaala Galmeessi","Hospital Registration":"Galmee Hospitaalaa",
        "Hospital Login":"Seensa Hospitaalaa","Hospital Dashboard":"Daashboordii Hospitaalaa","Hospital Name":"Maqaa Hospitaalaa",
        "Location":"Bakka","Full Address":"Teessoo Guutuu","Hospital Email":"Imeelii Hospitaalaa","Register Doctor":"Doktora Galmeessi",
        "Doctor Registration":"Galmee Doktoraa","Doctor Login":"Seensa Doktoraa","Doctor Dashboard":"Daashboordii Doktoraa",
        "Doctor Full Name":"Maqaa Guutuu Doktoraa","Specialization":"Ogummaa Addaa","Doctor Email":"Imeelii Doktoraa","Hospital":"Hospitaala",
        "Book Appointment":"Beellama Qabadhu","Book Doctor Appointment":"Beellama Doktoraa Qabadhu","My Appointments":"Beellamoota Koo",
        "Doctor Appointments":"Beellamoota Doktoraa","Appointment Date":"Guyyaa Beellamaa","Appointment Time":"Yeroo Beellamaa",
        "Reason / Symptoms":"Sababa / Mallattoolee","Notifications":"Beeksisa","Payment History":"Seenaa Kaffaltii","Make Payment":"Kaffaltii Godhi",
        "Payment Method":"Mala Kaffaltii","Amount (ETB)":"Hanga (ETB)","Pay Now":"Amma Kaffali","Telebirr":"Telebirr","CBE Birr":"CBE Birr",
        "Bank Transfer":"Dabarsa Baankii","Debit Card":"Kaardii Deebitii","Cash at Hospital":"Maallaqa Hospitaalatti",
        "Transaction ID (optional)":"ID Daldalaa (filannoo)","Admin Login":"Seensa Bulchaa","Administrator Login":"Seensa Bulchaa",
        "Admin Dashboard":"Daashboordii Bulchaa","Administrator Dashboard":"Daashboordii Bulchaa","System Administration":"Bulchiinsa Sirnaa",
        "All Patients":"Dhukkubsattoota Hunda","All Doctors":"Doktoroota Hunda","All Hospitals":"Hospitaalota Hunda",
        "All Appointments":"Beellamoota Hunda","All Payments":"Kaffaltiiwwan Hunda","Delete Patient":"Dhukkubsataa Haqi","Delete Doctor":"Doktora Haqi",
        "Confirm":"Mirkaneessi","Cancel":"Haqi","Delete":"Haqi","Pending":"Eeggachaa Jira","Confirmed":"Mirkanaa'e","Cancelled":"Haqame",
        "Our Services":"Tajaajiloota Keenya","Why EthioCare?":"Maaliif EthioCare?","Emergency Safety Tips":"Gorsa Nageenya Hatattamaa",
        "Username":"Maqaa Fayyadamaa","Status:":"Haala:","Date:":"Guyyaa:","Time:":"Yeroo:","Reason:":"Sababa:","Patient:":"Dhukkubsataa:",
        "Doctor:":"Doktora:","Specialization:":"Ogummaa:","Hospital:":"Hospitaala:","Phone:":"Bilbila:","Email:":"Imeelii:",
        "Address:":"Teessoo:","Available:":"Argama:","Method:":"Mala:","Amount:":"Hanga:","Transaction ID:":"ID Daldalaa:","Total Payments:":"Kaffaltii Waliigalaa:",
        "No results found.":"Bu'aan hin argamne.","No doctors are registered yet.":"Hanga ammaatti doktorri hin galmoofne.",
        "No doctors registered.":"Doktorri hin galmoofne.","No hospitals registered.":"Hospitaalli hin galmoofne.",
        "No patients registered.":"Dhukkubsataan hin galmoofne.","No appointments.":"Beellamni hin jiru.","No appointments found.":"Beellamni hin argamne.",
        "No payments recorded.":"Kaffaltiin hin galmoofne.","No payment history available.":"Seenaa kaffaltii hin jiru.",
        "No doctors are currently available.":"Amma doktorri argamu hin jiru.",
        "Call 911 / 907 / 991 for immediate emergency assistance.":"Gargaarsa hatattamaaf 911 / 907 / 991 irratti bilbili.",
    },
    "ti": {
        "Language":"ቋንቋ","Home":"ቀንዲ ገጽ","Back":"ተመለስ","Logout":"ውጻእ","Light":"ብርሃን","Dark":"ጸልማት",
        "Patient Services":"ኣገልግሎት ሕሙማት","Hospital Services":"ኣገልግሎት ሆስፒታል","Doctor Services":"ኣገልግሎት ሓኪም",
        "Emergency":"ህጹጽ","Emergency Help":"ህጹጽ ሓገዝ","Online Payment":"ኦንላይን ክፍሊት",
        "Available Doctors":"ዝርከቡ ሓካይም","Find Healthcare":"ኣገልግሎት ጥዕና ድለ","Find Doctors & Hospitals":"ሓካይምን ሆስፒታላትን ድለ",
        "Search":"ድለ","Search Type":"ዓይነት ምድላይ","All":"ኩሎም","Doctors":"ሓካይም","Hospitals":"ሆስፒታላት",
        "Create Patient Account":"ናይ ሕሙም ኣካውንት ፍጠር","Patient Login":"መእተዊ ሕሙም","Patient Registration":"ምዝገባ ሕሙም",
        "Patient Dashboard":"ዳሽቦርድ ሕሙም","My Profile":"ፕሮፋይለይ","Patient ID":"መለለዪ ሕሙም",
        "Full Name":"ምሉእ ስም","Age":"ዕድመ","Gender":"ጾታ","Male":"ተባዕታይ","Female":"ኣንስታይ","Other":"ካልእ",
        "Phone":"ተሌፎን","Phone Number":"ቁጽሪ ተሌፎን","Email":"ኢመይል","Address":"ኣድራሻ","Address / Location":"ኣድራሻ / ቦታ",
        "Password":"መሕለፊ ቃል","Confirm Password":"መሕለፊ ቃል ኣረጋግጽ","Show":"ኣርእይ","Hide":"ሓብእ",
        "Create Account":"ኣካውንት ፍጠር","Login":"እቶ","Register Hospital":"ሆስፒታል መዝግብ","Hospital Registration":"ምዝገባ ሆስፒታል",
        "Hospital Login":"መእተዊ ሆስፒታል","Hospital Dashboard":"ዳሽቦርድ ሆስፒታል","Hospital Name":"ስም ሆስፒታል",
        "Location":"ቦታ","Full Address":"ምሉእ ኣድራሻ","Hospital Email":"ኢመይል ሆስፒታል","Register Doctor":"ሓኪም መዝግብ",
        "Doctor Registration":"ምዝገባ ሓኪም","Doctor Login":"መእተዊ ሓኪም","Doctor Dashboard":"ዳሽቦርድ ሓኪም",
        "Doctor Full Name":"ምሉእ ስም ሓኪም","Specialization":"ፍሉይ ሙያ","Doctor Email":"ኢመይል ሓኪም","Hospital":"ሆስፒታል",
        "Book Appointment":"ቆጸራ ሓዝ","Book Doctor Appointment":"ቆጸራ ሓኪም ሓዝ","My Appointments":"ቆጸራታተይ",
        "Doctor Appointments":"ቆጸራታት ሓኪም","Appointment Date":"ዕለት ቆጸራ","Appointment Time":"ሰዓት ቆጸራ",
        "Reason / Symptoms":"ምኽንያት / ምልክታት","Notifications":"ሓበሬታታት","Payment History":"ታሪኽ ክፍሊት","Make Payment":"ክፍሊት ግበር",
        "Payment Method":"ኣገባብ ክፍሊት","Amount (ETB)":"መጠን (ETB)","Pay Now":"ሕጂ ክፈል","Telebirr":"ቴሌብር","CBE Birr":"CBE ብር",
        "Bank Transfer":"ምስግጋር ባንኪ","Debit Card":"ዴቢት ካርድ","Cash at Hospital":"ጥረ ገንዘብ ኣብ ሆስፒታል",
        "Transaction ID (optional)":"መለለዪ ግብይት (ኣማራጺ)","Admin Login":"መእተዊ ኣስተዳደር",
        "Administrator Login":"መእተዊ ኣስተዳደር","Admin Dashboard":"ዳሽቦርድ ኣስተዳደር","Administrator Dashboard":"ዳሽቦርድ ኣስተዳደር",
        "System Administration":"ኣስተዳደር ስርዓት","All Patients":"ኩሎም ሕሙማት","All Doctors":"ኩሎም ሓካይም",
        "All Hospitals":"ኩሎም ሆስፒታላት","All Appointments":"ኩሎም ቆጸራታት","All Payments":"ኩሎም ክፍሊታት",
        "Delete Patient":"ሕሙም ሰርዝ","Delete Doctor":"ሓኪም ሰርዝ","Confirm":"ኣረጋግጽ","Cancel":"ሰርዝ","Delete":"ሰርዝ",
        "Pending":"ኣብ ትጽቢት","Confirmed":"ተረጋጊጹ","Cancelled":"ተሰሪዙ","Registered":"ተመዝጊቡ",
        "Our Services":"ኣገልግሎታትና","Why EthioCare?":"ስለምንታይ EthioCare?","Emergency Safety Tips":"ምኽሪ ድሕነት ህጹጽ",
        "Username":"ስም ተጠቃሚ","Status:":"ኩነታት:","Date:":"ዕለት:","Time:":"ሰዓት:","Reason:":"ምኽንያት:","Patient:":"ሕሙም:",
        "Doctor:":"ሓኪም:","Specialization:":"ፍሉይ ሙያ:","Hospital:":"ሆስፒታል:","Phone:":"ተሌፎን:","Email:":"ኢመይል:",
        "Address:":"ኣድራሻ:","Available:":"ይርከብ:","Method:":"ኣገባብ:","Amount:":"መጠን:","Transaction ID:":"መለለዪ ግብይት:",
        "Total Payments:":"ጠቕላላ ክፍሊት:","No results found.":"ውጽኢት ኣይተረኽበን።",
        "No doctors are registered yet.":"ክሳብ ሕጂ ሓኪም ኣይተመዝገበን።","No doctors registered.":"ሓካይም ኣይተመዝገቡን።",
        "No hospitals registered.":"ሆስፒታላት ኣይተመዝገቡን።","No patients registered.":"ሕሙማት ኣይተመዝገቡን።",
        "No appointments.":"ቆጸራ የለን።","No appointments found.":"ቆጸራ ኣይተረኽበን።","No payments recorded.":"ክፍሊት ኣይተመዝገበን።",
        "No payment history available.":"ታሪኽ ክፍሊት የለን።","No doctors are currently available.":"ኣብዚ ግዜ ዝርከብ ሓኪም የለን።",
        "Call 911 / 907 / 991 for immediate emergency assistance.":"ንህጹጽ ሓገዝ 911 / 907 / 991 ደውል።",
    }
}

# Additional Amharic translations for interface text that is created
# directly inside individual pages.  These are merged into the existing
# Amharic dictionary so every visible English UI string is localized.
HERO_TRANSLATIONS = {
    "en": {
        "Smart Healthcare,\nMade Simple": "Smart Healthcare,\nMade Simple",
        "Access patient services, doctors, hospitals,\napointments and payments from one place.": "Access patient services, doctors, hospitals,\napointments and payments from one place.",
        "Patient Services": "Patient Services",
        "Emergency Help": "Emergency Help",
    },
    "am": {
        "Smart Healthcare,\nMade Simple": "ዘመናዊ የጤና አገልግሎት፣\nቀላል እና ቀልጣፋ",
        "Access patient services, doctors, hospitals,\napointments and payments from one place.": "የታካሚ አገልግሎቶችን፣ ዶክተሮችን፣ ሆስፒታሎችን፣\nቀጠሮዎችን እና ክፍያዎችን ከአንድ ቦታ ያግኙ።",
        "Patient Services": "የታካሚ አገልግሎቶች",
        "Emergency Help": "የአደጋ እርዳታ",
    },
    "om": {
        "Smart Healthcare,\nMade Simple": "Kunuunsa Fayyaa Ammayyaa,\nSalphaa Taasifame",
        "Access patient services, doctors, hospitals,\napointments and payments from one place.": "Tajaajila dhukkubsataa, doktoroota, hospitaalota,\nbeellamoota fi kaffaltii bakka tokko irraa argadhaa.",
        "Patient Services": "Tajaajila Dhukkubsataa",
        "Emergency Help": "Gargaarsa Hatattamaa",
    },
    "ti": {
        "Smart Healthcare,\nMade Simple": "ዘመናዊ ኣገልግሎት ጥዕና፣\nቀሊል ዝኾነ",
        "Access patient services, doctors, hospitals,\napointments and payments from one place.": "ኣገልግሎት ሕሙማት፣ ሓካይም፣ ሆስፒታላት፣\nቆጸራታትን ክፍሊታትን ካብ ሓደ ቦታ ረኽቡ።",
        "Patient Services": "ኣገልግሎት ሕሙማት",
        "Emergency Help": "ህጹጽ ሓገዝ",
    },
}

for _lang, _hero_table in HERO_TRANSLATIONS.items():
    TRANSLATIONS[_lang].update(_hero_table)

AMHARIC_EXTRA_TRANSLATIONS = {
    "Smart Healthcare,\nMade Simple": "ዘመናዊ የጤና አገልግሎት፣\nቀላል እና ቀልጣፋ",
    "Access patient services, doctors, hospitals,\nappointments and payments from one place.": "የታካሚ አገልግሎቶችን፣ ዶክተሮችን፣ ሆስፒታሎችን፣\nቀጠሮዎችን እና ክፍያዎችን ከአንድ ቦታ ያግኙ።",
    "🚑 EMERGENCY": "🚑 አደጋ",
    "Our Services": "አገልግሎቶቻችን",
    "Why EthioCare?": "ለምን EthioCare?",
    "System Administration": "የስርዓት አስተዳደር",
    "Gender": "ጾታ",
    "Patient ID": "የታካሚ መለያ",
    "Doctor": "ዶክተር",
    "Appointment": "ቀጠሮ",
    "Payment Method": "የክፍያ ዘዴ",
    "Doctors": "ዶክተሮች",
    "Hospitals": "ሆስፒታሎች",
    "Search Type": "የፍለጋ አይነት",
    "Emergency Assistance": "የአደጋ እርዳታ",
    "Ambulance / Emergency": "አምቡላንስ / አደጋ",
    "Police Emergency": "የፖሊስ አደጋ አገልግሎት",
    "Emergency Safety Tips": "የአደጋ ደህንነት ምክሮች",
    "No results found.": "ውጤት አልተገኘም።",
    "No doctors are registered yet.": "እስካሁን ምንም ዶክተር አልተመዘገበም።",
    "No doctors registered.": "ምንም ዶክተር አልተመዘገበም።",
    "No hospitals registered.": "ምንም ሆስፒታል አልተመዘገበም።",
    "No patients registered.": "ምንም ታካሚ አልተመዘገበም።",
    "No appointments.": "ምንም ቀጠሮ የለም።",
    "No appointments found.": "ምንም ቀጠሮ አልተገኘም።",
    "No payments recorded.": "ምንም ክፍያ አልተመዘገበም።",
    "No payment history available.": "የክፍያ ታሪክ የለም።",
    "No doctors are currently available.": "በአሁኑ ጊዜ ምንም የሚገኝ ዶክተር የለም።",
    "Call 911 / 907 / 991 for immediate emergency assistance.": "ለአስቸኳይ እርዳታ 911 / 907 / 991 ይደውሉ።",
    "Register, login, book appointments and manage your profile.": "ይመዝገቡ፣ ይግቡ፣ ቀጠሮ ይያዙ እና መገለጫዎን ያስተዳድሩ።",
    "Register your hospital and manage hospital information.": "ሆስፒታልዎን ይመዝግቡ እና የሆስፒታል መረጃዎን ያስተዳድሩ።",
    "Doctors can register, login and manage appointments.": "ዶክተሮች መመዝገብ፣ መግባት እና ቀጠሮዎችን ማስተዳደር ይችላሉ።",
    "Search hospitals and doctors easily.": "ሆስፒታሎችን እና ዶክተሮችን በቀላሉ ይፈልጉ።",
    "Pay consultation and appointment fees in ETB.": "የምክር እና የቀጠሮ ክፍያዎችን በብር ይክፈሉ።",
    "View doctors who are currently available for appointments.": "በአሁኑ ጊዜ ለቀጠሮ የሚገኙ ዶክተሮችን ይመልከቱ።",
    "Find important emergency contacts and instructions.": "አስፈላጊ የአደጋ ጊዜ እውቂያዎችን እና መመሪያዎችን ያግኙ።",
    "EthioCare is a smart hospital patient service system designed to make healthcare services easier to access. Patients can register from home, search for doctors and hospitals, book appointments and make payments.": "EthioCare የጤና አገልግሎቶችን በቀላሉ ለመድረስ የተዘጋጀ ዘመናዊ የሆስፒታል የታካሚ አገልግሎት ስርዓት ነው። ታካሚዎች ከቤት መመዝገብ፣ ዶክተሮችን እና ሆስፒታሎችን መፈለግ፣ ቀጠሮ መያዝ እና ክፍያ መፈጸም ይችላሉ።",
    "Patient Login Required": "የታካሚ መግቢያ ያስፈልጋል",
    "Please login as a patient before making an online payment.": "የመስመር ላይ ክፍያ ከመፈጸምዎ በፊት እንደ ታካሚ ይግቡ።",
    "Choose an option to continue.": "ለመቀጠል አንድ አማራጭ ይምረጡ።",
    "Register once and access your healthcare services.": "አንድ ጊዜ ይመዝገቡ እና የጤና አገልግሎቶችዎን ያግኙ።",
    "Missing Information": "የጎደለ መረጃ",
    "Please fill in all fields.": "እባክዎ ሁሉንም መስኮች ይሙሉ።",
    "Invalid Age": "የተሳሳተ ዕድሜ",
    "Please enter a valid age.": "እባክዎ ትክክለኛ ዕድሜ ያስገቡ።",
    "Password Error": "የይለፍ ቃል ስህተት",
    "Passwords do not match.": "የይለፍ ቃሎቹ አይመሳሰሉም።",
    "Weak Password": "ደካማ የይለፍ ቃል",
    "Password should contain at least 4 characters.": "የይለፍ ቃሉ ቢያንስ 4 ቁምፊዎችን መያዝ አለበት።",
    "Already Registered": "አስቀድሞ ተመዝግቧል",
    "A patient with this email already exists.": "ይህን ኢሜይል የሚጠቀም ታካሚ አስቀድሞ አለ።",
    "Registration Successful": "ምዝገባው ተሳክቷል",
    "Account created successfully!\n\nPatient ID: PAT-": "መለያው በተሳካ ሁኔታ ተፈጥሯል!\n\nየታካሚ መለያ: PAT-",
    "\n\nKeep your Patient ID safe.": "\n\nየታካሚ መለያዎን በደህና ይጠብቁ።",
    "Login using your email and password.": "ኢሜይልዎን እና የይለፍ ቃልዎን በመጠቀም ይግቡ።",
    "Enter email and password.": "ኢሜይል እና የይለፍ ቃል ያስገቡ።",
    "Login Failed": "መግባት አልተሳካም",
    "Incorrect email or password.": "የተሳሳተ ኢሜይል ወይም የይለፍ ቃል።",
    "Manage your healthcare services from one dashboard.": "የጤና አገልግሎቶችዎን ከአንድ ዳሽቦርድ ያስተዳድሩ።",
    "Your registered patient information.": "የተመዘገበው የታካሚ መረጃዎ።",
    "Choose a doctor, date and time.": "ዶክተር፣ ቀን እና ሰዓት ይምረጡ።",
    "Please fill in all appointment fields.": "እባክዎ ሁሉንም የቀጠሮ መስኮች ይሙሉ።",
    "Invalid Date": "የተሳሳተ ቀን",
    "Use date format YYYY-MM-DD.": "የቀን ቅርጸት YYYY-MM-DD ይጠቀሙ።",
    "Invalid Time": "የተሳሳተ ሰዓት",
    "Use time format HH:MM.": "የሰዓት ቅርጸት HH:MM ይጠቀሙ።",
    "Time Unavailable": "ሰዓቱ አይገኝም",
    "This doctor already has an appointment at this time.": "ይህ ዶክተር በዚህ ሰዓት አስቀድሞ ቀጠሮ አለው።",
    "Appointment Booked": "ቀጠሮ ተይዟል",
    "Appointment booked successfully!\n\nAppointment ID: APP-": "ቀጠሮው በተሳካ ሁኔታ ተይዟል!\n\nየቀጠሮ መለያ: APP-",
    "You do not have any appointments yet.": "እስካሁን ምንም ቀጠሮ የለዎትም።",
    "Cancel Appointment": "ቀጠሮ ሰርዝ",
    "Are you sure you want to cancel this appointment?": "ይህን ቀጠሮ ለመሰረዝ እርግጠኛ ነዎት?",
    "Appointment cancelled successfully.": "ቀጠሮው በተሳካ ሁኔታ ተሰርዟል።",
    "Pay your hospital consultation or appointment fee.": "የሆስፒታል ምክር ወይም የቀጠሮ ክፍያዎን ይክፈሉ።",
    "General Consultation": "አጠቃላይ ምክር",
    "Invalid Amount": "የተሳሳተ መጠን",
    "Enter a valid payment amount.": "ትክክለኛ የክፍያ መጠን ያስገቡ።",
    "Payment Successful": "ክፍያው ተሳክቷል",
    "Payment completed successfully!\n\nAmount: ": "ክፍያው በተሳካ ሁኔታ ተፈጽሟል!\n\nመጠን: ",
    " ETB\nMethod: ": " ብር\nዘዴ: ",
    "View all payments made through EthioCare.": "በEthioCare በኩል የተፈጸሙ ሁሉንም ክፍያዎች ይመልከቱ።",
    "Total Paid: ": "ጠቅላላ የተከፈለ: ",
    "Register or login as a hospital.": "እንደ ሆስፒታል ይመዝገቡ ወይም ይግቡ።",
    "Add your hospital to the EthioCare system.": "ሆስፒታልዎን ወደ EthioCare ስርዓት ያክሉ።",
    "Hospital Registered": "ሆስፒታሉ ተመዝግቧል",
    "Hospital registered successfully!\n\nHospital ID: HOS-": "ሆስፒታሉ በተሳካ ሁኔታ ተመዝግቧል!\n\nየሆስፒታል መለያ: HOS-",
    "Incorrect hospital email or password.": "የተሳሳተ የሆስፒታል ኢሜይል ወይም የይለፍ ቃል።",
    "Hospital management dashboard.": "የሆስፒታል አስተዳደር ዳሽቦርድ።",
    "Register or login as a doctor.": "እንደ ዶክተር ይመዝገቡ ወይም ይግቡ።",
    "Register a doctor in the EthioCare system.": "ዶክተርን በEthioCare ስርዓት ውስጥ ይመዝግቡ።",
    "A doctor with this email already exists.": "ይህን ኢሜይል የሚጠቀም ዶክተር አስቀድሞ አለ።",
    "Doctor registered successfully!\n\nDoctor ID: DOC-": "ዶክተሩ በተሳካ ሁኔታ ተመዝግቧል!\n\nየዶክተር መለያ: DOC-",
    "Incorrect doctor email or password.": "የተሳሳተ የዶክተር ኢሜይል ወይም የይለፍ ቃል።",
    "Doctor management dashboard.": "የዶክተር አስተዳደር ዳሽቦርድ።",
    "View My Appointments": "የእኔን ቀጠሮዎች ይመልከቱ",
    "Appointments booked with you.": "ከእርስዎ ጋር የተያዙ ቀጠሮዎች።",
    "Search registered healthcare providers.": "የተመዘገቡ የጤና አገልግሎት ሰጪዎችን ይፈልጉ።",
    "For immediate danger, contact emergency services.": "አስቸኳይ አደጋ ካለ ወዲያውኑ የአደጋ አገልግሎቶችን ያነጋግሩ።",
    "Do not wait for the application if the situation is life-threatening.": "ሁኔታው ለሕይወት አስጊ ከሆነ መተግበሪያውን አትጠብቁ።",
    "Stay calm and provide your exact location.": "ተረጋጉ እና ትክክለኛ አካባቢዎን ይግለጹ።",
    "Call emergency services immediately.": "ወዲያውኑ የአደጋ አገልግሎቶችን ይደውሉ።",
    "Do not drive yourself if you are seriously injured.": "በከባድ ከተጎዱ እራስዎን በመኪና አይውሰዱ።",
    "Follow instructions from emergency responders.": "ከአደጋ ጊዜ ምላሽ ሰጪዎች የሚሰጡ መመሪያዎችን ይከተሉ።",
    "Keep important medical information available.": "አስፈላጊ የሕክምና መረጃዎችን ዝግጁ ያድርጉ።",
    "Appointment and system notification settings.": "የቀጠሮ እና የስርዓት ማሳወቂያ ቅንብሮች።",
    "Windows notifications are available.": "የWindows ማሳወቂያዎች ይገኛሉ።",
    "Windows notifications are not installed.": "የWindows ማሳወቂያዎች አልተጫኑም።",
    "Winotify Not Installed": "Winotify አልተጫነም",
    "Notification Sent": "ማሳወቂያው ተልኳል",
    "Notification Error": "የማሳወቂያ ስህተት",
    "Test Windows Notification": "የWindows ማሳወቂያ ሙከራ",
    "System administration area.": "የስርዓት አስተዳደር ክፍል።",
    "Incorrect administrator username or password.": "የተሳሳተ የአስተዳዳሪ ተጠቃሚ ስም ወይም የይለፍ ቃል።",
    "Manage the EthioCare system.": "የEthioCare ስርዓትን ያስተዳድሩ።",
    "All Registered Patients": "ሁሉም የተመዘገቡ ታካሚዎች",
    "Doctors currently marked as available for appointments.": "በአሁኑ ጊዜ ለቀጠሮ እንደሚገኙ የተመለከቱ ዶክተሮች።",
    "All Registered Doctors": "ሁሉም የተመዘገቡ ዶክተሮች",
    "All Registered Hospitals": "ሁሉም የተመዘገቡ ሆስፒታሎች",
    "Logged Out": "ወጥተዋል",
    "You have been logged out successfully.": "በተሳካ ሁኔታ ወጥተዋል።",
}


# New translations for hospital approval and doctor appointment actions.
for _lang, _pairs in {
    "en": {
        "Previous Achievements": "Previous Achievements",
        "Hospital Status": "Hospital Status",
        "Approved": "Approved",
        "Rejected": "Rejected",
        "Accept": "Accept",
        "Reject": "Reject",
        "Pending Hospitals": "Pending Hospitals",
        "Hospital Approval": "Hospital Approval",
        "Hospital registration is waiting for administrator approval.": "Hospital registration is waiting for administrator approval.",
        "Hospital registration approved successfully.": "Hospital registration approved successfully.",
        "Hospital registration rejected.": "Hospital registration rejected.",
        "Your hospital account is pending administrator approval.": "Your hospital account is pending administrator approval.",
        "Your hospital account has been rejected.": "Your hospital account has been rejected.",
        "Hospital approved successfully.": "Hospital approved successfully.",
        "Hospital rejected successfully.": "Hospital rejected successfully.",
        "Approve": "Approve",
        "Reject": "Reject",
        "Appointment Approved": "Appointment Approved",
        "Appointment Rejected": "Appointment Rejected",
        "Appointment approved successfully.": "Appointment approved successfully.",
        "Appointment rejected successfully.": "Appointment rejected successfully.",
    },
    "am": {
        "Previous Achievements": "የቀድሞ ስኬቶች",
        "Hospital Status": "የሆስፒታል ሁኔታ",
        "Approved": "ጸድቋል",
        "Rejected": "ውድቅ ተደርጓል",
        "Accept": "ተቀበል",
        "Reject": "ውድቅ አድርግ",
        "Pending Hospitals": "በመጠባበቅ ላይ ያሉ ሆስፒታሎች",
        "Hospital Approval": "የሆስፒታል ማጽደቅ",
        "Hospital registration is waiting for administrator approval.": "የሆስፒታሉ ምዝገባ የአስተዳዳሪ ማጽደቅን እየጠበቀ ነው።",
        "Hospital registration approved successfully.": "የሆስፒታሉ ምዝገባ በተሳካ ሁኔታ ጸድቋል።",
        "Hospital registration rejected.": "የሆስፒታሉ ምዝገባ ውድቅ ተደርጓል።",
        "Your hospital account is pending administrator approval.": "የሆስፒታል መለያዎ የአስተዳዳሪ ማጽደቅን እየጠበቀ ነው።",
        "Your hospital account has been rejected.": "የሆስፒታል መለያዎ ውድቅ ተደርጓል።",
        "Hospital approved successfully.": "ሆስፒታሉ በተሳካ ሁኔታ ጸድቋል።",
        "Hospital rejected successfully.": "ሆስፒታሉ በተሳካ ሁኔታ ውድቅ ተደርጓል።",
        "Approve": "አጽድቅ",
        "Reject": "ውድቅ አድርግ",
        "Appointment Approved": "ቀጠሮው ጸድቋል",
        "Appointment Rejected": "ቀጠሮው ውድቅ ተደርጓል",
        "Appointment approved successfully.": "ቀጠሮው በተሳካ ሁኔታ ጸድቋል።",
        "Appointment rejected successfully.": "ቀጠሮው በተሳካ ሁኔታ ውድቅ ተደርጓል።",
    },
    "om": {
        "Previous Achievements": "Milkaa'ina Durii",
        "Hospital Status": "Haala Hospitaalaa",
        "Approved": "Mirkanaa'e",
        "Rejected": "Kufaa Ta'e",
        "Accept": "Fudhu",
        "Reject": "Kufaa Godhi",
        "Pending Hospitals": "Hospitaalota Eeggachaa Jiran",
        "Hospital Approval": "Mirkaneessa Hospitaalaa",
        "Approve": "Mirkaneessi",
        "Reject": "Kufaa Godhi",
        "Appointment Approved": "Beellamni Mirkanaa'e",
        "Appointment Rejected": "Beellamni Kufaa Ta'e",
        "Appointment approved successfully.": "Beellamni milkaa'inaan mirkanaa'e.",
        "Appointment rejected successfully.": "Beellamni milkaa'inaan kufaa ta'e.",
    },
    "ti": {
        "Previous Achievements": "ዝሓለፈ ዓወታት",
        "Hospital Status": "ኩነታት ሆስፒታል",
        "Approved": "ጸዲቑ",
        "Rejected": "ውድቂ ተገይሩ",
        "Accept": "ተቐበል",
        "Reject": "ውድቂ ግበር",
        "Pending Hospitals": "ኣብ ትጽቢት ዘለዉ ሆስፒታላት",
        "Hospital Approval": "ምጽዳቕ ሆስፒታል",
        "Approve": "ኣጽድቕ",
        "Reject": "ውድቂ ግበር",
        "Appointment Approved": "ቆጸራ ጸዲቑ",
        "Appointment Rejected": "ቆጸራ ውድቂ ተገይሩ",
        "Appointment approved successfully.": "ቆጸራ ብዓወት ጸዲቑ።",
        "Appointment rejected successfully.": "ቆጸራ ብዓወት ውድቂ ተገይሩ።",
    }
}.items():
    TRANSLATIONS[_lang].update(_pairs)

TRANSLATIONS["am"].update(AMHARIC_EXTRA_TRANSLATIONS)


# ------------------------------------------------------------
# HOME + ADMINISTRATOR UI TRANSLATIONS
# These keys are also used directly by the widgets below so
# changing the language rebuilds the page in that language.
# ------------------------------------------------------------
_UI_TRANSLATIONS = {
    "en": {
        "Smart Healthcare,\nMade Simple": "Smart Healthcare,\nMade Simple",
        "Access patient services, doctors, hospitals,\napppointments and payments from one place.": "Access patient services, doctors, hospitals,\napppointments and payments from one place.",
        "Access patient services, doctors, hospitals,\nappointments and payments from one place.": "Access patient services, doctors, hospitals,\nappointments and payments from one place.",
        "EMERGENCY": "EMERGENCY",
        "Our Services": "Our Services",
        "Register, login, book appointments and manage your profile.": "Register, login, book appointments and manage your profile.",
        "Register your hospital and manage hospital information.": "Register your hospital and manage hospital information.",
        "Doctors can register, login and manage appointments.": "Doctors can register, login and manage appointments.",
        "Search hospitals and doctors easily.": "Search hospitals and doctors easily.",
        "Pay consultation and appointment fees in ETB.": "Pay consultation and appointment fees in ETB.",
        "View doctors who are currently available for appointments.": "View doctors who are currently available for appointments.",
        "Find important emergency contacts and instructions.": "Find important emergency contacts and instructions.",
        "Why EthioCare?": "Why EthioCare?",
        "EthioCare is a smart hospital patient service system designed to make healthcare services easier to access. Patients can register from home, search for doctors and hospitals, book appointments and make payments.": "EthioCare is a smart hospital patient service system designed to make healthcare services easier to access. Patients can register from home, search for doctors and hospitals, book appointments and make payments.",
        "Patients": "Patients",
        "Doctors": "Doctors",
        "Hospitals": "Hospitals",
        "Appointments": "Appointments",
        "Payments": "Payments",
        "Available Doctors": "Available Doctors",
        "Pending Hospitals": "Pending Hospitals",
        "Manage the EthioCare system.": "Manage the EthioCare system.",
    },
    "am": {
        "Smart Healthcare,\nMade Simple": "ዘመናዊ የጤና አገልግሎት፣\nቀላል እና ቀልጣፋ",
        "Access patient services, doctors, hospitals,\napppointments and payments from one place.": "የታካሚ አገልግሎቶችን፣ ዶክተሮችን፣ ሆስፒታሎችን፣\nቀጠሮዎችን እና ክፍያዎችን ከአንድ ቦታ ያግኙ።",
        "Access patient services, doctors, hospitals,\nappointments and payments from one place.": "የታካሚ አገልግሎቶችን፣ ዶክተሮችን፣ ሆስፒታሎችን፣\nቀጠሮዎችን እና ክፍያዎችን ከአንድ ቦታ ያግኙ።",
        "EMERGENCY": "አስቸኳይ እርዳታ",
        "Our Services": "አገልግሎቶቻችን",
        "Register, login, book appointments and manage your profile.": "ይመዝገቡ፣ ይግቡ፣ ቀጠሮ ይያዙ እና መገለጫዎን ያስተዳድሩ።",
        "Register your hospital and manage hospital information.": "ሆስፒታልዎን ይመዝግቡ እና የሆስፒታል መረጃን ያስተዳድሩ።",
        "Doctors can register, login and manage appointments.": "ዶክተሮች መመዝገብ፣ መግባት እና ቀጠሮዎችን ማስተዳደር ይችላሉ።",
        "Search hospitals and doctors easily.": "ሆስፒታሎችን እና ዶክተሮችን በቀላሉ ይፈልጉ።",
        "Pay consultation and appointment fees in ETB.": "የምክር እና የቀጠሮ ክፍያዎችን በብር ይክፈሉ።",
        "View doctors who are currently available for appointments.": "በአሁኑ ጊዜ ለቀጠሮ የሚገኙ ዶክተሮችን ይመልከቱ።",
        "Find important emergency contacts and instructions.": "አስፈላጊ የአደጋ ጊዜ እውቂያዎችን እና መመሪያዎችን ያግኙ።",
        "Why EthioCare?": "ለምን EthioCare?",
        "EthioCare is a smart hospital patient service system designed to make healthcare services easier to access. Patients can register from home, search for doctors and hospitals, book appointments and make payments.": "EthioCare የጤና አገልግሎቶችን በቀላሉ ለመድረስ የተዘጋጀ ዘመናዊ የሆስፒታል የታካሚ አገልግሎት ስርዓት ነው። ታካሚዎች ከቤት መመዝገብ፣ ዶክተሮችን እና ሆስፒታሎችን መፈለግ፣ ቀጠሮ መያዝ እና ክፍያ መፈጸም ይችላሉ።",
        "Patients": "ታካሚዎች",
        "Doctors": "ዶክተሮች",
        "Hospitals": "ሆስፒታሎች",
        "Appointments": "ቀጠሮዎች",
        "Payments": "ክፍያዎች",
        "Available Doctors": "የሚገኙ ዶክተሮች",
        "Pending Hospitals": "በመጠባበቅ ላይ ያሉ ሆስፒታሎች",
        "Manage the EthioCare system.": "የEthioCare ስርዓትን ያስተዳድሩ።",
    },
    "om": {
        "Smart Healthcare,\nMade Simple": "Tajaajila Fayyaa Ammayyaa,\nSalphaa fi Saffisaa",
        "Access patient services, doctors, hospitals,\napppointments and payments from one place.": "Tajaajila dhukkubsataa, doktoroota, hospitaalota,\nbeellamoota fi kaffaltii bakka tokko irraa argadhaa.",
        "Access patient services, doctors, hospitals,\nappointments and payments from one place.": "Tajaajila dhukkubsataa, doktoroota, hospitaalota,\nbeellamoota fi kaffaltii bakka tokko irraa argadhaa.",
        "EMERGENCY": "HAALA HATATTAMAA",
        "Our Services": "Tajaajiloota Keenya",
        "Register, login, book appointments and manage your profile.": "Galmaa'i, seeni, beellama qabsiisi fi piroofaayila kee bulchi.",
        "Register your hospital and manage hospital information.": "Hospitaala kee galmeessi fi odeeffannoo hospitaalaa bulchi.",
        "Doctors can register, login and manage appointments.": "Doktoroonni galmaa'uu, seenuu fi beellamoota bulchuu danda'u.",
        "Search hospitals and doctors easily.": "Hospitaalota fi doktoroota salphaatti barbaadi.",
        "Pay consultation and appointment fees in ETB.": "Kaffaltii marii fi beellamaa ETBn kaffali.",
        "View doctors who are currently available for appointments.": "Doktoroota yeroo ammaa beellamaaf argaman ilaali.",
        "Find important emergency contacts and instructions.": "Quunnamtii fi qajeelfama hatattamaa barbaachisaa argadhu.",
        "Why EthioCare?": "Maaliif EthioCare?",
        "EthioCare is a smart hospital patient service system designed to make healthcare services easier to access. Patients can register from home, search for doctors and hospitals, book appointments and make payments.": "EthioCare sirna tajaajila dhukkubsataa hospitaalaa ammayyaa dha; tajaajila fayyaa argachuun akka salphatuuf qophaa'e. Dhukkubsattoonni mana irraa galmaa'uu, doktoroota fi hospitaalota barbaaduu, beellama qabachuu fi kaffaltii kaffaluu danda'u.",
        "Patients": "Dhukkubsattoota",
        "Doctors": "Doktoroota",
        "Hospitals": "Hospitaalota",
        "Appointments": "Beellamoota",
        "Payments": "Kaffaltii",
        "Available Doctors": "Doktoroota Argaman",
        "Pending Hospitals": "Hospitaalota Eeggachaa Jiran",
        "Manage the EthioCare system.": "Sirna EthioCare bulchi.",
    },
    "ti": {
        "Smart Healthcare,\nMade Simple": "ዘመናዊ ኣገልግሎት ጥዕና፣\nቀሊልን ቀልጣፋን",
        "Access patient services, doctors, hospitals,\napppointments and payments from one place.": "ኣገልግሎት ሕሙማት፣ ሓካይም፣ ሆስፒታላት፣\nቆጸራታትን ክፍሊታትን ካብ ሓደ ቦታ ርኸብ።",
        "Access patient services, doctors, hospitals,\nappointments and payments from one place.": "ኣገልግሎት ሕሙማት፣ ሓካይም፣ ሆስፒታላት፣\nቆጸራታትን ክፍሊታትን ካብ ሓደ ቦታ ርኸብ።",
        "EMERGENCY": "ህጹጽ ሓገዝ",
        "Our Services": "ኣገልግሎታትና",
        "Register, login, book appointments and manage your profile.": "ተመዝገብ፣ እቶ፣ ቆጸራ ሓዝን ፕሮፋይልካ ኣመሓድርን።",
        "Register your hospital and manage hospital information.": "ሆስፒታልካ ኣመዝግብን ሓበሬታ ሆስፒታል ኣመሓድርን።",
        "Doctors can register, login and manage appointments.": "ሓካይም ክምዝገቡ፣ ክኣትዉን ቆጸራታት ከመሓድሩን ይኽእሉ።",
        "Search hospitals and doctors easily.": "ሆስፒታላትን ሓካይምን ብቐሊሉ ድለ።",
        "Pay consultation and appointment fees in ETB.": "ክፍሊት ምኽርን ቆጸራን ብETB ክፈል።",
        "View doctors who are currently available for appointments.": "ኣብዚ ግዜ ንቆጸራ ዝርከቡ ሓካይም ርአ።",
        "Find important emergency contacts and instructions.": "ኣገደስቲ ርክባትን መምርሒታትን ህጹጽ ኩነታት ርኸብ።",
        "Why EthioCare?": "ስለምንታይ EthioCare?",
        "EthioCare is a smart hospital patient service system designed to make healthcare services easier to access. Patients can register from home, search for doctors and hospitals, book appointments and make payments.": "EthioCare ኣገልግሎት ጥዕና ብቐሊሉ ንምርካብ ዝተዳለወ ዘመናዊ ስርዓት ኣገልግሎት ሕሙማት ሆስፒታል እዩ። ሕሙማት ካብ ገዛ ክምዝገቡ፣ ሓካይምን ሆስፒታላትን ክደልዩ፣ ቆጸራ ክሕዙን ክፍሊት ክፍጽሙን ይኽእሉ።",
        "Patients": "ሕሙማት",
        "Doctors": "ሓካይም",
        "Hospitals": "ሆስፒታላት",
        "Appointments": "ቆጸራታት",
        "Payments": "ክፍሊታት",
        "Available Doctors": "ዝርከቡ ሓካይም",
        "Pending Hospitals": "ኣብ ትጽቢት ዘለዉ ሆስፒታላት",
        "Manage the EthioCare system.": "ስርዓት EthioCare ኣመሓድር።",
    },
}
for _code, _pairs in _UI_TRANSLATIONS.items():
    TRANSLATIONS.setdefault(_code, {}).update(_pairs)

CURRENT_LANGUAGE = "en"

def translate_text(text, language=None):
    """Translate an interface string while preserving unknown/dynamic text."""
    language = language or CURRENT_LANGUAGE
    if not isinstance(text, str):
        return text
    table = TRANSLATIONS.get(language, TRANSLATIONS["en"])

    # English is the master/source language.  If a widget currently contains
    # a translated value, first recover its English key so switching back to
    # English always restores the original text.
    if text in table:
        return table[text]
    if language == "en":
        for lang_code, lang_table in TRANSLATIONS.items():
            if lang_code == "en":
                continue
            for en_key, localized_value in lang_table.items():
                if localized_value == text:
                    return en_key

    # Handle common dynamic strings without changing their data.
    replacements = [
        ("Welcome, ", {"am":"እንኳን ደህና መጡ፣ ","om":"Baga nagaan dhuftan, ","ti":"እንቋዕ ብደሓን መጻእኩም፣ "}),
        ("Doctor: Dr. ", {"am":"ዶክተር፡ ","om":"Doktora: ","ti":"ሓኪም፡ "}),
        ("Dr. ", {"am":"ዶ/ር ","om":"Dok. ","ti":"ዶ/ር "}),
        ("Patient ID", {"am":"የታካሚ መለያ","om":"ID Dhukkubsataa","ti":"መለለዪ ሕሙም"}),
        ("Doctor ID", {"am":"የዶክተር መለያ","om":"ID Doktoraa","ti":"መለለዪ ሓኪም"}),
        ("Hospital ID", {"am":"የሆስፒታል መለያ","om":"ID Hospitaalaa","ti":"መለለዪ ሆስፒታል"}),
        ("● AVAILABLE", {"am":"● ይገኛል","om":"● ARGAMA","ti":"● ይርከብ"}),
        ("Payment #", {"am":"ክፍያ #","om":"Kaffaltii #","ti":"ክፍሊት #"}),
        ("Total Paid: ", {"am":"ጠቅላላ የተከፈለ: ","om":"Waliigala Kaffalame: ","ti":"ጠቕላላ ዝተኸፍለ: "}),
        ("Doctor: ", {"am":"ዶክተር: ","om":"Doktora: ","ti":"ሓኪም: "}),
        ("Hospital: ", {"am":"ሆስፒታል: ","om":"Hospitaala: ","ti":"ሆስፒታል: "}),
        ("Location: ", {"am":"አካባቢ: ","om":"Bakka: ","ti":"ቦታ: "}),
        ("Phone: ", {"am":"ስልክ: ","om":"Bilbila: ","ti":"ተሌፎን: "}),
        ("Email: ", {"am":"ኢሜይል: ","om":"Imeelii: ","ti":"ኢመይል: "}),
        ("Address: ", {"am":"አድራሻ: ","om":"Teessoo: ","ti":"ኣድራሻ: "}),
    ]
    for prefix, localized in replacements:
        if text.startswith(prefix):
            return localized.get(language, prefix) + text[len(prefix):]

    # Translate known "Label:" fragments inside multi-line records.
    if language != "en":
        for en, locs in table.items():
            if en.endswith(":") and en in text:
                text = text.replace(en, locs + ("" if en.endswith(":") else ""))
    return text


class LocalizedMessageBox:
    """Drop-in proxy for tkinter.messagebox that localizes dialog text."""
    def __getattr__(self, name):
        original = getattr(tk_messagebox, name)
        if not callable(original):
            return original
        def wrapped(title="", message="", *args, **kwargs):
            return original(
                translate_text(title),
                translate_text(message),
                *args,
                **kwargs
            )
        return wrapped

# Keep the original module available, while existing code continues to
# use the name 'messagebox'.
tk_messagebox = messagebox
messagebox = LocalizedMessageBox()

# ============================================================
# MAIN APPLICATION
# ============================================================

class HospitalApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "EthioCare | Smart Hospital Services"
        )

        self.root.geometry(
            "1200x760"
        )

        self.root.minsize(
            950,
            650
        )

        self.dark_mode = False

        # Language support
        self.language = "en"
        self.languages = LANGUAGE_NAMES.copy()

        self.current_user = None
        self.current_user_type = None
        self.current_page = None
        self.page_history = []
        self._going_back = False

        setup_database()

        self.apply_theme()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_app
        )

        self.show_home()
        self.translate_widgets()

    # ========================================================
    # LANGUAGE SUPPORT
    # ========================================================

    def set_language(self, code):
        global CURRENT_LANGUAGE
        if code not in self.languages:
            code = "en"
        self.language = code
        CURRENT_LANGUAGE = code

        # Rebuild the current screen and translate every visible widget.
        if self.current_page:
            self._going_back = True
            try:
                self.current_page()
                self.translate_widgets()
            finally:
                self._going_back = False

    def language_selector(self, parent):
        frame = tk.Frame(parent, bg=self.card_color)
        frame.pack(side="left", padx=5)
        tk.Label(
            frame, text="🌐", bg=self.card_color, fg=self.text,
            font=("Segoe UI", 11)
        ).pack(side="left", padx=(0, 4))

        box = ttk.Combobox(
            frame,
            values=list(self.languages.values()),
            state="readonly",
            width=15,
            font=("Segoe UI", 9)
        )
        box.set(self.languages.get(self.language, "English"))
        box.pack(side="left")

        reverse = {v: k for k, v in self.languages.items()}
        box.bind(
            "<<ComboboxSelected>>",
            lambda e: self.set_language(reverse[box.get()])
        )
        return box

    def t(self, key):
        return translate_text(key, self.language)

    def translate_widgets(self):
        """Translate visible interface widgets for the currently selected language.
        English is the master language, so switching back to English also
        restores labels that were previously translated.
        """
        def walk(parent):
            for widget in parent.winfo_children():
                try:
                    cls = widget.winfo_class()

                    if cls in ("Label", "Button"):
                        current = widget.cget("text")
                        if current:
                            widget.configure(text=translate_text(current, self.language))

                    # Do not translate ordinary Combobox values here.
                    # Several pages use the English values internally
                    # ("All", "Doctors", "Hospitals", etc.) for database logic.
                    # Translating those values would break that logic.
                    # The language selector itself is already localized by
                    # language_selector() and is intentionally left alone.

                except (tk.TclError, TypeError):
                    pass

                walk(widget)

        walk(self.root)

    # ========================================================
    # THEME
    # ========================================================

    def apply_theme(self):

        if self.dark_mode:

            self.bg = DARK_BG
            self.card_color = DARK_CARD
            self.text = DARK_TEXT
            self.muted = DARK_MUTED
            self.border = DARK_BORDER
            self.primary = DARK_PRIMARY
            self.primary_dark = DARK_PRIMARY_DARK

        else:

            self.bg = LIGHT_BG
            self.card_color = LIGHT_CARD
            self.text = LIGHT_TEXT
            self.muted = LIGHT_MUTED
            self.border = LIGHT_BORDER
            self.primary = LIGHT_PRIMARY
            self.primary_dark = LIGHT_PRIMARY_DARK

        self.root.configure(
            bg=self.bg
        )

        self.setup_styles()

    # ========================================================
    # STYLES
    # ========================================================

    def setup_styles(self):

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "TCombobox",
            fieldbackground=self.card_color,
            background=self.card_color,
            foreground=self.text,
            bordercolor=self.border
        )

        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", self.card_color)
            ],
            foreground=[
                ("readonly", self.text)
            ]
        )

        style.configure(
            "Treeview",
            background=self.card_color,
            foreground=self.text,
            fieldbackground=self.card_color,
            rowheight=35
        )

        style.configure(
            "Treeview.Heading",
            background=self.primary,
            foreground="white",
            font=("Segoe UI", 10, "bold")
        )

    # ========================================================
    # TOGGLE THEME
    # ========================================================

    def toggle_theme(self):

        self.dark_mode = not self.dark_mode

        self.apply_theme()

        if self.current_page:
            self.current_page()
            self.translate_widgets()

    # ========================================================
    # PAGE NAVIGATION HISTORY
    # ========================================================

    def set_current_page(self, page):

        # Save the page we came from so the Back arrow always
        # returns to the immediately previous screen.
        if self.current_page is not None and self.current_page != page and not self._going_back:
            self.page_history.append(self.current_page)

        self.current_page = page

    def go_back(self):

        # Go to the real previous page instead of always returning home.
        if self.page_history:
            previous_page = self.page_history.pop()
            self._going_back = True
            try:
                previous_page()
            finally:
                self._going_back = False
        else:
            # Home is the only sensible destination when there is no history.
            self._going_back = True
            try:
                self.show_home()
            finally:
                self._going_back = False

    # ========================================================
    # HOSPITAL NAVIGATION FIX
    # ========================================================

    def return_to_hospital_portal(self):
        # Register Hospital is a child screen of Hospital Services.
        # Remove both the registration entry and the Hospital Services
        # history entry before returning, so the next Back goes Home.
        self.page_history = [
            page for page in self.page_history
            if page not in (self.hospital_register, self.hospital_portal)
        ]

        self._going_back = True
        try:
            self.hospital_portal()
        finally:
            self._going_back = False

    # ========================================================
    # DASHBOARD / SERVICE NAVIGATION FIX
    # ========================================================

    def return_to_doctor_portal(self):
        # Registration is a child of Doctor Services.
        # Remove stale registration/portal entries so the next Back goes Home.
        self.page_history = [
            page for page in self.page_history
            if page not in (self.doctor_register, self.doctor_portal)
        ]
        self._going_back = True
        try:
            self.doctor_portal()
        finally:
            self._going_back = False

    def return_to_patient_portal(self):
        # Registration is a child of Patient Services.
        self.page_history = [
            page for page in self.page_history
            if page not in (self.patient_register, self.patient_portal)
        ]
        self._going_back = True
        try:
            self.patient_portal()
        finally:
            self._going_back = False

    # ========================================================
    # CLEAR WINDOW
    # ========================================================

    def clear(self):

        for widget in self.root.winfo_children():
            widget.destroy()

    # ========================================================
    # CURRENT TIME
    # ========================================================

    def now(self):

        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close_app(self):

        self.root.destroy()

    # ========================================================
    # HEADER
    # ========================================================

    def header(self, title="EthioCare"):

        header = tk.Frame(
            self.root,
            bg=self.card_color,
            height=78
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(False)

        # LEFT
        left = tk.Frame(
            header,
            bg=self.card_color
        )

        left.pack(
            side="left",
            padx=25
        )

        tk.Label(
            left,
            text="♥",
            font=("Segoe UI", 28, "bold"),
            fg=self.primary,
            bg=self.card_color
        ).pack(
            side="left",
            padx=(0, 10)
        )

        tk.Label(
            left,
            text=self.t(title),
            font=("Segoe UI", 20, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            side="left"
        )

        # RIGHT
        right = tk.Frame(
            header,
            bg=self.card_color
        )

        right.pack(
            side="right",
            padx=20
        )

        self.language_selector(right)

        theme_text = (
            "☀ " + self.t("Light")
            if self.dark_mode
            else
            "☾ " + self.t("Dark")
        )

        tk.Button(
            right,
            text=theme_text,
            command=self.toggle_theme,
            font=("Segoe UI", 10, "bold"),
            bg=self.bg,
            fg=self.text,
            activebackground=self.primary,
            activeforeground="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(
            side="left",
            padx=5
        )

        tk.Button(
            right,
            text=self.t("Home"),
            command=self.show_home,
            font=("Segoe UI", 10, "bold"),
            bg=self.primary,
            fg="white",
            activebackground=self.primary_dark,
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2"
        ).pack(
            side="left",
            padx=5
        )

    # ========================================================
    # BUTTON
    # ========================================================

    def button(
        self,
        parent,
        text,
        command,
        bg=None,
        fg="white",
        width=20
    ):

        if bg is None:
            bg = self.primary

        return tk.Button(
            parent,
            text=self.t(text),
            command=command,
            font=("Segoe UI", 10, "bold"),
            bg=bg,
            fg=fg,
            activebackground=self.primary_dark,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            width=width,
            padx=14,
            pady=11,
            highlightthickness=0
        )

    # ========================================================
    # CARD
    # ========================================================

    def card(
        self,
        parent,
        padx=25,
        pady=20
    ):

        frame = tk.Frame(
            parent,
            bg=self.card_color,
            highlightbackground=self.border,
            highlightthickness=1,
            bd=0
        )

        frame.pack(
            fill="x",
            padx=padx,
            pady=pady
        )

        return frame

    # ========================================================
    # SCROLLABLE PAGE
    # ========================================================

    def make_scrollable_page(self):

        outer = tk.Frame(
            self.root,
            bg=self.bg
        )

        outer.pack(
            fill="both",
            expand=True
        )

        canvas = tk.Canvas(
            outer,
            bg=self.bg,
            highlightthickness=0
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        content = tk.Frame(
            canvas,
            bg=self.bg
        )

        window_id = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw"
        )

        def configure_content(event):

            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        def configure_canvas(event):

            canvas.itemconfig(
                window_id,
                width=event.width
            )

        content.bind(
            "<Configure>",
            configure_content
        )

        canvas.bind(
            "<Configure>",
            configure_canvas
        )

        def mousewheel(event):

            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all(
            "<MouseWheel>",
            mousewheel
        )

        return content

    # ========================================================
    # PAGE TITLE
    # ========================================================

    def page_title(
        self,
        parent,
        title,
        subtitle=""
    ):

        box = tk.Frame(
            parent,
            bg=self.bg
        )

        box.pack(
            fill="x",
            padx=30,
            pady=(25, 10)
        )

        tk.Label(
            box,
            text=self.t(title),
            font=("Segoe UI", 24, "bold"),
            fg=self.text,
            bg=self.bg
        ).pack(
            anchor="w"
        )

        if subtitle:

            tk.Label(
                box,
                text=self.t(subtitle),
                font=("Segoe UI", 11),
                fg=self.muted,
                bg=self.bg
            ).pack(
                anchor="w",
                pady=(5, 0)
            )

    # ========================================================
    # FIELD
    # ========================================================

    def field(
        self,
        parent,
        label,
        show=None,
        default=""
    ):

        box = tk.Frame(
            parent,
            bg=self.card_color
        )

        box.pack(
            fill="x",
            pady=7
        )

        tk.Label(
            box,
            text=self.t(label),
            font=("Segoe UI", 10, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        entry = tk.Entry(
            box,
            font=("Segoe UI", 11),
            bg=self.bg,
            fg=self.text,
            insertbackground=self.text,
            relief="flat",
            show=show
        )

        entry.pack(
            fill="x",
            ipady=9,
            pady=(5, 0)
        )

        if default:

            entry.insert(
                0,
                default
            )

        return entry

    # ========================================================
    # PASSWORD FIELD
    # ========================================================

    def password_field(
        self,
        parent,
        label="Password"
    ):

        box = tk.Frame(
            parent,
            bg=self.card_color
        )

        box.pack(
            fill="x",
            pady=7
        )

        tk.Label(
            box,
            text=self.t(label),
            font=("Segoe UI", 10, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        row = tk.Frame(
            box,
            bg=self.card_color
        )

        row.pack(
            fill="x",
            pady=(5, 0)
        )

        entry = tk.Entry(
            row,
            font=("Segoe UI", 11),
            bg=self.bg,
            fg=self.text,
            insertbackground=self.text,
            relief="flat",
            show="•"
        )

        entry.pack(
            side="left",
            fill="x",
            expand=True,
            ipady=9
        )

        visible = [False]

        def toggle():

            visible[0] = not visible[0]

            if visible[0]:

                entry.config(
                    show=""
                )

                show_btn.config(
                    text="Hide"
                )

            else:

                entry.config(
                    show="•"
                )

                show_btn.config(
                    text="Show"
                )

        show_btn = tk.Button(
            row,
            text="Show",
            command=toggle,
            bg=self.primary,
            fg="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            padx=10
        )

        show_btn.pack(
            side="right",
            padx=(7, 0),
            ipady=7
        )

        return entry

    # ========================================================
    # HOME
    # ========================================================

    def show_home(self):

        self.set_current_page(self.show_home)

        self.clear()

        self.header(
            "EthioCare"
        )

        content = self.make_scrollable_page()

        # ----------------------------------------------------
        # HERO
        # ----------------------------------------------------

        hero = tk.Frame(
            content,
            bg=self.primary
        )

        hero.pack(
            fill="x",
            padx=30,
            pady=30
        )

        tk.Label(
            hero,
            text=self.t("Smart Healthcare,\nMade Simple"),
            font=("Segoe UI", 30, "bold"),
            fg="white",
            bg=self.primary,
            justify="left"
        ).pack(
            anchor="w",
            padx=35,
            pady=(30, 10)
        )

        tk.Label(
            hero,
            text=self.t(
                "Access patient services, doctors, hospitals,\n"
                "appointments and payments from one place."
            ),
            font=("Segoe UI", 12),
            fg="white",
            bg=self.primary,
            justify="left"
        ).pack(
            anchor="w",
            padx=35,
            pady=(0, 25)
        )

        hero_buttons = tk.Frame(
            hero,
            bg=self.primary
        )

        hero_buttons.pack(
            anchor="w",
            padx=35,
            pady=(0, 30)
        )

        self.button(
            hero_buttons,
            self.t("Patient Services"),
            self.patient_portal,
            bg="white",
            fg=self.primary,
            width=20
        ).pack(
            side="left",
            padx=(0, 10)
        )

        self.button(
            hero_buttons,
            self.t("Emergency Help"),
            self.emergency_page,
            bg=DANGER,
            width=20
        ).pack(
            side="left"
        )

        # ----------------------------------------------------
        # EMERGENCY BANNER
        # ----------------------------------------------------

        emergency = tk.Frame(
            content,
            bg="#fee2e2",
            highlightbackground="#fecaca",
            highlightthickness=1
        )

        emergency.pack(
            fill="x",
            padx=30,
            pady=(0, 20)
        )

        tk.Label(
            emergency,
            text="🚑 " + self.t("EMERGENCY"),
            font=("Segoe UI", 14, "bold"),
            fg=DANGER,
            bg="#fee2e2"
        ).pack(
            side="left",
            padx=20,
            pady=18
        )

        tk.Label(
            emergency,
            text=self.t(
                "Call 911 / 907 / 991 for immediate emergency assistance."
            ),
            font=("Segoe UI", 11),
            fg="#7f1d1d",
            bg="#fee2e2"
        ).pack(
            side="left",
            pady=18
        )

        # ----------------------------------------------------
        # SERVICES
        # ----------------------------------------------------

        tk.Label(
            content,
            text=self.t("Our Services"),
            font=("Segoe UI", 22, "bold"),
            fg=self.text,
            bg=self.bg
        ).pack(
            anchor="w",
            padx=30,
            pady=(10, 15)
        )

        services = tk.Frame(
            content,
            bg=self.bg
        )

        services.pack(
            fill="x",
            padx=25
        )

        # IMPORTANT:
        # Online Payment now goes directly to open_payment.
        service_data = [

            (
                "👤",
                "Patient Services",
                "Register, login, book appointments and manage your profile.",
                self.patient_portal
            ),

            (
                "🏥",
                "Hospital Services",
                "Register your hospital and manage hospital information.",
                self.hospital_portal
            ),

            (
                "👨‍⚕️",
                "Doctor Services",
                "Doctors can register, login and manage appointments.",
                self.doctor_portal
            ),

            (
                "💳",
                "Online Payment",
                "Pay consultation and appointment fees in ETB.",
                self.open_payment
            ),

            (
                "🩺",
                "Available Doctors",
                "View doctors who are currently available for appointments.",
                self.available_doctors
            ),

            (
                "🚑",
                "Emergency",
                "Find important emergency contacts and instructions.",
                self.emergency_page
            )
        ]

        for i, item in enumerate(service_data):

            row = i // 3
            col = i % 3

            box = tk.Frame(
                services,
                bg=self.card_color,
                highlightbackground=self.border,
                highlightthickness=1,
                cursor="hand2"
            )

            box.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=7,
                pady=7
            )

            services.grid_columnconfigure(
                col,
                weight=1
            )

            # ------------------------------------------------
            # CARD CLICK FUNCTION
            # ------------------------------------------------

            def activate_card(
                event=None,
                command=item[3]
            ):
                command()

            # Entire card is clickable
            box.bind(
                "<Button-1>",
                activate_card
            )

            # ------------------------------------------------
            # ICON
            # ------------------------------------------------

            icon = tk.Label(
                box,
                text=item[0],
                font=("Segoe UI Emoji", 28),
                bg=self.card_color,
                fg=self.primary,
                cursor="hand2"
            )

            icon.pack(
                anchor="w",
                padx=20,
                pady=(20, 5)
            )

            icon.bind(
                "<Button-1>",
                activate_card
            )

            # ------------------------------------------------
            # TITLE
            # ------------------------------------------------

            title = tk.Label(
                box,
                text=self.t(item[1]),
                font=("Segoe UI", 14, "bold"),
                bg=self.card_color,
                fg=self.text,
                cursor="hand2"
            )

            title.pack(
                anchor="w",
                padx=20
            )

            title.bind(
                "<Button-1>",
                activate_card
            )

            # ------------------------------------------------
            # DESCRIPTION
            # ------------------------------------------------

            description = tk.Label(
                box,
                text=self.t(item[2]),
                font=("Segoe UI", 10),
                bg=self.card_color,
                fg=self.muted,
                wraplength=280,
                justify="left",
                cursor="hand2"
            )

            description.pack(
                anchor="w",
                padx=20,
                pady=(5, 20)
            )

            description.bind(
                "<Button-1>",
                activate_card
            )

        # ----------------------------------------------------
        # ABOUT
        # ----------------------------------------------------

        about = self.card(
            content,
            30,
            30
        )

        tk.Label(
            about,
            text=self.t("Why EthioCare?"),
            font=("Segoe UI", 20, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        tk.Label(
            about,
            text=self.t(
                "EthioCare is a smart hospital patient service system designed "
                "to make healthcare services easier to access. Patients can "
                "register from home, search for doctors and hospitals, book "
                "appointments and make payments."
            ),
            font=("Segoe UI", 11),
            fg=self.muted,
            bg=self.card_color,
            wraplength=1000,
            justify="left"
        ).pack(
            anchor="w",
            pady=(10, 0)
        )

        # ----------------------------------------------------
        # ADMIN LOGIN
        # ----------------------------------------------------

        admin_area = self.card(
            content,
            30,
            10
        )

        tk.Label(
            admin_area,
            text="System Administration",
            font=("Segoe UI", 16, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        self.button(
            admin_area,
            "Administrator Login",
            self.admin_login,
            bg=INFO,
            width=28
        ).pack(
            pady=15
        )

    # ========================================================
    # ONLINE PAYMENT ENTRY
    # ========================================================

    def open_payment(self):

        # If patient is already logged in,
        # open payment directly.

        if (
            self.current_user is not None
            and self.current_user_type == "patient"
        ):

            self.make_payment()

        else:

            messagebox.showinfo(
                "Patient Login Required",
                "Please login as a patient before making an online payment."
            )

            self.patient_login()

    # ========================================================
    # PATIENT PORTAL
    # ========================================================

    def patient_portal(self):

        self.set_current_page(self.patient_portal)

        self.clear()

        self.header(
            "Patient Services"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Patient Services",
            "Choose an option to continue."
        )

        box = self.card(
            content,
            30,
            20
        )

        self.button(
            box,
            "Create Patient Account",
            self.patient_register,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Patient Login",
            self.patient_login,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Online Payment",
            self.open_payment,
            bg=SUCCESS,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Back", self.go_back,
            bg=self.muted,
            width=28
        ).pack(
            pady=10
        )

    # ========================================================
    # PATIENT REGISTER
    # ========================================================

    def return_to_patient_portal(self):
        # Patient Registration is a child screen of Patient Services.
        # Remove stale registration/portal history so the next Back
        # from Patient Services returns directly to Home.
        self.page_history = [
            page for page in self.page_history
            if page not in (
                self.patient_register,
                self.patient_portal
            )
        ]

        self._going_back = True
        try:
            self.patient_portal()
        finally:
            self._going_back = False

    def patient_register(self):

        self.set_current_page(self.patient_register)

        self.clear()

        self.header(
            "Patient Registration"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Create Patient Account",
            "Register once and access your healthcare services."
        )

        box = self.card(
            content,
            30,
            15
        )

        name = self.field(
            box,
            "Full Name"
        )

        age = self.field(
            box,
            "Age"
        )

        gender_var = tk.StringVar()

        tk.Label(
            box,
            text="Gender",
            font=("Segoe UI", 10, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        gender = ttk.Combobox(
            box,
            textvariable=gender_var,
            values=[
                "Male",
                "Female",
                "Other"
            ],
            state="readonly",
            font=("Segoe UI", 11)
        )

        gender.pack(
            fill="x",
            pady=(5, 7),
            ipady=6
        )

        phone = self.field(
            box,
            "Phone Number",
            default="+251 "
        )

        email = self.field(
            box,
            "Email"
        )

        address = self.field(
            box,
            "Address / Location"
        )

        password = self.password_field(
            box,
            "Password"
        )

        confirm = self.password_field(
            box,
            "Confirm Password"
        )

        def register():

            n = name.get().strip()
            a = age.get().strip()
            g = gender_var.get().strip()
            p = phone.get().strip()
            e = email.get().strip()
            ad = address.get().strip()
            pw = password.get()
            cp = confirm.get()

            if not all([
                n,
                a,
                g,
                p,
                e,
                ad,
                pw,
                cp
            ]):

                messagebox.showwarning(
                    "Missing Information",
                    "Please fill in all fields."
                )

                return

            try:

                age_num = int(a)

                if age_num <= 0 or age_num > 120:
                    raise ValueError

            except ValueError:

                messagebox.showerror(
                    "Invalid Age",
                    "Please enter a valid age."
                )

                return

            if pw != cp:

                messagebox.showerror(
                    "Password Error",
                    "Passwords do not match."
                )

                return

            if len(pw) < 4:

                messagebox.showwarning(
                    "Weak Password",
                    "Password should contain at least 4 characters."
                )

                return

            conn = get_db()

            existing = conn.execute("""
                SELECT patient_id
                FROM patients
                WHERE email = ?
            """, (
                e,
            )).fetchone()

            if existing:

                conn.close()

                messagebox.showerror(
                    "Already Registered",
                    "A patient with this email already exists."
                )

                return

            conn.execute("""
                INSERT INTO patients
                (
                    name,
                    age,
                    gender,
                    phone,
                    email,
                    address,
                    password,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                n,
                age_num,
                g,
                p,
                e,
                ad,
                hash_password(pw),
                self.now()
            ))

            patient_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Registration Successful",
                (
                    "Account created successfully!\n\n"
                    f"Patient ID: PAT-{1000 + patient_id}\n\n"
                    "Keep your Patient ID safe."
                )
            )

            self.patient_login()

        self.button(
            box,
            "Create Account",
            register,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.return_to_patient_portal,
            bg=self.muted,
            width=28
        ).pack(
            pady=(0, 15)
        )

    # ========================================================
    # PATIENT LOGIN
    # ========================================================

    def patient_login(self):

        self.set_current_page(self.patient_login)

        self.clear()

        # TOP-LEFT BACK BUTTON
        nav = tk.Frame(self.root, bg=self.bg, height=48)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        tk.Button(
            nav,
            text="←",
            command=self.go_back,
            font=("Segoe UI", 18, "bold"),
            bg=self.bg,
            fg=self.text,
            activebackground=self.primary,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18
        ).pack(side="left", padx=10, pady=5)

        self.header(
            "Patient Login"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Patient Login",
            "Login using your email and password."
        )

        box = self.card(
            content,
            30,
            20
        )

        email = self.field(
            box,
            "Email"
        )

        password = self.password_field(
            box
        )

        def login():

            e = email.get().strip()
            pw = password.get()

            if not e or not pw:

                messagebox.showwarning(
                    "Missing Information",
                    "Enter email and password."
                )

                return

            conn = get_db()

            user = conn.execute("""
                SELECT *
                FROM patients
                WHERE email = ?
                AND password = ?
            """, (
                e,
                hash_password(pw)
            )).fetchone()

            conn.close()

            if not user:

                messagebox.showerror(
                    "Login Failed",
                    "Incorrect email or password."
                )

                return

            self.current_user = dict(user)

            self.current_user_type = "patient"

            self.patient_dashboard()

        self.button(
            box,
            "Login",
            login,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Create Account",
            self.patient_register,
            bg=INFO,
            width=28
        ).pack(
            pady=5
        )

        self.button(
            box,
            "Back",
            self.patient_portal,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # PATIENT DASHBOARD
    # ========================================================

    def patient_dashboard(self):

        self.set_current_page(self.patient_dashboard)

        self.clear()

        # TOP-LEFT BACK BUTTON
        nav = tk.Frame(self.root, bg=self.bg, height=48)
        nav.pack(fill="x")
        nav.pack_propagate(False)

        tk.Button(
            nav,
            text="←",
            command=self.go_back,
            font=("Segoe UI", 18, "bold"),
            bg=self.bg,
            fg=self.text,
            activebackground=self.primary,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18
        ).pack(side="left", padx=10, pady=5)

        self.header(
            "Patient Dashboard"
        )

        content = self.make_scrollable_page()

        name = self.current_user["name"]

        self.page_title(
            content,
            f"Welcome, {name}",
            "Manage your healthcare services from one dashboard."
        )

        id_box = self.card(
            content,
            30,
            10
        )

        tk.Label(
            id_box,
            text="Patient ID",
            font=("Segoe UI", 10, "bold"),
            fg=self.muted,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        tk.Label(
            id_box,
            text=(
                f"PAT-{1000 + self.current_user['patient_id']}"
            ),
            font=("Segoe UI", 22, "bold"),
            fg=self.primary,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        services = tk.Frame(
            content,
            bg=self.bg
        )

        services.pack(
            fill="x",
            padx=25,
            pady=10
        )

        data = [

            (
                "👤",
                "My Profile",
                self.patient_profile
            ),

            (
                "📅",
                "Book Appointment",
                self.book_appointment
            ),

            (
                "📋",
                "My Appointments",
                self.patient_appointments
            ),

            (
                "💳",
                "Make Payment",
                self.make_payment
            ),

            (
                "💰",
                "Payment History",
                self.payment_history
            ),

            (
                "🩺",
                "Available Doctors",
                self.available_doctors
            ),

            (
                "🚪",
                "Logout",
                self.logout
            )
        ]

        for i, item in enumerate(data):

            row = i // 4
            col = i % 4

            box = tk.Frame(
                services,
                bg=self.card_color,
                highlightbackground=self.border,
                highlightthickness=1,
                cursor="hand2"
            )

            box.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=6,
                pady=6,
                ipadx=8,
                ipady=15
            )

            services.grid_columnconfigure(
                col,
                weight=1
            )

            tk.Label(
                box,
                text=item[0],
                font=("Segoe UI Emoji", 25),
                bg=self.card_color,
                fg=self.primary
            ).pack(
                pady=(10, 5)
            )

            tk.Label(
                box,
                text=item[1],
                font=("Segoe UI", 10, "bold"),
                bg=self.card_color,
                fg=self.text
            ).pack(
                pady=(0, 10)
            )

            box.bind(
                "<Button-1>",
                lambda e, command=item[2]: command()
            )

    # ========================================================
    # PATIENT PROFILE
    # ========================================================

    def patient_profile(self):

        self.set_current_page(self.patient_profile)

        self.clear()

        self.header(
            "My Profile"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "My Profile",
            "Your registered patient information."
        )

        box = self.card(
            content,
            30,
            20
        )

        fields = [

            (
                "Patient ID",
                f"PAT-{1000 + self.current_user['patient_id']}"
            ),

            (
                "Full Name",
                self.current_user["name"]
            ),

            (
                "Age",
                str(self.current_user["age"])
            ),

            (
                "Gender",
                self.current_user["gender"]
            ),

            (
                "Phone",
                self.current_user["phone"]
            ),

            (
                "Email",
                self.current_user["email"]
            ),

            (
                "Address",
                self.current_user["address"]
            ),

            (
                "Registered",
                self.current_user["created_at"]
            )
        ]

        for label, value in fields:

            row = tk.Frame(
                box,
                bg=self.card_color
            )

            row.pack(
                fill="x",
                pady=8
            )

            tk.Label(
                row,
                text=self.t(label),
                font=("Segoe UI", 10, "bold"),
                fg=self.muted,
                bg=self.card_color,
                width=18,
                anchor="w"
            ).pack(
                side="left"
            )

            tk.Label(
                row,
                text=value,
                font=("Segoe UI", 11),
                fg=self.text,
                bg=self.card_color,
                anchor="w"
            ).pack(
                side="left",
                fill="x",
                expand=True
            )

        self.button(
            box,
            "Back",
            self.patient_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # BOOK APPOINTMENT
    # ========================================================

    def book_appointment(self):

        self.set_current_page(self.book_appointment)

        self.clear()

        self.header(
            "Book Appointment"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Book Doctor Appointment",
            "Choose a doctor, date and time."
        )

        box = self.card(
            content,
            30,
            20
        )

        conn = get_db()

        doctors = conn.execute("""
            SELECT *
            FROM doctors
            ORDER BY name
        """).fetchall()

        conn.close()

        if not doctors:

            tk.Label(
                box,
                text="No doctors are registered yet.",
                font=("Segoe UI", 12),
                fg=self.muted,
                bg=self.card_color
            ).pack(
                pady=20
            )

            self.button(
                box,
                "Back",
                self.patient_dashboard,
                bg=self.muted,
                width=25
            ).pack(
                pady=10
            )

            return

        doctor_map = {}

        tk.Label(
            box,
            text="Doctor",
            font=("Segoe UI", 10, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        doctor_var = tk.StringVar()

        doctor_values = []

        for d in doctors:

            code = f"DOC-{1000 + d['doctor_id']}"

            display = (
                f"{code} | Dr. {d['name']} | "
                f"{d['specialization']} | "
                f"{d['hospital']}"
            )

            doctor_values.append(
                display
            )

            doctor_map[
                display
            ] = d["doctor_id"]

        doctor_combo = ttk.Combobox(
            box,
            textvariable=doctor_var,
            values=doctor_values,
            state="readonly",
            font=("Segoe UI", 10)
        )

        doctor_combo.pack(
            fill="x",
            pady=(5, 12),
            ipady=7
        )

        date_entry = self.field(
            box,
            "Appointment Date",
            default=(
                datetime.now() + timedelta(days=1)
            ).strftime("%Y-%m-%d")
        )

        time_entry = self.field(
            box,
            "Appointment Time",
            default="10:00"
        )

        reason = self.field(
            box,
            "Reason / Symptoms"
        )

        def book():

            selected = doctor_var.get().strip()
            date = date_entry.get().strip()
            time = time_entry.get().strip()
            rsn = reason.get().strip()

            if not selected or not date or not time or not rsn:

                messagebox.showwarning(
                    "Missing Information",
                    "Please fill in all appointment fields."
                )

                return

            try:

                datetime.strptime(
                    date,
                    "%Y-%m-%d"
                )

            except ValueError:

                messagebox.showerror(
                    "Invalid Date",
                    "Use date format YYYY-MM-DD."
                )

                return

            try:

                datetime.strptime(
                    time,
                    "%H:%M"
                )

            except ValueError:

                messagebox.showerror(
                    "Invalid Time",
                    "Use time format HH:MM."
                )

                return

            doctor_id = doctor_map[
                selected
            ]

            conn2 = get_db()

            conflict = conn2.execute("""
                SELECT id
                FROM appointments
                WHERE doctor_id = ?
                AND date = ?
                AND time = ?
                AND status != 'Cancelled'
            """, (
                doctor_id,
                date,
                time
            )).fetchone()

            if conflict:

                conn2.close()

                messagebox.showwarning(
                    "Time Unavailable",
                    "This doctor already has an appointment at this time."
                )

                return

            conn2.execute("""
                INSERT INTO appointments
                (
                    patient_id,
                    doctor_id,
                    date,
                    time,
                    reason,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, 'Pending', ?)
            """, (
                self.current_user["patient_id"],
                doctor_id,
                date,
                time,
                rsn,
                self.now()
            ))

            appointment_id = conn2.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            conn2.commit()
            conn2.close()

            messagebox.showinfo(
                "Appointment Booked",
                (
                    "Appointment booked successfully!\n\n"
                    f"Appointment ID: APP-{1000 + appointment_id}\n"
                    f"Date: {date}\n"
                    f"Time: {time}"
                )
            )

            self.patient_appointments()

        self.button(
            box,
            "Book Appointment",
            book,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.patient_dashboard,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # PATIENT APPOINTMENTS
    # ========================================================

    def patient_appointments(self):

        self.set_current_page(self.patient_appointments)

        self.clear()

        self.header(
            "My Appointments"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "My Appointments",
            "View your booked appointments."
        )

        box = self.card(
            content,
            20,
            15
        )

        conn = get_db()

        appointments = conn.execute("""
            SELECT
                a.*,
                d.name AS doctor_name,
                d.specialization,
                d.hospital
            FROM appointments a
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            WHERE a.patient_id = ?
            ORDER BY a.date DESC, a.time DESC
        """, (
            self.current_user["patient_id"],
        )).fetchall()

        conn.close()

        if not appointments:

            tk.Label(
                box,
                text="You do not have any appointments yet.",
                font=("Segoe UI", 12),
                fg=self.muted,
                bg=self.card_color
            ).pack(
                pady=30
            )

        else:

            for a in appointments:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=7
                )

                tk.Label(
                    item,
                    text=f"APP-{1000 + a['id']}",
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 3)
                )

                tk.Label(
                    item,
                    text=(
                        f"Doctor: Dr. {a['doctor_name']}\n"
                        f"Specialization: {a['specialization']}\n"
                        f"Hospital: {a['hospital']}\n"
                        f"Date: {a['date']}    Time: {a['time']}\n"
                        f"Reason: {a['reason']}\n"
                        f"Status: {a['status']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

                if a["status"] == "Pending":

                    def cancel_appointment(
                        appointment_id=a["id"]
                    ):

                        if not messagebox.askyesno(
                            "Cancel Appointment",
                            "Are you sure you want to cancel this appointment?"
                        ):
                            return

                        conn2 = get_db()

                        conn2.execute("""
                            UPDATE appointments
                            SET status = 'Cancelled'
                            WHERE id = ?
                            AND patient_id = ?
                        """, (
                            appointment_id,
                            self.current_user["patient_id"]
                        ))

                        conn2.commit()
                        conn2.close()

                        messagebox.showinfo(
                            "Cancelled",
                            "Appointment cancelled successfully."
                        )

                        self.patient_appointments()

                    self.button(
                        item,
                        "Cancel Appointment",
                        cancel_appointment,
                        bg=DANGER,
                        width=22
                    ).pack(
                        anchor="w",
                        padx=15,
                        pady=(0, 12)
                    )

        self.button(
            box,
            "Back",
            self.patient_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # PAYMENT
    # ========================================================

    def make_payment(self):

        self.set_current_page(self.make_payment)

        self.clear()

        self.header(
            "Online Payment"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Make Payment",
            "Pay your hospital consultation or appointment fee."
        )

        box = self.card(
            content,
            30,
            20
        )

        conn = get_db()

        appointments = conn.execute("""
            SELECT
                a.id,
                a.date,
                a.time,
                a.status,
                d.name AS doctor_name
            FROM appointments a
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            WHERE a.patient_id = ?
            AND a.status != 'Cancelled'
            ORDER BY a.date DESC
        """, (
            self.current_user["patient_id"],
        )).fetchall()

        conn.close()

        appointment_map = {}

        tk.Label(
            box,
            text="Appointment",
            font=("Segoe UI", 10, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        appointment_var = tk.StringVar()

        values = [
            "General Consultation"
        ]

        for a in appointments:

            display = (
                f"APP-{1000 + a['id']} | "
                f"Dr. {a['doctor_name']} | "
                f"{a['date']} {a['time']}"
            )

            values.append(
                display
            )

            appointment_map[
                display
            ] = a["id"]

        combo = ttk.Combobox(
            box,
            textvariable=appointment_var,
            values=values,
            state="readonly",
            font=("Segoe UI", 10)
        )

        combo.pack(
            fill="x",
            pady=(5, 15),
            ipady=7
        )

        combo.current(0)

        amount = self.field(
            box,
            "Amount (ETB)",
            default="500"
        )

        method_var = tk.StringVar(
            value="Telebirr"
        )

        tk.Label(
            box,
            text="Payment Method",
            font=("Segoe UI", 10, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        methods = [

            "Telebirr",
            "CBE Birr",
            "Bank Transfer",
            "Debit Card",
            "Cash at Hospital"
        ]

        method_combo = ttk.Combobox(
            box,
            textvariable=method_var,
            values=methods,
            state="readonly",
            font=("Segoe UI", 10)
        )

        method_combo.pack(
            fill="x",
            pady=(5, 15),
            ipady=7
        )

        transaction = self.field(
            box,
            "Transaction ID (optional)"
        )

        def pay():

            try:

                amt = float(
                    amount.get().strip()
                )

                if amt <= 0:
                    raise ValueError

            except ValueError:

                messagebox.showerror(
                    "Invalid Amount",
                    "Enter a valid payment amount."
                )

                return

            selected = appointment_var.get()

            appointment_id = appointment_map.get(
                selected
            )

            conn2 = get_db()

            conn2.execute("""
                INSERT INTO payments
                (
                    patient_id,
                    appointment_id,
                    amount,
                    method,
                    status,
                    transaction_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, 'Paid', ?, ?)
            """, (
                self.current_user["patient_id"],
                appointment_id,
                amt,
                method_var.get(),
                transaction.get().strip(),
                self.now()
            ))

            conn2.commit()
            conn2.close()

            messagebox.showinfo(
                "Payment Successful",
                (
                    "Payment completed successfully!\n\n"
                    f"Amount: {amt:,.2f} ETB\n"
                    f"Method: {method_var.get()}"
                )
            )

            self.payment_history()

        self.button(
            box,
            "Pay Now",
            pay,
            bg=SUCCESS,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.patient_dashboard,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # PAYMENT HISTORY
    # ========================================================

    def payment_history(self):

        self.set_current_page(self.payment_history)

        self.clear()

        self.header(
            "Payment History"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Payment History",
            "View all payments made through EthioCare."
        )

        box = self.card(
            content,
            20,
            15
        )

        conn = get_db()

        payments = conn.execute("""
            SELECT
                p.*,
                a.date,
                a.time
            FROM payments p
            LEFT JOIN appointments a
                ON p.appointment_id = a.id
            WHERE p.patient_id = ?
            ORDER BY p.payment_id DESC
        """, (
            self.current_user["patient_id"],
        )).fetchall()

        conn.close()

        if not payments:

            tk.Label(
                box,
                text="No payment history available.",
                font=("Segoe UI", 12),
                fg=self.muted,
                bg=self.card_color
            ).pack(
                pady=30
            )

        else:

            total = 0

            for p in payments:

                total += p["amount"]

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=7
                )

                appointment_text = (
                    f"APP-{1000 + p['appointment_id']}"
                    if p["appointment_id"]
                    else "General"
                )

                tk.Label(
                    item,
                    text=f"Payment #{p['payment_id']}",
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 4)
                )

                tk.Label(
                    item,
                    text=(
                        f"Amount: {p['amount']:,.2f} ETB\n"
                        f"Appointment: {appointment_text}\n"
                        f"Method: {p['method']}\n"
                        f"Status: {p['status']}\n"
                        f"Transaction ID: "
                        f"{p['transaction_id'] or 'N/A'}\n"
                        f"Date: {p['created_at']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

            total_box = tk.Frame(
                box,
                bg=self.primary
            )

            total_box.pack(
                fill="x",
                pady=15
            )

            tk.Label(
                total_box,
                text=f"Total Paid: {total:,.2f} ETB",
                font=("Segoe UI", 15, "bold"),
                fg="white",
                bg=self.primary
            ).pack(
                anchor="w",
                padx=20,
                pady=15
            )

        self.button(
            box,
            "Back",
            self.patient_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # HOSPITAL PORTAL
    # ========================================================

    def hospital_portal(self):

        self.set_current_page(self.hospital_portal)

        self.clear()

        self.header(
            "Hospital Services"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Hospital Services",
            "Register or login as a hospital."
        )

        box = self.card(
            content,
            30,
            20
        )

        self.button(
            box,
            "Register Hospital",
            self.hospital_register,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Hospital Login",
            self.hospital_login,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Back", self.go_back,
            bg=self.muted,
            width=28
        ).pack(
            pady=10
        )

    # ========================================================
    # HOSPITAL REGISTER
    # ========================================================

    def hospital_register(self):

        self.set_current_page(self.hospital_register)

        self.clear()

        self.header(
            "Hospital Registration"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Register Hospital",
            "Add your hospital to the EthioCare system."
        )

        box = self.card(
            content,
            30,
            20
        )

        name = self.field(
            box,
            "Hospital Name"
        )

        location = self.field(
            box,
            "Location"
        )

        phone = self.field(
            box,
            "Phone"
        )

        email = self.field(
            box,
            "Email"
        )

        address = self.field(
            box,
            "Full Address"
        )

        achievements = self.field(
            box,
            "Previous Achievements",
            default=""
        )

        password = self.password_field(
            box
        )

        confirm = self.password_field(
            box,
            "Confirm Password"
        )

        def register():

            n = name.get().strip()
            l = location.get().strip()
            p = phone.get().strip()
            e = email.get().strip()
            a = address.get().strip()
            ach = achievements.get().strip()
            pw = password.get()
            cp = confirm.get()

            if not all([
                n,
                l,
                p,
                e,
                a,
                pw,
                cp
            ]):

                messagebox.showwarning(
                    "Missing Information",
                    "Please fill in all fields."
                )

                return

            if pw != cp:

                messagebox.showerror(
                    "Password Error",
                    "Passwords do not match."
                )

                return

            conn = get_db()

            conn.execute("""
                INSERT INTO hospitals
                (
                    name,
                    location,
                    phone,
                    email,
                    address,
                    password,
                    achievements,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
            """, (
                n,
                l,
                p,
                e,
                a,
                hash_password(pw),
                ach,
                self.now()
            ))

            hospital_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Hospital Registered",
                (
                    "Hospital registration is waiting for administrator approval.\n\n"
                    f"Hospital ID: HOS-{1000 + hospital_id}"
                )
            )

            self.hospital_login()

        self.button(
            box,
            "Register Hospital",
            register,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.return_to_hospital_portal,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # HOSPITAL LOGIN
    # ========================================================

    def hospital_login(self):

        self.set_current_page(self.hospital_login)

        self.clear()

        self.header(
            "Hospital Login"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Hospital Login"
        )

        box = self.card(
            content,
            30,
            20
        )

        email = self.field(
            box,
            "Hospital Email"
        )

        password = self.password_field(
            box
        )

        def login():

            conn = get_db()

            user = conn.execute("""
                SELECT *
                FROM hospitals
                WHERE email = ?
                AND password = ?
            """, (
                email.get().strip(),
                hash_password(password.get())
            )).fetchone()

            conn.close()

            if not user:

                messagebox.showerror(
                    "Login Failed",
                    "Incorrect hospital email or password."
                )

                return

            self.current_user = dict(user)

            self.current_user_type = "hospital"

            self.hospital_dashboard()

        self.button(
            box,
            "Login",
            login,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Register Hospital",
            self.hospital_register,
            bg=INFO,
            width=28
        ).pack(
            pady=5
        )

        self.button(
            box,
            "Back",
            self.hospital_portal,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # HOSPITAL DASHBOARD
    # ========================================================

    def hospital_dashboard(self):

        self.set_current_page(self.hospital_dashboard)

        self.clear()

        self.header(
            "Hospital Dashboard"
        )

        content = self.make_scrollable_page()

        h = self.current_user

        self.page_title(
            content,
            f"Welcome, {h['name']}",
            "Hospital management dashboard."
        )

        box = self.card(
            content,
            30,
            20
        )

        tk.Label(
            box,
            text=(
                f"Hospital ID: HOS-{1000 + h['hospital_id']}"
            ),
            font=("Segoe UI", 16, "bold"),
            fg=self.primary,
            bg=self.card_color
        ).pack(
            anchor="w",
            pady=5
        )

        tk.Label(
            box,
            text=(
                f"Location: {h['location']}\n"
                f"Phone: {h['phone']}\n"
                f"Email: {h['email']}\n"
                f"Address: {h['address']}"
            ),
            font=("Segoe UI", 11),
            fg=self.text,
            bg=self.card_color,
            justify="left"
        ).pack(
            anchor="w",
            pady=15
        )

        self.button(
            box,
            "Logout",
            self.logout,
            bg=DANGER,
            width=25
        ).pack(
            pady=8
        )

    # ========================================================
    # DOCTOR PORTAL
    # ========================================================

    def doctor_portal(self):

        self.set_current_page(self.doctor_portal)

        self.clear()

        self.header(
            "Doctor Services"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Doctor Services",
            "Register or login as a doctor."
        )

        box = self.card(
            content,
            30,
            20
        )

        self.button(
            box,
            "Doctor Registration",
            self.doctor_register,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Doctor Login",
            self.doctor_login,
            width=28
        ).pack(
            pady=10
        )

        self.button(
            box,
            "Back", self.go_back,
            bg=self.muted,
            width=28
        ).pack(
            pady=10
        )

    # ========================================================
    # DOCTOR REGISTER
    # ========================================================

    def doctor_register(self):

        self.set_current_page(self.doctor_register)

        self.clear()

        self.header(
            "Doctor Registration"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Doctor Registration",
            "Register a doctor in the EthioCare system."
        )

        box = self.card(
            content,
            30,
            20
        )

        name = self.field(
            box,
            "Doctor Full Name"
        )

        specialization = self.field(
            box,
            "Specialization",
            default="General Practitioner"
        )

        phone = self.field(
            box,
            "Phone"
        )

        email = self.field(
            box,
            "Email"
        )

        hospital = self.field(
            box,
            "Hospital"
        )

        password = self.password_field(
            box
        )

        confirm = self.password_field(
            box,
            "Confirm Password"
        )

        def register():

            values = [

                name.get().strip(),
                specialization.get().strip(),
                phone.get().strip(),
                email.get().strip(),
                hospital.get().strip(),
                password.get(),
                confirm.get()
            ]

            if not all(values):

                messagebox.showwarning(
                    "Missing Information",
                    "Please fill in all fields."
                )

                return

            if password.get() != confirm.get():

                messagebox.showerror(
                    "Password Error",
                    "Passwords do not match."
                )

                return

            conn = get_db()

            existing = conn.execute("""
                SELECT doctor_id
                FROM doctors
                WHERE email = ?
            """, (
                email.get().strip(),
            )).fetchone()

            if existing:

                conn.close()

                messagebox.showerror(
                    "Already Registered",
                    "A doctor with this email already exists."
                )

                return

            conn.execute("""
                INSERT INTO doctors
                (
                    name,
                    specialization,
                    phone,
                    email,
                    hospital,
                    password,
                    available,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'Yes', ?)
            """, (
                name.get().strip(),
                specialization.get().strip(),
                phone.get().strip(),
                email.get().strip(),
                hospital.get().strip(),
                hash_password(password.get()),
                self.now()
            ))

            doctor_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Registration Successful",
                (
                    "Doctor registered successfully!\n\n"
                    f"Doctor ID: DOC-{1000 + doctor_id}"
                )
            )

            self.doctor_login()

        self.button(
            box,
            "Register Doctor",
            register,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.return_to_doctor_portal,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # DOCTOR LOGIN
    # ========================================================

    def doctor_login(self):

        self.set_current_page(self.doctor_login)

        self.clear()

        self.header(
            "Doctor Login"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Doctor Login"
        )

        box = self.card(
            content,
            30,
            20
        )

        email = self.field(
            box,
            "Doctor Email"
        )

        password = self.password_field(
            box
        )

        def login():

            conn = get_db()

            doctor = conn.execute("""
                SELECT *
                FROM doctors
                WHERE email = ?
                AND password = ?
            """, (
                email.get().strip(),
                hash_password(password.get())
            )).fetchone()

            conn.close()

            if not doctor:

                messagebox.showerror(
                    "Login Failed",
                    "Incorrect doctor email or password."
                )

                return

            self.current_user = dict(doctor)

            self.current_user_type = "doctor"

            self.doctor_dashboard()

        self.button(
            box,
            "Login",
            login,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Register Doctor",
            self.doctor_register,
            bg=INFO,
            width=28
        ).pack(
            pady=5
        )

        self.button(
            box,
            "Back",
            self.doctor_portal,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # DOCTOR DASHBOARD
    # ========================================================

    def doctor_dashboard(self):

        self.set_current_page(self.doctor_dashboard)

        self.clear()

        self.header(
            "Doctor Dashboard"
        )

        content = self.make_scrollable_page()

        d = self.current_user

        self.page_title(
            content,
            f"Dr. {d['name']}",
            "Doctor management dashboard."
        )

        box = self.card(
            content,
            30,
            20
        )

        tk.Label(
            box,
            text=(
                f"Doctor ID: DOC-{1000 + d['doctor_id']}"
            ),
            font=("Segoe UI", 16, "bold"),
            fg=self.primary,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        tk.Label(
            box,
            text=(
                f"Specialization: {d['specialization']}\n"
                f"Hospital: {d['hospital']}\n"
                f"Phone: {d['phone']}\n"
                f"Email: {d['email']}\n"
                f"Available: {d['available']}"
            ),
            font=("Segoe UI", 11),
            fg=self.text,
            bg=self.card_color,
            justify="left"
        ).pack(
            anchor="w",
            pady=15
        )

        self.button(
            box,
            "View My Appointments",
            self.doctor_appointments,
            width=28
        ).pack(
            pady=8
        )

        self.button(
            box,
            "Logout",
            self.logout,
            bg=DANGER,
            width=28
        ).pack(
            pady=8
        )

    # ========================================================
    # DOCTOR APPOINTMENTS
    # ========================================================

    def doctor_appointments(self):

        self.set_current_page(self.doctor_appointments)

        self.clear()

        self.header(
            "Doctor Appointments"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "My Appointments",
            "Appointments booked with you."
        )

        box = self.card(
            content,
            20,
            15
        )

        conn = get_db()

        appointments = conn.execute("""
            SELECT
                a.*,
                p.name AS patient_name,
                p.phone AS patient_phone,
                p.email AS patient_email
            FROM appointments a
            JOIN patients p
                ON a.patient_id = p.patient_id
            WHERE a.doctor_id = ?
            ORDER BY a.date DESC, a.time DESC
        """, (
            self.current_user["doctor_id"],
        )).fetchall()

        conn.close()

        if not appointments:

            tk.Label(
                box,
                text="No appointments found.",
                font=("Segoe UI", 12),
                fg=self.muted,
                bg=self.card_color
            ).pack(
                pady=30
            )

        else:

            for a in appointments:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=7
                )

                tk.Label(
                    item,
                    text=f"APP-{1000 + a['id']}",
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 4)
                )

                tk.Label(
                    item,
                    text=(
                        f"Patient: {a['patient_name']}\n"
                        f"Phone: {a['patient_phone']}\n"
                        f"Email: {a['patient_email']}\n"
                        f"Date: {a['date']}\n"
                        f"Time: {a['time']}\n"
                        f"Reason: {a['reason']}\n"
                        f"Status: {a['status']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

                if a["status"] == "Pending":

                    actions = tk.Frame(
                        item,
                        bg=self.bg
                    )

                    actions.pack(
                        anchor="w",
                        padx=15,
                        pady=(0, 12)
                    )

                    def update_status(
                        appointment_id,
                        new_status
                    ):

                        conn2 = get_db()

                        conn2.execute("""
                            UPDATE appointments
                            SET status = ?
                            WHERE id = ?
                        """, (
                            new_status,
                            appointment_id
                        ))

                        conn2.commit()
                        conn2.close()

                        if new_status == "Approved":
                            messagebox.showinfo(
                                "Appointment Approved",
                                "Appointment approved successfully."
                            )
                        else:
                            messagebox.showinfo(
                                "Appointment Rejected",
                                "Appointment rejected successfully."
                            )

                        self.doctor_appointments()

                    self.button(
                        actions,
                        "Approve",
                        lambda aid=a["id"]:
                        update_status(
                            aid,
                            "Approved"
                        ),
                        bg=SUCCESS,
                        width=12
                    ).pack(
                        side="left",
                        padx=(0, 7)
                    )

                    self.button(
                        actions,
                        "Reject",
                        lambda aid=a["id"]:
                        update_status(
                            aid,
                            "Rejected"
                        ),
                        bg=DANGER,
                        width=12
                    ).pack(
                        side="left"
                    )

        self.button(
            box,
            "Back",
            self.doctor_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # EMERGENCY
    # ========================================================

    def emergency_page(self):

        self.set_current_page(self.emergency_page)

        self.clear()

        self.header(
            "Emergency Help"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Emergency Assistance",
            "For immediate danger, contact emergency services."
        )

        alert = tk.Frame(
            content,
            bg="#fee2e2",
            highlightbackground="#fecaca",
            highlightthickness=1
        )

        alert.pack(
            fill="x",
            padx=30,
            pady=20
        )

        tk.Label(
            alert,
            text="🚑 EMERGENCY",
            font=("Segoe UI", 25, "bold"),
            fg=DANGER,
            bg="#fee2e2"
        ).pack(
            pady=(25, 10)
        )

        tk.Label(
            alert,
            text=(
                "Do not wait for the application "
                "if the situation is life-threatening."
            ),
            font=("Segoe UI", 11, "bold"),
            fg="#7f1d1d",
            bg="#fee2e2"
        ).pack(
            pady=(0, 25)
        )

        contacts = [

            (
                "911",
                "Emergency Assistance"
            ),

            (
                "907",
                "Ambulance / Emergency"
            ),

            (
                "991",
                "Police Emergency"
            )
        ]

        for number, description in contacts:

            box = self.card(
                content,
                30,
                7
            )

            tk.Label(
                box,
                text=number,
                font=("Segoe UI", 25, "bold"),
                fg=DANGER,
                bg=self.card_color
            ).pack(
                side="left",
                padx=15
            )

            tk.Label(
                box,
                text=description,
                font=("Segoe UI", 12, "bold"),
                fg=self.text,
                bg=self.card_color
            ).pack(
                side="left",
                padx=15
            )

        info = self.card(
            content,
            30,
            20
        )

        tk.Label(
            info,
            text="Emergency Safety Tips",
            font=("Segoe UI", 18, "bold"),
            fg=self.text,
            bg=self.card_color
        ).pack(
            anchor="w"
        )

        tips = [

            "Stay calm and provide your exact location.",
            "Call emergency services immediately.",
            "Do not drive yourself if you are seriously injured.",
            "Follow instructions from emergency responders.",
            "Keep important medical information available."
        ]

        for tip in tips:

            tk.Label(
                info,
                text="• " + tip,
                font=("Segoe UI", 11),
                fg=self.text,
                bg=self.card_color,
                justify="left"
            ).pack(
                anchor="w",
                pady=4
            )

        self.button(
            info,
            "Back", self.go_back,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # WINDOWS NOTIFICATION
    # ========================================================

    def show_windows_notification(
        self,
        title,
        message
    ):

        if not WIN_NOTIFY_AVAILABLE:
            return False

        try:

            toast = Notification(
                app_id="EthioCare",
                title=title,
                msg=message
            )

            toast.set_audio(
                audio.Reminder,
                loop=False
            )

            toast.show()

            return True

        except Exception:

            return False

    # ========================================================
    # NOTIFICATION PAGE
    # ========================================================

    def notification_page(self):

        self.set_current_page(self.notification_page)

        self.clear()

        self.header(
            "Notifications"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Notifications",
            "Appointment and system notification settings."
        )

        box = self.card(
            content,
            30,
            20
        )

        status = (
            "Windows notifications are available."
            if WIN_NOTIFY_AVAILABLE
            else
            "Windows notifications are not installed."
        )

        status_color = (
            SUCCESS
            if WIN_NOTIFY_AVAILABLE
            else
            WARNING
        )

        tk.Label(
            box,
            text=status,
            font=("Segoe UI", 12, "bold"),
            fg=status_color,
            bg=self.card_color
        ).pack(
            anchor="w",
            pady=10
        )

        if not WIN_NOTIFY_AVAILABLE:

            tk.Label(
                box,
                text=(
                    "To enable Windows popup notifications, "
                    "open your terminal and run:\n\n"
                    "python -m pip install winotify"
                ),
                font=("Segoe UI", 11),
                fg=self.text,
                bg=self.card_color,
                justify="left"
            ).pack(
                anchor="w",
                pady=10
            )

        def test_notification():

            if not WIN_NOTIFY_AVAILABLE:

                messagebox.showwarning(
                    "Winotify Not Installed",
                    (
                        "Install winotify first:\n\n"
                        "python -m pip install winotify"
                    )
                )

                return

            success = self.show_windows_notification(
                "EthioCare Test Notification",
                "Your Windows notifications are working!"
            )

            if success:

                messagebox.showinfo(
                    "Notification Sent",
                    "A Windows notification was sent."
                )

            else:

                messagebox.showerror(
                    "Notification Error",
                    "The Windows notification could not be sent."
                )

        self.button(
            box,
            "Test Windows Notification",
            test_notification,
            bg=INFO,
            width=30
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.patient_dashboard,
            bg=self.muted,
            width=30
        ).pack(
            pady=5
        )

    # ========================================================
    # ADMIN LOGIN
    # ========================================================

    def admin_login(self):

        self.set_current_page(self.admin_login)

        self.clear()

        self.header(
            "Admin Login"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Administrator Login",
            "System administration area."
        )

        box = self.card(
            content,
            30,
            20
        )

        username = self.field(
            box,
            "Username",
            default="admin"
        )

        password = self.password_field(
            box
        )

        def login():

            conn = get_db()

            admin = conn.execute("""
                SELECT *
                FROM admins
                WHERE username = ?
                AND password = ?
            """, (
                username.get().strip(),
                hash_password(password.get())
            )).fetchone()

            conn.close()

            if not admin:

                messagebox.showerror(
                    "Login Failed",
                    "Incorrect administrator username or password."
                )

                return

            self.current_user = dict(admin)

            self.current_user_type = "admin"

            self.admin_dashboard()

        self.button(
            box,
            "Admin Login",
            login,
            width=28
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back", self.go_back,
            bg=self.muted,
            width=28
        ).pack(
            pady=5
        )

    # ========================================================
    # ADMIN DASHBOARD
    # ========================================================

    def admin_dashboard(self):

        self.set_current_page(self.admin_dashboard)

        self.clear()

        self.header(
            "Admin Dashboard"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Administrator Dashboard",
            "Manage the EthioCare system."
        )

        conn = get_db()

        patient_count = conn.execute(
            "SELECT COUNT(*) AS c FROM patients"
        ).fetchone()["c"]

        doctor_count = conn.execute(
            "SELECT COUNT(*) AS c FROM doctors"
        ).fetchone()["c"]

        hospital_count = conn.execute(
            "SELECT COUNT(*) AS c FROM hospitals"
        ).fetchone()["c"]

        pending_hospital_count = conn.execute(
            "SELECT COUNT(*) AS c FROM hospitals WHERE status = 'Pending'"
        ).fetchone()["c"]

        appointment_count = conn.execute(
            "SELECT COUNT(*) AS c FROM appointments"
        ).fetchone()["c"]

        payment_count = conn.execute(
            "SELECT COUNT(*) AS c FROM payments"
        ).fetchone()["c"]

        conn.close()

        stats = tk.Frame(
            content,
            bg=self.bg
        )

        stats.pack(
            fill="x",
            padx=25,
            pady=10
        )

        stat_data = [

            (
                "Patients",
                patient_count
            ),

            (
                "Doctors",
                doctor_count
            ),

            (
                "Hospitals",
                hospital_count
            ),

            (
                "Pending Hospitals",
                pending_hospital_count
            ),

            (
                "Appointments",
                appointment_count
            ),

            (
                "Payments",
                payment_count
            )
        ]

        for i, (label, number) in enumerate(
            stat_data
        ):

            box = tk.Frame(
                stats,
                bg=self.card_color,
                highlightbackground=self.border,
                highlightthickness=1
            )

            box.grid(
                row=0,
                column=i,
                sticky="nsew",
                padx=5
            )

            stats.grid_columnconfigure(
                i,
                weight=1
            )

            tk.Label(
                box,
                text=str(number),
                font=("Segoe UI", 25, "bold"),
                fg=self.primary,
                bg=self.card_color
            ).pack(
                pady=(15, 2)
            )

            tk.Label(
                box,
                text=label,
                font=("Segoe UI", 10, "bold"),
                fg=self.muted,
                bg=self.card_color
            ).pack(
                pady=(0, 15)
            )

        box = self.card(
            content,
            30,
            20
        )

        options = [

            (
                "View All Patients",
                self.admin_patients
            ),

            (
                "View All Doctors",
                self.admin_doctors
            ),

            (
                "Available Doctors",
                self.available_doctors
            ),

            (
                "View All Hospitals",
                self.admin_hospitals
            ),

            (
                "Pending Hospitals",
                self.admin_hospital_approvals
            ),

            (
                "View All Appointments",
                self.admin_appointments
            ),

            (
                "View All Payments",
                self.admin_payments
            ),

            (
                "Delete Patient",
                self.admin_delete_patient
            ),

            (
                "Delete Doctor",
                self.admin_delete_doctor
            ),

            (
                "Logout",
                self.logout
            )
        ]

        for text, command in options:

            bg = self.primary

            if "Delete" in text:
                bg = DANGER

            if text == "Logout":
                bg = DANGER

            self.button(
                box,
                text,
                command,
                bg=bg,
                width=30
            ).pack(
                pady=5
            )

    # ========================================================
    # ADMIN PATIENTS
    # ========================================================

    def admin_patients(self):

        self.set_current_page(self.admin_patients)

        self.clear()

        self.header(
            "All Patients"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "All Registered Patients"
        )

        box = self.card(
            content,
            15,
            15
        )

        conn = get_db()

        patients = conn.execute("""
            SELECT *
            FROM patients
            ORDER BY patient_id DESC
        """).fetchall()

        conn.close()

        if not patients:

            tk.Label(
                box,
                text="No patients registered.",
                fg=self.muted,
                bg=self.card_color,
                font=("Segoe UI", 11)
            ).pack(
                pady=30
            )

        else:

            for p in patients:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=5
                )

                tk.Label(
                    item,
                    text=(
                        f"PAT-{1000 + p['patient_id']} | "
                        f"{p['name']}"
                    ),
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 4)
                )

                tk.Label(
                    item,
                    text=(
                        f"Age: {p['age']} | Gender: {p['gender']}\n"
                        f"Phone: {p['phone']}\n"
                        f"Email: {p['email']}\n"
                        f"Address: {p['address']}\n"
                        f"Registered: {p['created_at']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # AVAILABLE DOCTORS
    # ========================================================

    def available_doctors(self):

        self.set_current_page(self.available_doctors)

        self.clear()

        self.header(
            "Available Doctors"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Available Doctors",
            "Doctors currently marked as available for appointments."
        )

        box = self.card(
            content,
            20,
            20
        )

        conn = get_db()

        doctors = conn.execute(
            """
            SELECT doctor_id, name, specialization, hospital,
                   phone, email, available
            FROM doctors
            WHERE LOWER(COALESCE(available, 'No')) = 'yes'
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()

        conn.close()

        if not doctors:

            tk.Label(
                box,
                text="No doctors are currently available.",
                font=("Segoe UI", 13, "bold"),
                fg=self.muted,
                bg=self.card_color
            ).pack(pady=35)

        else:

            for d in doctors:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=7
                )

                top = tk.Frame(
                    item,
                    bg=self.bg
                )
                top.pack(
                    fill="x",
                    padx=18,
                    pady=(14, 5)
                )

                tk.Label(
                    top,
                    text=f"🩺  Dr. {d['name']}",
                    font=("Segoe UI", 14, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(side="left")

                tk.Label(
                    top,
                    text="● AVAILABLE",
                    font=("Segoe UI", 9, "bold"),
                    fg="#16803c",
                    bg=self.bg
                ).pack(side="right")

                tk.Label(
                    item,
                    text=(
                        f"Specialization: {d['specialization']}\n"
                        f"Hospital: {d['hospital']}\n"
                        f"Phone: {d['phone']}\n"
                        f"Email: {d['email']}\n"
                        f"Doctor ID: DOC-{1000 + d['doctor_id']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=18,
                    pady=(0, 14)
                )

                if self.current_user_type == "patient":
                    self.button(
                        item,
                        "Book Appointment",
                        self.book_appointment,
                        width=20
                    ).pack(
                        anchor="w",
                        padx=18,
                        pady=(0, 14)
                    )

        self.button(
            box,
            "←",
            self.go_back,
            bg=self.muted,
            width=6
        ).pack(pady=20)

    # ========================================================
    # ADMIN DOCTORS
    # ========================================================

    def admin_doctors(self):

        self.set_current_page(self.admin_doctors)

        self.clear()

        self.header(
            "All Doctors"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "All Registered Doctors"
        )

        box = self.card(
            content,
            15,
            15
        )

        conn = get_db()

        doctors = conn.execute("""
            SELECT *
            FROM doctors
            ORDER BY doctor_id DESC
        """).fetchall()

        conn.close()

        if not doctors:

            tk.Label(
                box,
                text="No doctors registered.",
                fg=self.muted,
                bg=self.card_color,
                font=("Segoe UI", 11)
            ).pack(
                pady=30
            )

        else:

            for d in doctors:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=5
                )

                tk.Label(
                    item,
                    text=(
                        f"DOC-{1000 + d['doctor_id']} | "
                        f"Dr. {d['name']}"
                    ),
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 4)
                )

                tk.Label(
                    item,
                    text=(
                        f"Specialization: {d['specialization']}\n"
                        f"Hospital: {d['hospital']}\n"
                        f"Phone: {d['phone']}\n"
                        f"Email: {d['email']}\n"
                        f"Available: {d['available']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )


    # ========================================================
    # ADMIN HOSPITAL APPROVALS
    # ========================================================

    def admin_hospital_approvals(self):
        self.set_current_page(self.admin_hospital_approvals)
        self.clear()

        self.header("Hospital Approval")

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Pending Hospitals",
            "Review registered hospitals and accept or reject them."
        )

        box = self.card(
            content,
            15,
            15
        )

        conn = get_db()
        hospitals = conn.execute("""
            SELECT *
            FROM hospitals
            WHERE status = 'Pending'
            ORDER BY hospital_id DESC
        """).fetchall()
        conn.close()

        if not hospitals:
            tk.Label(
                box,
                text="No pending hospitals.",
                fg=self.muted,
                bg=self.card_color,
                font=("Segoe UI", 11)
            ).pack(pady=30)
        else:
            for h in hospitals:
                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )
                item.pack(fill="x", pady=7)

                tk.Label(
                    item,
                    text=f"HOS-{1000 + h['hospital_id']} | {h['name']}",
                    font=("Segoe UI", 13, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(anchor="w", padx=15, pady=(12, 5))

                details = (
                    f"Location: {h['location']}\n"
                    f"Phone: {h['phone']}\n"
                    f"Email: {h['email']}\n"
                    f"Address: {h['address']}\n"
                    f"Previous Achievements: {h['achievements'] or 'None provided'}\n"
                    f"Hospital Status: {h['status']}"
                )

                tk.Label(
                    item,
                    text=details,
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left",
                    wraplength=900
                ).pack(anchor="w", padx=15, pady=(0, 10))

                actions = tk.Frame(item, bg=self.bg)
                actions.pack(anchor="w", padx=15, pady=(0, 12))

                def update_hospital_status(hospital_id, status):
                    conn2 = get_db()
                    conn2.execute(
                        "UPDATE hospitals SET status = ? WHERE hospital_id = ?",
                        (status, hospital_id)
                    )
                    conn2.commit()
                    conn2.close()

                    if status == "Approved":
                        messagebox.showinfo(
                            "Hospital Approval",
                            "Hospital approved successfully."
                        )
                    else:
                        messagebox.showinfo(
                            "Hospital Approval",
                            "Hospital rejected successfully."
                        )

                    self.admin_hospital_approvals()

                self.button(
                    actions,
                    "Accept",
                    lambda hid=h["hospital_id"]:
                    update_hospital_status(hid, "Approved"),
                    bg=SUCCESS,
                    width=12
                ).pack(side="left", padx=(0, 8))

                self.button(
                    actions,
                    "Reject",
                    lambda hid=h["hospital_id"]:
                    update_hospital_status(hid, "Rejected"),
                    bg=DANGER,
                    width=12
                ).pack(side="left")

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(pady=20)

    # ========================================================
    # ADMIN HOSPITALS
    # ========================================================

    def admin_hospitals(self):

        self.set_current_page(self.admin_hospitals)

        self.clear()

        self.header(
            "All Hospitals"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "All Registered Hospitals"
        )

        box = self.card(
            content,
            15,
            15
        )

        conn = get_db()

        hospitals = conn.execute("""
            SELECT *
            FROM hospitals
            ORDER BY hospital_id DESC
        """).fetchall()

        conn.close()

        if not hospitals:

            tk.Label(
                box,
                text="No hospitals registered.",
                fg=self.muted,
                bg=self.card_color,
                font=("Segoe UI", 11)
            ).pack(
                pady=30
            )

        else:

            for h in hospitals:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=5
                )

                tk.Label(
                    item,
                    text=(
                        f"HOS-{1000 + h['hospital_id']} | "
                        f"{h['name']}"
                    ),
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 4)
                )

                tk.Label(
                    item,
                    text=(
                        f"Location: {h['location']}\n"
                        f"Phone: {h['phone']}\n"
                        f"Email: {h['email']}\n"
                        f"Address: {h['address']}\n"
                        f"Previous Achievements: {h['achievements'] or 'None provided'}\n"
                        f"Hospital Status: {h['status']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

        self.button(
            box,
            "Pending Hospitals",
            self.admin_hospital_approvals,
            bg=WARNING,
            width=25
        ).pack(
            pady=6
        )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # ADMIN APPOINTMENTS
    # ========================================================

    def admin_appointments(self):

        self.set_current_page(self.admin_appointments)

        self.clear()

        self.header(
            "All Appointments"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "All Appointments"
        )

        box = self.card(
            content,
            15,
            15
        )

        conn = get_db()

        appointments = conn.execute("""
            SELECT
                a.*,
                p.name AS patient_name,
                d.name AS doctor_name
            FROM appointments a
            JOIN patients p
                ON a.patient_id = p.patient_id
            JOIN doctors d
                ON a.doctor_id = d.doctor_id
            ORDER BY a.id DESC
        """).fetchall()

        conn.close()

        if not appointments:

            tk.Label(
                box,
                text="No appointments.",
                fg=self.muted,
                bg=self.card_color,
                font=("Segoe UI", 11)
            ).pack(
                pady=30
            )

        else:

            for a in appointments:

                item = tk.Frame(
                    box,
                    bg=self.bg,
                    highlightbackground=self.border,
                    highlightthickness=1
                )

                item.pack(
                    fill="x",
                    pady=5
                )

                tk.Label(
                    item,
                    text=f"APP-{1000 + a['id']}",
                    font=("Segoe UI", 12, "bold"),
                    fg=self.primary,
                    bg=self.bg
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(12, 4)
                )

                tk.Label(
                    item,
                    text=(
                        f"Patient: {a['patient_name']}\n"
                        f"Doctor: Dr. {a['doctor_name']}\n"
                        f"Date: {a['date']}    Time: {a['time']}\n"
                        f"Reason: {a['reason']}\n"
                        f"Status: {a['status']}"
                    ),
                    font=("Segoe UI", 10),
                    fg=self.text,
                    bg=self.bg,
                    justify="left"
                ).pack(
                    anchor="w",
                    padx=15,
                    pady=(0, 12)
                )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # ADMIN PAYMENTS
    # ========================================================

    def admin_payments(self):

        self.set_current_page(self.admin_payments)

        self.clear()

        self.header(
            "All Payments"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "All Payments"
        )

        box = self.card(
            content,
            15,
            15
        )

        conn = get_db()

        payments = conn.execute("""
            SELECT
                p.*,
                patients.name AS patient_name
            FROM payments p
            JOIN patients
                ON p.patient_id = patients.patient_id
            ORDER BY p.payment_id DESC
        """).fetchall()

        conn.close()

        total = 0

        if not payments:

            tk.Label(
                box,
                text="No payments recorded.",
                font=("Segoe UI", 12),
                fg=self.muted,
                bg=self.card_color
            ).pack(
                pady=30
            )

        for p in payments:

            total += p["amount"]

            item = tk.Frame(
                box,
                bg=self.bg,
                highlightbackground=self.border,
                highlightthickness=1
            )

            item.pack(
                fill="x",
                pady=5
            )

            tk.Label(
                item,
                text=f"Payment #{p['payment_id']}",
                font=("Segoe UI", 12, "bold"),
                fg=self.primary,
                bg=self.bg
            ).pack(
                anchor="w",
                padx=15,
                pady=(12, 4)
            )

            tk.Label(
                item,
                text=(
                    f"Patient: {p['patient_name']}\n"
                    f"Amount: {p['amount']:,.2f} ETB\n"
                    f"Method: {p['method']}\n"
                    f"Status: {p['status']}\n"
                    f"Transaction ID: "
                    f"{p['transaction_id'] or 'N/A'}\n"
                    f"Date: {p['created_at']}"
                ),
                font=("Segoe UI", 10),
                fg=self.text,
                bg=self.bg,
                justify="left"
            ).pack(
                anchor="w",
                padx=15,
                pady=(0, 12)
            )

        total_box = tk.Frame(
            box,
            bg=self.primary
        )

        total_box.pack(
            fill="x",
            pady=15
        )

        tk.Label(
            total_box,
            text=(
                f"Total Payments: "
                f"{total:,.2f} ETB"
            ),
            font=("Segoe UI", 15, "bold"),
            fg="white",
            bg=self.primary
        ).pack(
            padx=20,
            pady=15
        )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=20
        )

    # ========================================================
    # DELETE PATIENT
    # ========================================================

    def admin_delete_patient(self):

        self.set_current_page(self.admin_delete_patient)

        self.clear()

        self.header(
            "Delete Patient"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Delete Patient",
            "Delete a registered patient from the system."
        )

        box = self.card(
            content,
            30,
            20
        )

        patient_id = self.field(
            box,
            "Patient ID",
            default="PAT-1001"
        )

        def delete():

            value = patient_id.get().strip().upper()

            if value.startswith("PAT-"):

                value = value.replace(
                    "PAT-",
                    ""
                )

            try:

                pid = int(value) - 1000

                if pid <= 0:
                    raise ValueError

            except ValueError:

                messagebox.showerror(
                    "Invalid ID",
                    "Enter a valid Patient ID such as PAT-1001."
                )

                return

            conn = get_db()

            patient = conn.execute(
                """
                SELECT name
                FROM patients
                WHERE patient_id = ?
                """,
                (pid,)
            ).fetchone()

            if not patient:

                conn.close()

                messagebox.showerror(
                    "Not Found",
                    "Patient not found."
                )

                return

            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Delete patient {patient['name']}?"
            )

            if not confirm:

                conn.close()

                return

            conn.execute(
                "DELETE FROM patients WHERE patient_id = ?",
                (pid,)
            )

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Deleted",
                "Patient deleted successfully."
            )

            self.admin_dashboard()

        self.button(
            box,
            "Delete Patient",
            delete,
            bg=DANGER,
            width=25
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=5
        )

    # ========================================================
    # DELETE DOCTOR
    # ========================================================

    def admin_delete_doctor(self):

        self.set_current_page(self.admin_delete_doctor)

        self.clear()

        self.header(
            "Delete Doctor"
        )

        content = self.make_scrollable_page()

        self.page_title(
            content,
            "Delete Doctor",
            "Delete a registered doctor from the system."
        )

        box = self.card(
            content,
            30,
            20
        )

        doctor_id = self.field(
            box,
            "Doctor ID",
            default="DOC-1001"
        )

        def delete():

            value = doctor_id.get().strip().upper()

            if value.startswith("DOC-"):

                value = value.replace(
                    "DOC-",
                    ""
                )

            try:

                did = int(value) - 1000

                if did <= 0:
                    raise ValueError

            except ValueError:

                messagebox.showerror(
                    "Invalid ID",
                    "Enter a valid Doctor ID such as DOC-1001."
                )

                return

            conn = get_db()

            doctor = conn.execute(
                """
                SELECT name
                FROM doctors
                WHERE doctor_id = ?
                """,
                (did,)
            ).fetchone()

            if not doctor:

                conn.close()

                messagebox.showerror(
                    "Not Found",
                    "Doctor not found."
                )

                return

            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Delete Dr. {doctor['name']}?"
            )

            if not confirm:

                conn.close()

                return

            conn.execute(
                "DELETE FROM doctors WHERE doctor_id = ?",
                (did,)
            )

            conn.commit()
            conn.close()

            messagebox.showinfo(
                "Deleted",
                "Doctor deleted successfully."
            )

            self.admin_dashboard()

        # IMPORTANT:
        # Delete Doctor button is included.
        self.button(
            box,
            "Delete Doctor",
            delete,
            bg=DANGER,
            width=25
        ).pack(
            pady=15
        )

        self.button(
            box,
            "Back",
            self.admin_dashboard,
            bg=self.muted,
            width=25
        ).pack(
            pady=5
        )

    # ========================================================
    # LOGOUT
    # ========================================================

    def logout():

        pass


# ============================================================
# FIX LOGOUT METHOD
# ============================================================

def hospital_app_logout(self):

    self.current_user = None

    self.current_user_type = None

    self.page_history.clear()
    self._going_back = True
    self.current_page = self.show_home

    messagebox.showinfo(
        "Logged Out",
        "You have been logged out successfully."
    )

    self.show_home()


HospitalApp.logout = hospital_app_logout


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    setup_database()

    root = tk.Tk()

    app = HospitalApp(
        root
    )

    root.mainloop()