[app]
title = Inventory Manager
package.name = inventorymanager
package.domain = org.peterbwalya
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
version = 1.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
android.permissions = READ_MEDIA_IMAGES,READ_MEDIA_VIDEO
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.allow_backup = True
log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
