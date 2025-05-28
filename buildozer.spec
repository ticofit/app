[app]
title = Ticofit
package.name = ticofit
package.domain = org.ticofit
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,po,json
version = 0.1
requirements = python3,kivy==2.2.1,pillow,plyer,kivymd
osx.python_version = 3
osx.kivy_version = 2.2.1

[buildozer]
log_level = 2
warn_on_root = 1

[buildozer:android]
api = 31
minapi = 21
ndk = 25b
android.accept_sdk_license = True
android.arch = arm64-v8a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.gradle_dependencies = 
android.release = False
android.debug = True
