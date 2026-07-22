[app]
title = PSX Smart Terminal
package.name = psxsmartterminal
package.domain = com.alilabs

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
source.include_patterns = assets/*

version = 1.0.0

# Core deps: kivy/kivymd for UI, plyer for notifications,
# requests+bs4+pandas for the backend (unchanged from desktop),
# openpyxl for Excel export.
requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer,requests,beautifulsoup4,pandas,openpyxl,sqlite3,certifi

icon.filename = %(source.dir)s/assets/icon.ico

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,POST_NOTIFICATIONS,WAKE_LOCK

# Reasonable modern defaults; raise minapi if pandas wheel
# availability forces your hand during the build.
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
