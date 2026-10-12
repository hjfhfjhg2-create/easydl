[app]
title = EasyDL
package.name = easydl
package.domain = org.easydl
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.2.0
requirements = python3,hostpython3,kivy==2.3.0,yt-dlp,certifi,openssl,android,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.ndk = 25b
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
