[app]
title = Ticofit
package.name = ticofit
package.domain = org.ticofit
source.dir = .
source.include_exts = py,png,jpg,jpeg,gif,kv,atlas,json,txt,mp3,wav,ogg
source.include_patterns = assets/*,images/*,datos_salud/*,*.json
version = 0.1
requirements = python3,kivy==2.2.1,kivymd,pillow,plyer,requests,certifi,urllib3,idna,charset-normalizer,mapview
garden_requirements = mapview
presplash.filename = %(source.dir)s/data/presplash.png
icon.filename = %(source.dir)s/data/icon.png
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[buildozer:android]
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,ACCESS_BACKGROUND_LOCATION,VIBRATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.arch = armeabi-v7a
android.allow_backup = True
android.gradle_dependencies = com.google.android.gms:play-services-location:21.0.1, com.google.android.gms:play-services-maps:18.2.0
p4a.branch = master
android.logcat_filters = *:S python:D
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,VIBRATE,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
