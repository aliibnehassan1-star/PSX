"""
settings_schema.py
====================================================
Single source of truth for every user-editable setting.

Each entry becomes one row in the Settings screen and one key in the
`settings` SQLite table. This is the in-app equivalent of editing
config.py / a .env file by hand -- nothing here requires a rebuild.

Fields:
    key      -- row key in the settings table
    label    -- shown in the UI
    group    -- section heading in the Settings screen
    type     -- "float" | "int" | "bool"
    default  -- fallback value (mirrors config.py)
    hint     -- short explanation shown under the field
"""

from __future__ import annotations

import config

SETTINGS_SCHEMA = [
    # ------------------------------------------------------------
    # SCANNER -- the core accumulation-strategy knobs
    # ------------------------------------------------------------
    {
        "key": "position_filter",
        "label": "Position Filter Limit (%)",
        "group": "Scanner",
        "type": "float",
        "default": config.POSITION_FILTER_LIMIT,
        "hint": "Only stocks trading within the lowest X% of their 7-month range are analyzed. Everything above is ignored (0-30 recommended).",
    },
    {
        "key": "min_volume",
        "label": "Minimum Average Volume",
        "group": "Scanner",
        "type": "int",
        "default": config.MIN_AVG_VOLUME,
        "hint": "Stocks averaging below this daily volume are penalized as illiquid.",
    },
    {
        "key": "min_bounce",
        "label": "Minimum Bounce off Low (%)",
        "group": "Scanner",
        "type": "float",
        "default": config.MIN_BOUNCE_PERCENT,
        "hint": "A rebound smaller than this from the 7-month low is treated as a Weak Bounce penalty.",
    },
    # ------------------------------------------------------------
    # SIGNAL THRESHOLDS -- score cutoffs (0-100) after filtering
    # ------------------------------------------------------------
    {
        "key": "signal_strong_buy",
        "label": "STRONG BUY Score Cutoff",
        "group": "Signal Thresholds",
        "type": "int",
        "default": config.SIGNAL_STRONG_BUY,
        "hint": "Minimum score for STRONG BUY.",
    },
    {
        "key": "signal_buy",
        "label": "BUY Score Cutoff",
        "group": "Signal Thresholds",
        "type": "int",
        "default": config.SIGNAL_BUY,
        "hint": "Minimum score for BUY.",
    },
    {
        "key": "signal_watch_plus",
        "label": "WATCH+ Score Cutoff",
        "group": "Signal Thresholds",
        "type": "int",
        "default": config.SIGNAL_WATCH_PLUS,
        "hint": "Minimum score for WATCH+.",
    },
    {
        "key": "signal_watch",
        "label": "WATCH Score Cutoff",
        "group": "Signal Thresholds",
        "type": "int",
        "default": config.SIGNAL_WATCH,
        "hint": "Minimum score for WATCH. Below this -> IGNORE.",
    },
    # ------------------------------------------------------------
    # DATA DOWNLOAD -- how market_data.py fetches history
    # ------------------------------------------------------------
    {
        "key": "months_history",
        "label": "Months of History (first run)",
        "group": "Data Download",
        "type": "int",
        "default": config.MONTHS_HISTORY,
        "hint": "How many months of history to backfill the first time a symbol is downloaded.",
    },
    {
        "key": "request_timeout",
        "label": "Request Timeout (seconds)",
        "group": "Data Download",
        "type": "int",
        "default": config.REQUEST_TIMEOUT,
        "hint": "How long to wait on a single PSX request before giving up.",
    },
    # ------------------------------------------------------------
    # APP BEHAVIOR
    # ------------------------------------------------------------
    {
        "key": "auto_interval",
        "label": "Auto Update Interval (seconds)",
        "group": "App Behavior",
        "type": "int",
        "default": config.REFRESH_INTERVAL,
        "hint": "How often the app re-downloads data automatically in the background.",
    },
    {
        "key": "auto_analysis",
        "label": "Auto-Analyze after Update",
        "group": "App Behavior",
        "type": "bool",
        "default": True,
        "hint": "Automatically re-run analysis every time the database updates.",
    },
    {
        "key": "notifications_on",
        "label": "Notifications",
        "group": "App Behavior",
        "type": "bool",
        "default": True,
        "hint": "Notify on WATCH->BUY and BUY->STRONG BUY upgrades only.",
    },
    {
        "key": "dark_mode",
        "label": "Dark Mode",
        "group": "App Behavior",
        "type": "bool",
        "default": True,
        "hint": "",
    },
    {
        "key": "store_filtered",
        "label": "Store Filtered-Out Stocks",
        "group": "App Behavior",
        "type": "bool",
        "default": False,
        "hint": "Keep stocks above the position filter in the database (signal=FILTERED) instead of discarding them.",
    },
]

GROUP_ORDER = ["Scanner", "Signal Thresholds", "Data Download", "App Behavior"]


def grouped_schema():
    groups = {g: [] for g in GROUP_ORDER}
    for item in SETTINGS_SCHEMA:
        groups.setdefault(item["group"], []).append(item)
    return [(g, groups[g]) for g in GROUP_ORDER if groups.get(g)]
