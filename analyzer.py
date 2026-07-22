"""
analyzer.py
====================================================
PSX Smart Terminal
Institutional Accumulation Analysis Engine
====================================================

Core philosophy:
    We are not hunting for stocks making new highs.
    We are hunting for quality companies currently trading
    near the BOTTOM of their 7-month range, because that is
    where the best risk-to-reward accumulation opportunities
    are.

Pipeline for every symbol:
    1. Load history. No history -> skip.
    2. Compute Position % (where price sits in the 7M range).
    3. PRIMARY FILTER: Position % must be 0-30% (configurable).
       Anything above that is ignored immediately and never
       reaches the scoring engine.
    4. Only stocks that pass the filter get scored (0-100).
    5. Score maps to a signal: STRONG BUY / BUY / WATCH+ / WATCH / IGNORE.

Author : Ali Labs
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

import config
from database import db


class Analyzer:

    def __init__(self):

        self.updated = datetime.now()

    # =====================================================
    # SETTINGS (overridable at runtime, fall back to config)
    # =====================================================

    def position_filter_limit(self):

        value = db.get_setting("position_filter")

        return float(value) if value else config.POSITION_FILTER_LIMIT

    def min_avg_volume(self):

        value = db.get_setting("min_volume")

        return float(value) if value else config.MIN_AVG_VOLUME

    def min_bounce_percent(self):

        value = db.get_setting("min_bounce")

        return float(value) if value else config.MIN_BOUNCE_PERCENT

    def signal_thresholds(self):

        return {
            "STRONG BUY": float(db.get_setting("signal_strong_buy") or config.SIGNAL_STRONG_BUY),
            "BUY": float(db.get_setting("signal_buy") or config.SIGNAL_BUY),
            "WATCH+": float(db.get_setting("signal_watch_plus") or config.SIGNAL_WATCH_PLUS),
            "WATCH": float(db.get_setting("signal_watch") or config.SIGNAL_WATCH),
        }

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def safe(value):

        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def round2(value):

        return round(float(value), 2)

    # =====================================================
    # BASIC CALCULATIONS
    # =====================================================

    def high_7m(self, df):

        if df.empty:
            return 0

        return float(df["high"].max())

    def low_7m(self, df):

        if df.empty:
            return 0

        return float(df["low"].min())

    def current_price(self, df):

        if df.empty:
            return 0

        return float(df.iloc[-1]["close"])

    def average_volume(self, df):

        if df.empty:
            return 0

        return float(df["volume"].mean())

    def highest_close(self, df):

        if df.empty:
            return 0

        return float(df["close"].max())

    def lowest_close(self, df):

        if df.empty:
            return 0

        return float(df["close"].min())

    def average_close(self, df):

        if df.empty:
            return 0

        return float(df["close"].mean())

    def latest_volume(self, df):

        if df.empty:
            return 0

        return float(df.iloc[-1]["volume"])

    # =====================================================
    # DISCOUNT %  (discount from the 7-month high)
    # =====================================================

    def discount_percent(self, current, highest):

        if highest <= 0:
            return 0

        return self.round2(
            ((highest - current) / highest) * 100
        )

    # =====================================================
    # POSITION %  (where price sits inside the 7M range)
    # 0%   = sitting exactly at the 7-month low
    # 100% = sitting exactly at the 7-month high
    # =====================================================

    def position_percent(self, current, highest, lowest):

        rng = highest - lowest

        if rng <= 0:
            return 0

        return self.round2(
            ((current - lowest) / rng) * 100
        )

    # =====================================================
    # BOUNCE %  (rebound off the 7-month low)
    # =====================================================

    def bounce_percent(self, current, lowest):

        if lowest <= 0:
            return 0

        return self.round2(
            ((current - lowest) / lowest) * 100
        )

    # =====================================================
    # TREND
    # =====================================================

    def trend(self, df):

        if len(df) < 5:
            return "UNKNOWN"

        closes = df["close"].tail(5).tolist()

        if closes[-1] > closes[0]:
            return "UP"
        elif closes[-1] < closes[0]:
            return "DOWN"

        return "SIDEWAYS"

    # =====================================================
    # RECOVERY -- three consecutive higher closes
    # =====================================================

    def recovery(self, df):

        if len(df) < 3:
            return False

        closes = df["close"].tail(3).tolist()

        return closes[0] < closes[1] < closes[2]

    # =====================================================
    # PAUSE -- sideways action near the bottom (accumulation)
    # =====================================================

    def paused(self, df):

        if len(df) < 3:
            return False

        lows = df["low"].tail(3)

        difference = lows.max() - lows.min()

        return difference <= lows.mean() * 0.01

    # =====================================================
    # BULLISH CANDLE -- latest close above latest open
    # =====================================================

    def bullish(self, df):

        if df.empty:
            return False

        last = df.iloc[-1]

        return last["close"] > last["open"]

    # =====================================================
    # VOLUME -- is recent volume increasing vs prior period?
    # =====================================================

    def volume_up(self, df):

        if len(df) < 10:
            return False

        previous = df["volume"].iloc[-10:-5].mean()

        recent = df["volume"].tail(5).mean()

        return recent > previous

    # =====================================================
    # NEW LOW -- did the stock make a fresh low today?
    # =====================================================

    def new_low(self, df):

        if len(df) < 2:
            return False

        return df.iloc[-1]["low"] < df.iloc[-2]["low"]

    # =====================================================
    # SCORING ENGINE
    # ----------------------------------------------------
    # Only called for stocks that already passed the
    # Position % <= filter_limit primary filter.
    #
    #   Position inside the filter window ..... 40
    #   Discount from high ..................... 20
    #   Recovery pattern ....................... 15
    #   Trend improvement ...................... 10
    #   Volume increasing ...................... 10
    #   Bullish candle .......................... 5
    #   ------------------------------------------
    #   Max ..................................... 100
    #
    # Position is scaled within the filter window itself:
    # sitting right at the 7-month low earns the full 40,
    # sitting at the edge of the window earns close to 0 --
    # this rewards stocks closer to the bottom, matching the
    # "buy near the bottom" philosophy, instead of treating
    # every stock inside the window identically.
    #
    # Penalties:
    #   New low today ......................... -20
    #   Strong downtrend ....................... -15
    #   Extremely low volume ................... -10
    #   Poor recovery (no recovery + downtrend) . -5
    #   Weak bounce off the low ................. -5
    # =====================================================

    def calculate_score(
        self,
        position,
        filter_limit,
        discount,
        avg_volume,
        min_volume,
        bounce,
        trend,
        recovery,
        paused,
        bullish,
        volume_up,
        new_low,
    ):

        score = 0

        # ---- Position inside filter window (scaled, closer to low = more points)
        if filter_limit > 0:
            closeness = max(0.0, 1 - (position / filter_limit))
            score += 40 * closeness

        # ---- Discount from high
        if discount >= 50:
            score += 20
        elif discount >= 40:
            score += 15
        elif discount >= 30:
            score += 10
        elif discount >= 20:
            score += 5

        # ---- Recovery pattern
        if recovery:
            score += 15

        # ---- Trend improvement
        if trend == "UP":
            score += 10
        elif trend == "SIDEWAYS":
            score += 5

        # ---- Volume increasing
        if volume_up:
            score += 10

        # ---- Bullish candle
        if bullish:
            score += 5

        # ---- Small bonus for a quiet base (accumulation)
        if paused:
            score += 5

        # ================= PENALTIES =================

        if new_low:
            score -= 20

        if trend == "DOWN":
            score -= 15

        if avg_volume < min_volume:
            score -= 10

        if not recovery and trend == "DOWN":
            score -= 5

        if bounce < self.min_bounce_percent():
            score -= 5

        score = max(0, min(round(score), 100))

        return score

    # =====================================================
    # SIGNAL ENGINE
    # =====================================================

    def generate_signal(self, score):

        t = self.signal_thresholds()

        if score >= t["STRONG BUY"]:
            return "STRONG BUY"
        elif score >= t["BUY"]:
            return "BUY"
        elif score >= t["WATCH+"]:
            return "WATCH+"
        elif score >= t["WATCH"]:
            return "WATCH"

        return "IGNORE"

    # =====================================================
    # STATUS
    # =====================================================

    def market_status(self, trend, recovery, new_low):

        if new_low:
            return "FALLING"

        if recovery:
            return "RECOVERING"

        if trend == "UP":
            return "RISING"

        if trend == "DOWN":
            return "DECLINING"

        return "SIDEWAYS"

    # =====================================================
    # ANALYZE ONE SYMBOL
    # =====================================================

    def analyze_symbol(self, symbol):

        history = db.load_history(symbol)

        if history.empty:
            return None

        highest = self.high_7m(history)
        lowest = self.low_7m(history)
        current = self.current_price(history)
        avg_volume = self.average_volume(history)

        position = self.position_percent(current, highest, lowest)

        filter_limit = self.position_filter_limit()

        # ============================================================
        # PRIMARY FILTER -- the single most important rule.
        # Stocks trading above the lowest `filter_limit` % of their
        # 7-month range are not scored at all. By default they are
        # not stored in `analysis` (kept out of the watchlist and off
        # the dashboard). Set the 'store_filtered' setting to "1" to
        # instead store them with signal=FILTERED / status=ABOVE_POSITION_LIMIT.
        # ============================================================

        if position > filter_limit:

            if db.get_setting("store_filtered") == "1":

                return {
                    "symbol": symbol,
                    "current_price": current,
                    "high_7m": highest,
                    "low_7m": lowest,
                    "discount": self.discount_percent(current, highest),
                    "position": position,
                    "bounce": self.bounce_percent(current, lowest),
                    "avg_volume": avg_volume,
                    "trend": self.trend(history),
                    "near_low": False,
                    "recovery": False,
                    "paused": False,
                    "bullish": False,
                    "volume_up": False,
                    "new_low": False,
                    "score": 0,
                    "signal": "FILTERED",
                    "status": "ABOVE_POSITION_LIMIT",
                    "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

            return None

        # ============================================================
        # SCORING (only stocks that passed the position filter reach here)
        # ============================================================

        discount = self.discount_percent(current, highest)
        bounce = self.bounce_percent(current, lowest)
        trend = self.trend(history)
        recovery = self.recovery(history)
        paused = self.paused(history)
        bullish = self.bullish(history)
        volume_up = self.volume_up(history)
        new_low = self.new_low(history)
        min_volume = self.min_avg_volume()

        score = self.calculate_score(
            position=position,
            filter_limit=filter_limit,
            discount=discount,
            avg_volume=avg_volume,
            min_volume=min_volume,
            bounce=bounce,
            trend=trend,
            recovery=recovery,
            paused=paused,
            bullish=bullish,
            volume_up=volume_up,
            new_low=new_low,
        )

        signal = self.generate_signal(score)

        status = self.market_status(trend, recovery, new_low)

        return {
            "symbol": symbol,
            "current_price": current,
            "high_7m": highest,
            "low_7m": lowest,
            "discount": discount,
            "position": position,
            "bounce": bounce,
            "avg_volume": avg_volume,
            "trend": trend,
            "near_low": position <= filter_limit,
            "recovery": recovery,
            "paused": paused,
            "bullish": bullish,
            "volume_up": volume_up,
            "new_low": new_low,
            "score": score,
            "signal": signal,
            "status": status,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # =====================================================
    # ANALYZE ALL SYMBOLS
    # =====================================================

    def analyze_all(self, progress_callback=None):

        print("\n" + "=" * 70)
        print("PSX ACCUMULATION SCAN STARTED")
        print("=" * 70)

        symbols = db.get_symbols()

        total = len(symbols)

        strong_buy = buy = watch_plus = watch = ignored = filtered_out = failed = 0

        db.clear_analysis()

        for index, item in enumerate(symbols, start=1):

            symbol = item["symbol"]

            try:

                result = self.analyze_symbol(symbol)

                if result is None:
                    filtered_out += 1
                else:

                    db.save_analysis(result)

                    signal = result["signal"]

                    if signal == "STRONG BUY":
                        strong_buy += 1
                    elif signal == "BUY":
                        buy += 1
                    elif signal == "WATCH+":
                        watch_plus += 1
                    elif signal == "WATCH":
                        watch += 1
                    else:
                        ignored += 1

                    # log signal transitions for notification diffing
                    previous = db.get_latest_signal(symbol)

                    if not previous or previous["signal"] != signal:

                        db.add_signal(
                            symbol,
                            signal,
                            result["score"],
                            result["current_price"],
                            result["updated"],
                        )

                    print(
                        f"[{index}/{total}] "
                        f"{symbol:<8}"
                        f"{signal:<12}"
                        f"Score={result['score']:>3}"
                    )

            except Exception as e:

                failed += 1

                print(f"[{index}/{total}] {symbol:<8} FAILED : {e}")

            if progress_callback:
                progress_callback(index, total, symbol)

        print("\n" + "=" * 70)
        print("SCAN COMPLETED")
        print("=" * 70)
        print(f"Total Symbols     : {total}")
        print(f"Passed Filter     : {total - filtered_out - failed}")
        print(f"Filtered Out (>{self.position_filter_limit():.0f}%) : {filtered_out}")
        print(f"STRONG BUY        : {strong_buy}")
        print(f"BUY               : {buy}")
        print(f"WATCH+            : {watch_plus}")
        print(f"WATCH             : {watch}")
        print(f"IGNORE            : {ignored}")
        print(f"Failed            : {failed}")
        print("=" * 70)

        return db.load_watchlist()


# =====================================================
# Global Analyzer Object
# =====================================================

analyzer = Analyzer()


if __name__ == "__main__":

    analyzer.analyze_all()
