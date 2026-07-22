"""
main.py
====================================================
PSX Smart Terminal — Mobile (Android)
Institutional Accumulation Scanner
====================================================

Screens:
    Dashboard  -- summary stats + Update/Analyze actions
    Watchlist  -- stocks that passed the position filter,
                  filterable by signal, searchable by symbol
    Settings   -- every scanner/app setting, editable in-app
                  (the mobile equivalent of hand-editing
                  config.py / a .env file)

Author : Ali Labs
"""

from __future__ import annotations

import threading
import json
from datetime import datetime

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox, MDSwitch
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.toolbar import MDTopAppBar

import config
from database import db
from market_data import market
from analyzer import analyzer
from settings_schema import grouped_schema

try:
    from plyer import notification as android_notification
except Exception:
    android_notification = None

Builder.load_file("main.kv")


SIGNAL_COLORS = {
    "STRONG BUY": (0.06, 0.45, 0.22, 1),
    "BUY": (0.14, 0.56, 0.14, 1),
    "WATCH+": (0.58, 0.5, 0.03, 1),
    "WATCH": (0.7, 0.5, 0.05, 1),
    "IGNORE": (0.24, 0.24, 0.24, 1),
}


# ============================================================
# REUSABLE THEMED WIDGETS (styled via main.kv)
# ============================================================

class StatCard(MDCard):
    def __init__(self, highlight=False, **kwargs):
        self.highlight = highlight
        super().__init__(**kwargs)


class SectionHeader(MDLabel):
    pass


class SettingRow(MDCard):
    pass


class HintLabel(MDLabel):
    pass


