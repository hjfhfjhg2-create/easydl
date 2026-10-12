
[app]

title = EasyDL
package.name = easydl
package.domain = org.easydl

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 1.0.0

requirements = python3,kivy,requests,yt-dlp

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.api = 35
android.minapi = 23
android.ndk = 27c

android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
