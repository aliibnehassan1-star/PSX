# PSX Smart Terminal — Mobile

An offline-first Android accumulation scanner for the Pakistan Stock
Exchange. Downloads history via `requests`/`BeautifulSoup`, stores it in
SQLite, and scores only the stocks trading within the lowest 30% of their
7-month range.

## What changed from the desktop version

- **`analyzer.py`** — rewritten around a primary Position % filter.
  Stocks trading above the filter limit (default 30%, editable in
  Settings) are skipped before scoring, not just penalized. Scoring is
  now 0–100 across Position (scaled, closer-to-low = more points),
  Discount, Recovery, Trend, Volume, and Bullish Candle, with penalties
  for new lows, downtrends, thin volume, and weak bounces.
- **`database.py`** — added a `bounce` column and a `dashboard_stats()`
  query; `load_watchlist()` now strictly returns WATCH/WATCH+/BUY/STRONG
  BUY only.
- **`config.py`** — database/log paths now resolve to writable Android
  app storage instead of the (read-only) source folder; added the new
  filter/threshold constants.
- **`gui.py` → `main.py` + `main.kv`** — the CustomTkinter desktop GUI is
  replaced entirely with a KivyMD app styled via `main.kv` (rounded
  cards, elevation, a themed toolbar with quick-action icons): Dashboard
  (stats + Update/Analyze), Watchlist (filterable + searchable, tap a
  stock for details), and Settings.
- **`settings_schema.py` (new)** — every scanner/app knob (position
  filter %, min volume, min bounce %, all 4 signal score cutoffs,
  months of history, request timeout, auto-update interval,
  notifications, auto-analysis, dark mode, store-filtered) is declared
  once here and rendered as an editable field in the Settings tab —
  this is the in-app equivalent of hand-editing `config.py` or a
  `.env` file, with a "Reset to Defaults" button. `analyzer.py` and
  `market_data.py` read these live from the settings table, so changes
  take effect on the next Update/Analyze run with no rebuild.
- `export_database.py`'s Excel export is now Excel/CSV/JSON from the
  Settings tab.
- `market_data.py` is carried over essentially unchanged — it was
  already pure `requests`/`BeautifulSoup`/`pandas`, so it runs on
  Android as-is.

## Building the APK

I can't compile the APK myself (no internet/Android SDK access in my
sandbox), but this repo is CI-ready — you don't need Buildozer installed
locally:

1. Push this folder to a GitHub repo.
2. GitHub → **Actions** tab → **Build Android APK** → **Run workflow**.
3. Wait ~20–40 minutes (first run downloads the Android SDK/NDK).
4. Download the `psx-smart-terminal-apk` artifact from the finished run
   — that's your installable `.apk`.

To build locally instead (Linux/WSL only):
```bash
pip install buildozer cython==0.29.36
buildozer android debug
# APK lands in bin/
```

## Known risks worth knowing about before you rely on this

- **pandas on Android** is the single biggest risk in this build. It
  needs a compiled numpy wheel for Android's architecture; if the
  Buildozer/python-for-android recipe fails for your `android.api`/
  `android.ndk` combo in `buildozer.spec`, that's the first place to
  look (try dropping `android.api` or pinning an older pandas).
- First install requires **internet** to download symbols/history;
  after that the app is fully offline as specified.
- `android.minapi = 24` and `android.api = 34` in `buildozer.spec` are
  reasonable defaults — adjust if your target devices need otherwise.

## Testing done so far

I validated the new `analyzer.py` logic (not the Android build itself,
since I can't run that here) against synthetic data: confirmed a stock
sitting at 16% of its range passes the filter and scores correctly
(WATCH+, score 63), and confirmed a stock near its high is filtered out
before scoring, exactly as specified.
