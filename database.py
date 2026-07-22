"""
database.py
==================================================
PSX Smart Terminal Database Manager
==================================================
Handles:
    - Database creation
    - Table creation
    - Insert/Update symbols
    - Insert/Update history
    - Read history
    - Save analysis
    - Watchlist
    - Settings
"""

from __future__ import annotations

import sqlite3
from typing import List, Dict, Optional

import pandas as pd

import config


class Database:

    def __init__(self):

        self.conn = sqlite3.connect(
            config.DATABASE_FILE,
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.create_tables()

    # =====================================================
    # CREATE TABLES
    # =====================================================

    def create_tables(self):

        cursor = self.conn.cursor()

        # -----------------------------------------
        # Symbols
        # -----------------------------------------

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS symbols(

            symbol TEXT PRIMARY KEY,

            company TEXT,

            sector TEXT,

            etf INTEGER,

            debt INTEGER

        )

        """)

        # -----------------------------------------
        # History
        # -----------------------------------------

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS history(

            symbol TEXT,

            date TEXT,

            open REAL,

            high REAL,

            low REAL,

            close REAL,

            volume INTEGER,

            PRIMARY KEY(symbol,date)

        )

        """)
        # -----------------------------------------
        # Analysis
        # -----------------------------------------

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS analysis(

            symbol TEXT PRIMARY KEY,

            current_price REAL,

            high_7m REAL,

            low_7m REAL,

            discount REAL,

            position REAL,

            bounce REAL,

            avg_volume REAL,

            trend TEXT,

            near_low INTEGER,

            recovery INTEGER,

            paused INTEGER,

            bullish INTEGER,

            volume_up INTEGER,

            new_low INTEGER,

            score INTEGER,

            signal TEXT,

            status TEXT,

            updated TEXT

        )

        """)

        # Migration: older databases created before 'bounce' existed
        cursor.execute("PRAGMA table_info(analysis)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        if "bounce" not in existing_cols:
            cursor.execute("ALTER TABLE analysis ADD COLUMN bounce REAL DEFAULT 0")

        # -----------------------------------------
        # Settings
        # -----------------------------------------

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS settings(

            key TEXT PRIMARY KEY,

            value TEXT

        )

        """)

        # -----------------------------------------
        # Signal History
        # -----------------------------------------

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS signal_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            symbol TEXT,

            signal TEXT,

            score INTEGER,

            price REAL,

            datetime TEXT

        )

        """)

        self.conn.commit()

    # =====================================================
    # SYMBOLS
    # =====================================================

    def save_symbols(self, symbols: List[Dict]):

        cursor = self.conn.cursor()

        for item in symbols:

            cursor.execute("""

            INSERT OR REPLACE INTO symbols

            VALUES(?,?,?,?,?)

            """, (

                item.get("symbol"),

                item.get("name"),

                item.get("sectorName"),

                int(item.get("isETF", False)),

                int(item.get("isDebt", False))

            ))

        self.conn.commit()

    def get_symbols(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT *

        FROM symbols

        ORDER BY symbol

        """)

        return [dict(x) for x in cursor.fetchall()]
    
    def get_symbol_info(self, symbol):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT company, sector

        FROM symbols

        WHERE symbol=?

        """, (symbol,))

        row = cursor.fetchone()

        if row:

            return dict(row)

        return {

            "company": "",

            "sector": ""

        }
    
    
    def total_symbols(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT COUNT(*)

        FROM symbols

        """)

        return cursor.fetchone()[0]


    def history_count(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT COUNT(*)

        FROM history

        """)

        return cursor.fetchone()[0]
    
    def is_empty(self):

        return self.history_count() == 0


    def latest_database_date(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT MAX(date)

        FROM history

        """)

        return cursor.fetchone()[0]

    # =====================================================
    # HISTORY
    # =====================================================

    def save_history(self, symbol: str, df: pd.DataFrame):

        if df.empty:
            return

        cursor = self.conn.cursor()

        for _, row in df.iterrows():

            cursor.execute("""

            INSERT OR REPLACE INTO history

            VALUES(?,?,?,?,?,?,?)

            """, (

                symbol,

                str(row["DATE"])[:10],

                float(row["OPEN"]),

                float(row["HIGH"]),

                float(row["LOW"]),

                float(row["CLOSE"]),

                int(row["VOLUME"])

            ))

        self.conn.commit()

    def last_history_date(self, symbol: str):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT MAX(date)

        FROM history

        WHERE symbol=?

        """, (symbol,))

        result = cursor.fetchone()[0]

        return result

    def load_history(self, symbol: str):

        query = """

        SELECT *

        FROM history

        WHERE symbol=?

        ORDER BY date

        """

        return pd.read_sql_query(

            query,

            self.conn,

            params=(symbol,)

        )

    def load_all_history(self):

        query = """

        SELECT *

        FROM history

        ORDER BY symbol, date

        """

        return pd.read_sql_query(

            query,

            self.conn

        )
    
    def delete_history(self, symbol):

        cursor = self.conn.cursor()

        cursor.execute("""

        DELETE FROM history

        WHERE symbol=?

        """, (symbol,))

        self.conn.commit()


    def clear_history(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        DELETE FROM history

        """)

        self.conn.commit()


    def load_all_symbols_history(self):

        symbols = self.get_symbols()

        data = {}

        for item in symbols:

            symbol = item["symbol"]

            data[symbol] = self.load_history(symbol)

        return data


    def symbol_exists(self, symbol):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT 1

        FROM symbols

        WHERE symbol=?

        LIMIT 1

        """, (symbol,))

        return cursor.fetchone() is not None


    def history_exists(self, symbol):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT 1

        FROM history

        WHERE symbol=?

        LIMIT 1

        """, (symbol,))

        return cursor.fetchone() is not None
    # =====================================================
    # ANALYSIS
    # =====================================================

    def save_analysis(self, data: Dict):

        cursor = self.conn.cursor()

        cursor.execute("""

        INSERT OR REPLACE INTO analysis

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """, (

            data["symbol"],

            data["current_price"],

            data["high_7m"],

            data["low_7m"],

            data["discount"],

            data["position"],

            data.get("bounce", 0),

            data["avg_volume"],

            data["trend"],

            int(data["near_low"]),

            int(data["recovery"]),

            int(data["paused"]),

            int(data["bullish"]),

            int(data["volume_up"]),

            int(data["new_low"]),

            data["score"],

            data["signal"],

            data["status"],

            data["updated"]

        ))

        self.conn.commit()

    def load_watchlist(self):

        query = """

        SELECT *

        FROM analysis

        WHERE signal IN ('WATCH','WATCH+','BUY','STRONG BUY')

        ORDER BY score DESC

        """

        return pd.read_sql_query(

            query,

            self.conn

        )
    
    def load_analysis(self):

        query = """

        SELECT *

        FROM analysis

        ORDER BY score DESC

        """

        return pd.read_sql_query(

            query,

            self.conn

        )


    def clear_analysis(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        DELETE FROM analysis

        """)

        self.conn.commit()


    def get_watchlist_count(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT COUNT(*)

        FROM analysis

        WHERE signal!='IGNORE'

        """)

        return cursor.fetchone()[0]
    
    def dashboard_stats(self):

        cursor = self.conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM symbols")
        stats["symbols"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM history")
        stats["history"] = cursor.fetchone()[0]

        # Stocks passing the position filter = everything currently
        # stored in `analysis` (filtered-out stocks aren't stored
        # by default -- see analyzer.py).
        cursor.execute("SELECT COUNT(*) FROM analysis")
        stats["passed_filter"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM analysis WHERE signal='STRONG BUY'")
        stats["strong_buy"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM analysis WHERE signal='BUY'")
        stats["buy"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM analysis WHERE signal IN ('WATCH','WATCH+')")
        stats["watch"] = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(date) FROM history")
        stats["db_last_updated"] = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(updated) FROM analysis")
        stats["analysis_last_updated"] = cursor.fetchone()[0]

        return stats

    def database_stats(self):

        cursor = self.conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM symbols")
        stats["symbols"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM history")
        stats["history"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM analysis")
        stats["analysis"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM signal_history")
        stats["signals"] = cursor.fetchone()[0]

        return stats

    # =====================================================
    # SETTINGS
    # =====================================================

    def set_setting(self, key, value):

        cursor = self.conn.cursor()

        cursor.execute("""

        INSERT OR REPLACE INTO settings

        VALUES(?,?)

        """, (key, str(value)))

        self.conn.commit()

    def get_setting(self, key):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT value

        FROM settings

        WHERE key=?

        """, (key,))

        result = cursor.fetchone()

        if result:
            return result["value"]

        return None
    
    def has_setting(self, key):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT 1

        FROM settings

        WHERE key=?

        LIMIT 1

        """, (key,))

        return cursor.fetchone() is not None

    # =====================================================
    # SIGNAL HISTORY
    # =====================================================

    def add_signal(self,

                   symbol,

                   signal,

                   score,

                   price,

                   dt):

        cursor = self.conn.cursor()

        cursor.execute("""

        INSERT INTO signal_history

        (

            symbol,

            signal,

            score,

            price,

            datetime

        )

        VALUES(?,?,?,?,?)

        """, (

            symbol,

            signal,

            score,

            price,

            dt

        ))

        self.conn.commit()
    def get_latest_signal(self, symbol):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT *

        FROM signal_history

        WHERE symbol=?

        ORDER BY id DESC

        LIMIT 1

        """, (symbol,))

        row = cursor.fetchone()

        if row:

            return dict(row)

        return None


    def load_signal_history(self, symbol):

        query = """

        SELECT *

        FROM signal_history

        WHERE symbol=?

        ORDER BY datetime DESC

        """

        return pd.read_sql_query(

            query,

            self.conn,

            params=(symbol,)

        )
    
    def clear_signal_history(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        DELETE FROM signal_history

        """)

        self.conn.commit()
    # =====================================================
    # CLOSE
    # =====================================================
    def clear_symbols(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        DELETE FROM symbols

        """)

        self.conn.commit()


    def reset_database(self):

        self.clear_history()

        self.clear_analysis()

        self.clear_signal_history()

        self.clear_symbols()

        
    def vacuum(self):

        self.conn.execute("VACUUM")

        self.conn.commit()
    def close(self):

        self.conn.close()


db = Database()