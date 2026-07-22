[app]
title = PSX Smart Terminal
package.name = psxsmartterminal
package.domain = com.alilabs

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,db,xlsx,csv,txt,ttf,ico
source.include_patterns = assets/*

version = 1.0.0

# Python dependencies
requirements = python3,kivy==2.3.0,kivymd==1.2.0,plyer,requests,beautifulsoup4,pandas,numpy,openpyxl,certifi

icon.filename = %(source.dir)s/assets/icon.ico

orientation = portrait
fullscreen = 0

# Android configuration
android.api = 34
android.minapi = 24
android.sdk = 34
android.ndk = 26b
android.build_tools = 34.0.0

android.archs = arm64-v8a,armeabi-v7a

android.permissions = INTERNET,POST_NOTIFICATIONS,WAKE_LOCK

android.allow_backup = True

android.accept_sdk_license = True

android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1
