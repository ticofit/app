[app]
title = Ticofit
package.name = ticofit
package.domain = org.ticofit
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy

[buildozer]
log_level = 2
warn_on_root = 1

[buildozer:android]
api = 31
minapi = 21
ndk = 25b
android.accept_sdk_license = True
android.arch = armeabi-v7a
android.permissions = INTERNET
android.release = False
android.debug = True