class StockRow(MDCard):

    def __init__(self, row, on_tap, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.md_bg_color = SIGNAL_COLORS.get(row["signal"], (0.2, 0.2, 0.2, 1))
        self.row_data = row
        self.on_tap = on_tap
        self.bind(on_touch_up=self._touch)

        top = MDBoxLayout(size_hint_y=None, height=dp(26))
        top.add_widget(MDLabel(
            text=f"[b]{row['symbol']}[/b]", markup=True,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
        ))
        top.add_widget(MDLabel(
            text=row["signal"], halign="right", bold=True,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
        ))
        self.add_widget(top)

        mid = MDBoxLayout(size_hint_y=None, height=dp(22))
        mid.add_widget(MDLabel(
            text=f"Price {row['current_price']:.2f}   Pos {row['position']:.1f}%   Score {row['score']}",
            font_style="Caption",
            theme_text_color="Custom", text_color=(0.92, 0.92, 0.92, 1),
        ))
        self.add_widget(mid)

        bot = MDBoxLayout(size_hint_y=None, height=dp(20))
        bot.add_widget(MDLabel(
            text=f"Discount {row['discount']:.1f}%   Bounce {row.get('bounce', 0):.1f}%   {row['status']}",
            font_style="Caption",
            theme_text_color="Custom", text_color=(0.8, 0.8, 0.8, 1),
        ))
        self.add_widget(bot)

    def _touch(self, widget, touch):
        if self.collide_point(*touch.pos):
            self.on_tap(self.row_data)
            return True
        return False


# ============================================================
# DASHBOARD SCREEN
# ============================================================

class DashboardTab(MDBottomNavigationItem):

    def __init__(self, app, **kwargs):
        super().__init__(name="dashboard", text="Dashboard", icon="view-dashboard", **kwargs)
        self.app = app

        root = MDBoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        self.stats_grid = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.stats_grid.bind(minimum_height=self.stats_grid.setter("height"))
        self.stat_labels = {}

        stat_defs = [
            ("symbols", "Total Symbols", False),
            ("history", "History Records", False),
            ("passed_filter", "Passing Position Filter", True),
            ("strong_buy", "STRONG BUY", True),
            ("buy", "BUY", False),
            ("watch", "WATCH / WATCH+", False),
            ("db_last_updated", "Database Last Updated", False),
            ("analysis_last_updated", "Analysis Last Updated", False),
        ]

        for key, title, highlight in stat_defs:
            card = StatCard(highlight=highlight, orientation="horizontal")
            card.add_widget(MDLabel(text=title))
            value_lbl = MDLabel(text="-", halign="right", bold=True)
            self.stat_labels[key] = value_lbl
            card.add_widget(value_lbl)
            self.stats_grid.add_widget(card)

        scroll = ScrollView()
        scroll.add_widget(self.stats_grid)
        root.add_widget(scroll)

        self.progress = MDProgressBar(value=0, size_hint_y=None, height=dp(6))
        root.add_widget(self.progress)

        self.status_label = MDLabel(text="Ready", size_hint_y=None, height=dp(24), font_style="Caption")
        root.add_widget(self.status_label)

        btn_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.btn_update = MDRaisedButton(text="Update Database", on_release=lambda *_: self.app.thread_update())
        self.btn_analyze = MDRaisedButton(text="Analyze Market", on_release=lambda *_: self.app.thread_analyze())
        btn_row.add_widget(self.btn_update)
        btn_row.add_widget(self.btn_analyze)
        root.add_widget(btn_row)

        self.add_widget(root)

    def refresh(self):
        stats = db.dashboard_stats()
        self.stat_labels["symbols"].text = str(stats["symbols"])
        self.stat_labels["history"].text = f'{stats["history"]:,}'
        self.stat_labels["passed_filter"].text = str(stats["passed_filter"])
        self.stat_labels["strong_buy"].text = str(stats["strong_buy"])
        self.stat_labels["buy"].text = str(stats["buy"])
        self.stat_labels["watch"].text = str(stats["watch"])
        self.stat_labels["db_last_updated"].text = stats["db_last_updated"] or "-"
        self.stat_labels["analysis_last_updated"].text = stats["analysis_last_updated"] or "-"

    def set_progress(self, current, total, text):
        self.progress.value = (current / total) * 100 if total else 0
        self.status_label.text = text


# ============================================================
# WATCHLIST SCREEN
# ============================================================

class WatchlistTab(MDBottomNavigationItem):

    def __init__(self, app, **kwargs):
        super().__init__(name="watchlist", text="Watchlist", icon="chart-line", **kwargs)
        self.app = app

        root = MDBoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))

        self.search_field = MDTextField(
            hint_text="Search symbol...",
            size_hint_y=None, height=dp(48),
        )
        self.search_field.bind(text=lambda *_: self.refresh())
        root.add_widget(self.search_field)

        filter_row = MDBoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        self.filters = {}
        for signal in ["STRONG BUY", "BUY", "WATCH+", "WATCH"]:
            box = MDBoxLayout(size_hint_x=None, width=dp(88))
            chk = MDCheckbox(active=True, size_hint=(None, None), size=(dp(24), dp(24)))
            chk.bind(active=lambda *_: self.refresh())
            self.filters[signal] = chk
            box.add_widget(chk)
            box.add_widget(MDLabel(text=signal, font_style="Caption"))
            filter_row.add_widget(box)
        root.add_widget(filter_row)

        self.list_container = MDBoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.list_container.bind(minimum_height=self.list_container.setter("height"))

        scroll = ScrollView()
        scroll.add_widget(self.list_container)
        root.add_widget(scroll)

        self.add_widget(root)

    def refresh(self):
        self.list_container.clear_widgets()

        watchlist = db.load_watchlist()

        if watchlist.empty:
            self.list_container.add_widget(MDLabel(
                text="No stocks in the watchlist yet.\nRun Update Database then Analyze Market.",
                halign="center", size_hint_y=None, height=dp(80),
            ))
            return

        query = self.search_field.text.strip().upper()
        shown = 0

        for _, row in watchlist.iterrows():
            row = dict(row)
            if not self.filters[row["signal"]].active:
                continue
            if query and query not in row["symbol"].upper():
                continue
            self.list_container.add_widget(StockRow(row, self.app.show_stock_detail))
            shown += 1

        if shown == 0:
            self.list_container.add_widget(MDLabel(
                text="No matches for the current filters/search.",
                halign="center", size_hint_y=None, height=dp(60),
            ))


# ============================================================
# SETTINGS SCREEN -- schema-driven, in-app equivalent of
# hand-editing config.py / a .env file
# ============================================================

