"""
market_data.py
====================================================
PSX Smart Terminal
Market Data Engine
====================================================

Handles:
    • Download PSX symbols
    • Download live market data
    • Download historical data
    • Update database

Author : Ali Labs
"""

from __future__ import annotations

import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Callable, Optional

import config
from database import db


class MarketData:

    def __init__(self,
                 progress_callback: Optional[Callable] = None):

        self.session = requests.Session()

        self.session.headers.update(config.HEADERS)

        self.progress = progress_callback

        self.total_symbols = 0

    @property
    def timeout(self):
        try:
            from database import db
            value = db.get_setting("request_timeout")
            return int(value) if value else config.REQUEST_TIMEOUT
        except Exception:
            return config.REQUEST_TIMEOUT

    # =====================================================
    # Progress
    # =====================================================

    def _progress(
        self,
        current: int,
        total: int,
        symbol: str,
        status: str
    ):

        if self.progress:

            self.progress(
                current,
                total,
                symbol,
                status
            )

        else:

            print(
                f"[{current}/{total}] "
                f"{symbol:<8} "
                f"{status}"
            )

    # =====================================================
    # Download All Symbols
    # =====================================================

    def fetch_symbols(self):

        response = self.session.get(

            config.SYMBOLS_URL,

            timeout=self.timeout

        )

        response.raise_for_status()

        symbols = response.json()

        db.save_symbols(symbols)

        self.total_symbols = len(symbols)

        return symbols

    # =====================================================
    # Download Live Market
    # =====================================================

    def fetch_live_market(self):

        response = self.session.get(

            config.MARKET_WATCH_URL,

            timeout=self.timeout

        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        table = soup.find("table")

        if table is None:

            return pd.DataFrame()

        rows = []

        tbody = table.find("tbody")

        if tbody is None:

            return pd.DataFrame()

        for tr in tbody.find_all("tr"):

            cols = [

                td.get_text(strip=True)

                for td in tr.find_all("td")

            ]

            if len(cols) >= 9:

                rows.append(cols)

        if not rows:

            return pd.DataFrame()

        df = pd.DataFrame(rows)

        return df

    # =====================================================
    # Market Watch Symbols Only
    # =====================================================

    def fetch_market_symbols(self):

        df = self.fetch_live_market()

        if df.empty:
            return []

        symbols = []

        for symbol in df.iloc[:, 0]:

            symbol = str(symbol).strip()

            if symbol:

                symbols.append({
                    "symbol": symbol
                })

        return symbols
    # =====================================================
    # Download One Month
    # =====================================================

    def _download_month(
        self,
        symbol,
        month,
        year
    ):

        payload = {

            "month": month,

            "year": year,

            "symbol": symbol

        }

        response = self.session.post(

            config.HISTORY_URL,

            data=payload,

            timeout=self.timeout

        )

        response.raise_for_status()

        return response.text

    # =====================================================
    # Parse Historical HTML
    # =====================================================

    def _parse_history(self, html):

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        table = soup.find(
            "table",
            id="historicalTable"
        )

        if table is None:

            return pd.DataFrame()

        tbody = table.find("tbody")

        if tbody is None:

            return pd.DataFrame()

        rows = []

        for tr in tbody.find_all("tr"):

            cols = [

                td.get_text(strip=True)

                for td in tr.find_all("td")

            ]

            if len(cols) == 6:

                rows.append(cols)

        if not rows:

            return pd.DataFrame()

        return pd.DataFrame(

            rows,

            columns=[

                "DATE",

                "OPEN",

                "HIGH",

                "LOW",

                "CLOSE",

                "VOLUME"

            ]

        )

    # =====================================================
    # Clean DataFrame
    # =====================================================

    def _clean_history(self, df):

        if df.empty:

            return df

        df["DATE"] = pd.to_datetime(

            df["DATE"],

            format="%b %d, %Y",

            errors="coerce"

        )

        for col in [

            "OPEN",

            "HIGH",

            "LOW",

            "CLOSE"

        ]:

            df[col] = (

                df[col]

                .astype(str)

                .str.replace(",", "")

                .astype(float)

            )

        df["VOLUME"] = (

            df["VOLUME"]

            .astype(str)

            .str.replace(",", "")

            .astype(int)

        )

        df.drop_duplicates(

            subset=["DATE"],

            inplace=True

        )

        df.sort_values(

            "DATE",

            inplace=True

        )

        df.reset_index(

            drop=True,

            inplace=True
        )

        return df

        # =====================================================
    # Get Missing Months
    # =====================================================

    def _get_missing_months(self, last_date):
        """
        Returns the months that need to be downloaded.

        First Run:
            Returns previous N months.

        Later Runs:
            Returns only missing months.
        """

        today = datetime.today()

        # ----------------------------
        # First Run
        # ----------------------------

        if last_date is None:

            months = []

            month = today.month
            year = today.year

            try:
                from database import db as _db
                months_setting = _db.get_setting("months_history")
                months_history = int(months_setting) if months_setting else config.MONTHS_HISTORY
            except Exception:
                months_history = config.MONTHS_HISTORY

            for _ in range(months_history):

                months.append((month, year))

                month -= 1

                if month == 0:
                    month = 12
                    year -= 1

            months.reverse()

            return months

        # ----------------------------
        # Incremental Update
        # ----------------------------

        if isinstance(last_date, str):

            last_date = datetime.strptime(
                last_date,
                "%Y-%m-%d"
            )

        months = []

        month = last_date.month
        year = last_date.year

        while (year < today.year) or (
            year == today.year and month <= today.month
        ):

            months.append((month, year))

            month += 1

            if month == 13:
                month = 1
                year += 1

        return months


    # =====================================================
    # Fetch History
    # =====================================================

    def fetch_history(self, symbol):
        """
        Downloads all required history for one symbol.
        """

        last_date = db.last_history_date(symbol)

        months = self._get_missing_months(last_date)

        frames = []

        for month, year in months:

            try:

                html = self._download_month(
                    symbol,
                    month,
                    year
                )

                df = self._parse_history(html)

                df = self._clean_history(df)

                if not df.empty:

                    frames.append(df)

            except Exception as e:

                print(
                    f"{symbol} {month}/{year} : {e}"
                )

        if not frames:

            return pd.DataFrame()

        history = pd.concat(
            frames,
            ignore_index=True
        )

        history.drop_duplicates(
            subset=["DATE"],
            inplace=True
        )

        history.sort_values(
            "DATE",
            inplace=True
        )

        # Keep only new records
        if last_date is not None:

            last_date = pd.to_datetime(last_date)

            history = history[
                history["DATE"] > last_date
            ]

        history.reset_index(
            drop=True,
            inplace=True
        )

        return history

        # =====================================================
    # Update One Symbol
    # =====================================================

    def update_symbol(self, symbol):

        history = self.fetch_history(symbol)

        if history.empty:
            return 0

        db.save_history(symbol, history)

        return len(history)
    
        # =====================================================
    # Update Complete Database
    # =====================================================

    def update_database(self):
        """
        First Run:
            Downloads previous 7 months for every symbol.

        Later Runs:
            Downloads only missing history.
        """

        symbols = self.fetch_market_symbols()

        total = len(symbols)

        success = 0
        updated = 0
        failed = 0

        print("\n" + "=" * 70)
        print("PSX DATABASE UPDATE STARTED")
        print("=" * 70)

        for index, item in enumerate(symbols, start=1):

            symbol = item["symbol"]

            try:

                rows = self.update_symbol(symbol)

                if rows > 0:

                    updated += 1

                    self._progress(
                        index,
                        total,
                        symbol,
                        f"Added {rows} rows"
                    )

                else:

                    self._progress(
                        index,
                        total,
                        symbol,
                        "Already Updated"
                    )

                success += 1

            except Exception as e:

                failed += 1

                self._progress(
                    index,
                    total,
                    symbol,
                    f"FAILED : {e}"
                )

        print("\n" + "=" * 70)
        print("DATABASE UPDATE COMPLETED")
        print("=" * 70)
        print(f"Symbols        : {total}")
        print(f"Successful     : {success}")
        print(f"Updated        : {updated}")
        print(f"Failed         : {failed}")
        print("=" * 70)

market = MarketData()

if __name__ == "__main__":

    market.update_database()