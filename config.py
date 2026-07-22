"""
config.py
=========================================
PSX Smart Terminal Configuration
=========================================
Author : Ali Labs
Version: 1.0
"""

from pathlib import Path

# ==========================================================
# APPLICATION
# ==========================================================

APP_NAME = "PSX Smart Terminal"
VERSION = "1.0.0"

# ==========================================================
# DIRECTORIES
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

# On Android the app's source folder is read-only (it's inside
# the APK), so the database and logs must live in writable app
# storage instead. android.storage is only importable on-device.
try:
    from android.storage import app_storage_path  # noqa
    DATA_DIR = Path(app_storage_path())
except Exception:
    DATA_DIR = BASE_DIR

ASSETS_DIR = BASE_DIR / "assets"
LOG_DIR = DATA_DIR / "logs"

DATABASE_FILE = DATA_DIR / "psx.db"

ICON_FILE = ASSETS_DIR / "icon.ico"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# PSX API
# ==========================================================

BASE_URL = "https://dps.psx.com.pk"

SYMBOLS_URL = f"{BASE_URL}/symbols"

MARKET_WATCH_URL = f"{BASE_URL}/market-watch"

HISTORY_URL = f"{BASE_URL}/historical"

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer":
        "https://dps.psx.com.pk/",
}

REQUEST_TIMEOUT = 30

# ==========================================================
# HISTORY SETTINGS
# ==========================================================

MONTHS_HISTORY = 7

MAX_RETRIES = 3

REQUEST_DELAY = 0.25

# ==========================================================
# ANALYZER SETTINGS
# ==========================================================

NEAR_LOW_PERCENT = 10.0
MIN_DISCOUNT_PERCENT = 35.0

WATCH_SCORE = 40
BASE_SCORE = 55
RECOVERY_SCORE = 70
BUY_SCORE = 85
STRONG_BUY_SCORE = 95

# ----------------------------------------------------------
# PRIMARY POSITION FILTER (accumulation scanner)
# ----------------------------------------------------------
# Only stocks trading within the lowest POSITION_FILTER_LIMIT %
# of their 7-month range are scored at all. Everything above
# this is skipped before scoring, per the "buy near the bottom
# of the range" strategy. Can be overridden at runtime via the
# 'position_filter' setting in the settings table.

POSITION_FILTER_LIMIT = 30.0

# Stocks trading below this average daily volume are treated as
# too illiquid and penalized ("Extremely Low Volume"). Overridable
# via the 'min_volume' setting.
MIN_AVG_VOLUME = 50000

# A rebound of less than this % from the 7-month low is
# considered a "Weak Bounce" and penalized.
MIN_BOUNCE_PERCENT = 3.0

# ----------------------------------------------------------
# SIGNAL THRESHOLDS (score out of 100, after the position filter)
# ----------------------------------------------------------

SIGNAL_STRONG_BUY = 85
SIGNAL_BUY = 65
SIGNAL_WATCH_PLUS = 45
SIGNAL_WATCH = 25
# below SIGNAL_WATCH -> IGNORE

# ==========================================================
# GUI SETTINGS
# ==========================================================

WINDOW_WIDTH = 1450
WINDOW_HEIGHT = 850

REFRESH_INTERVAL = 300

THEME = "dark"

# ==========================================================
# DATABASE TABLES
# ==========================================================

TABLE_SYMBOLS = "symbols"
TABLE_HISTORY = "history"
TABLE_ANALYSIS = "analysis"
TABLE_SETTINGS = "settings"
TABLE_SIGNAL_HISTORY = "signal_history"

# ==========================================================
# LOGGING
# ==========================================================

LOG_FILE = LOG_DIR / "terminal.log"

LOG_LEVEL = "INFO"

# ==========================================================
# SIGNALS
# ==========================================================

IGNORE = "IGNORE"
WATCH = "WATCH"
BASE_FORMING = "BASE FORMING"
RECOVERY = "RECOVERY"
BUY_SETUP = "BUY SETUP"
STRONG_BUY = "STRONG BUY"