class SettingsTab(MDBottomNavigationItem):

    def __init__(self, app, **kwargs):
        super().__init__(name="settings", text="Settings", icon="cog", **kwargs)
        self.app = app
        self.widgets = {}  # key -> MDTextField or MDSwitch

        outer = MDBoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))

        content = MDBoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None, padding=dp(4))
        content.bind(minimum_height=content.setter("height"))

        for group_name, items in grouped_schema():
            content.add_widget(SectionHeader(text=group_name))

            for item in items:
                row = SettingRow(orientation="vertical")

                header = MDBoxLayout(size_hint_y=None, height=dp(40))
                header.add_widget(MDLabel(text=item["label"]))

                current = db.get_setting(item["key"])

                if item["type"] == "bool":
                    current_val = (current != "0") if current is not None else item["default"]
                    widget = MDSwitch(active=bool(current_val))
                    header.add_widget(widget)
                    row.height = dp(48) if not item["hint"] else dp(68)
                else:
                    widget = MDTextField(
                        text=str(current) if current is not None else str(item["default"]),
                        input_filter=item["type"],
                        size_hint_x=0.4,
                    )
                    header.add_widget(widget)
                    row.height = dp(70) if item["hint"] else dp(50)

                row.add_widget(header)

                if item["hint"]:
                    row.add_widget(HintLabel(text=item["hint"]))

                self.widgets[item["key"]] = (widget, item)
                content.add_widget(row)

        action_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        action_row.add_widget(MDRaisedButton(text="Save All Settings", on_release=self.save_all))
        action_row.add_widget(MDFlatButton(text="Reset to Defaults", on_release=self.reset_defaults))
        content.add_widget(action_row)

        export_header = SectionHeader(text="Export Watchlist")
        content.add_widget(export_header)
        export_row = MDBoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        export_row.add_widget(MDRaisedButton(text="Excel", on_release=lambda *_: self.app.export("xlsx")))
        export_row.add_widget(MDRaisedButton(text="CSV", on_release=lambda *_: self.app.export("csv")))
        export_row.add_widget(MDRaisedButton(text="JSON", on_release=lambda *_: self.app.export("json")))
        content.add_widget(export_row)

        self.status = MDLabel(text="", size_hint_y=None, height=dp(24), font_style="Caption")
        content.add_widget(self.status)

        scroll = ScrollView()
        scroll.add_widget(content)
        outer.add_widget(scroll)
        self.add_widget(outer)

    def save_all(self, *_):
        for key, (widget, item) in self.widgets.items():
            if item["type"] == "bool":
                db.set_setting(key, "1" if widget.active else "0")
            else:
                text = (widget.text or "").strip()
                if text == "":
                    text = str(item["default"])
                db.set_setting(key, text)
        self.status.text = "All settings saved."

    def reset_defaults(self, *_):
        for key, (widget, item) in self.widgets.items():
            db.set_setting(key, "1" if item["default"] is True else "0" if item["default"] is False else str(item["default"]))
            if item["type"] == "bool":
                widget.active = bool(item["default"])
            else:
                widget.text = str(item["default"])
        self.status.text = "Reset to defaults."


# ============================================================
# APP
# ============================================================

class PSXApp(MDApp):

    def build(self):
        self.theme_cls.theme_style = "Dark" if db.get_setting("dark_mode") != "0" else "Light"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Amber"
        self.title = "PSX Smart Terminal"

        self.running = False
        self.last_notified = {}

        screen = MDScreen()
        layout = BoxLayout(orientation="vertical")

        self.toolbar = MDTopAppBar(
            title="PSX Smart Terminal",
            elevation=4,
            right_action_items=[
                ["refresh", lambda *_: self.thread_update()],
                ["magnify-scan", lambda *_: self.thread_analyze()],
            ],
        )
        layout.add_widget(self.toolbar)

        self.nav = MDBottomNavigation()
        self.dashboard_tab = DashboardTab(self)
        self.watchlist_tab = WatchlistTab(self)
        self.settings_tab = SettingsTab(self)
        self.nav.add_widget(self.dashboard_tab)
        self.nav.add_widget(self.watchlist_tab)
        self.nav.add_widget(self.settings_tab)

        layout.add_widget(self.nav)
        screen.add_widget(layout)

        Clock.schedule_once(lambda dt: self.refresh_all(), 0.3)
        Clock.schedule_interval(self.auto_refresh_tick, 1)

        return screen

    # --------------------------------------------------
    def refresh_all(self):
        self.dashboard_tab.refresh()
        self.watchlist_tab.refresh()

    # --------------------------------------------------
    # UPDATE DATABASE (background thread)
    # --------------------------------------------------

    def thread_update(self):
        if self.running:
            return
        threading.Thread(target=self._update_database, daemon=True).start()

    def _update_database(self):
        self.running = True
        Clock.schedule_once(lambda dt: self.dashboard_tab.set_progress(0, 1, "Downloading PSX data..."))

        def progress_cb(current, total, symbol, status=""):
            Clock.schedule_once(lambda dt: self.dashboard_tab.set_progress(current, total, f"{symbol} {status}"))

        market.progress = progress_cb

        try:
            market.update_database()
        except Exception as e:
            print("update_database error:", e)

        Clock.schedule_once(lambda dt: self.dashboard_tab.set_progress(1, 1, "Database Updated"))
        self.running = False
        Clock.schedule_once(lambda dt: self.refresh_all())

        if db.get_setting("auto_analysis") != "0":
            self.thread_analyze()

    # --------------------------------------------------
    # ANALYZE (background thread)
    # --------------------------------------------------

    def thread_analyze(self):
        if self.running:
            return
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        self.running = True

        def progress_cb(current, total, symbol):
            Clock.schedule_once(lambda dt: self.dashboard_tab.set_progress(current, total, f"Analyzing {symbol} ({current}/{total})"))

        try:
            analyzer.analyze_all(progress_callback=progress_cb)
        except Exception as e:
            print("analyze_all error:", e)

        Clock.schedule_once(lambda dt: self.dashboard_tab.set_progress(1, 1, "Analysis Complete"))
        self.running = False
        Clock.schedule_once(lambda dt: self.refresh_all())
        Clock.schedule_once(lambda dt: self.check_notifications())

    # --------------------------------------------------
    # NOTIFICATIONS -- only WATCH->BUY and BUY->STRONG BUY
    # --------------------------------------------------

    def check_notifications(self):
        if db.get_setting("notifications_on") == "0":
            return
        if android_notification is None:
            return

        watchlist = db.load_watchlist()
        if watchlist.empty:
            return

        upgrade_pairs = {("WATCH", "BUY"), ("WATCH+", "BUY"), ("BUY", "STRONG BUY")}

        for _, row in watchlist.iterrows():
            symbol = row["symbol"]
            signal = row["signal"]
            previous = self.last_notified.get(symbol)
            self.last_notified[symbol] = signal

            if previous and (previous, signal) in upgrade_pairs:
                try:
                    android_notification.notify(
                        title=f"{symbol} upgraded to {signal}",
                        message=f"Score: {row['score']}  Price: {row['current_price']:.2f}",
                        timeout=8,
                    )
                except Exception as e:
                    print("notify error:", e)

    # --------------------------------------------------
    def auto_refresh_tick(self, dt):
        interval = int(db.get_setting("auto_interval") or config.REFRESH_INTERVAL)
        now = datetime.now().timestamp()
        last = getattr(self, "_last_auto", 0)
        if now - last >= interval and not self.running:
            self._last_auto = now
            self.thread_update()

    # --------------------------------------------------
    def show_stock_detail(self, row):
        info = db.get_symbol_info(row["symbol"])

        text = (
            f"[b]{row['symbol']}[/b]  {info.get('company','')}\n"
            f"Sector: {info.get('sector','')}\n\n"
            f"Price: {row['current_price']:.2f}\n"
            f"7M High: {row['high_7m']:.2f}   7M Low: {row['low_7m']:.2f}\n"
            f"Discount: {row['discount']:.2f}%   Position: {row['position']:.2f}%\n"
            f"Bounce: {row.get('bounce', 0):.2f}%\n"
            f"Trend: {row['trend']}   Status: {row['status']}\n"
            f"Score: {row['score']}   Signal: {row['signal']}\n"
            f"Updated: {row['updated']}"
        )

        dialog = MDDialog(
            title=row["symbol"],
            text=text,
            buttons=[MDFlatButton(text="CLOSE", on_release=lambda *_: dialog.dismiss())],
        )
        dialog.open()

    # --------------------------------------------------
    def export(self, fmt):
        watchlist = db.load_watchlist()
        if watchlist.empty:
            self.settings_tab.status.text = "Nothing to export."
            return

        out_dir = self.user_data_dir
        filename = f"{out_dir}/PSX_Watchlist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}"

        try:
            if fmt == "xlsx":
                watchlist.to_excel(filename, index=False)
            elif fmt == "csv":
                watchlist.to_csv(filename, index=False)
            elif fmt == "json":
                with open(filename, "w") as f:
                    json.dump(watchlist.to_dict(orient="records"), f, indent=2, default=str)
            self.settings_tab.status.text = f"Exported to {filename}"
        except Exception as e:
            self.settings_tab.status.text = f"Export failed: {e}"


if __name__ == "__main__":
    PSXApp().run()
