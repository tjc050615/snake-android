[app]
version = 0.1
title = Snake Android
package.name = snake
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,ttf,otf,wav,json
source.include_patterns = assets/fonts/*,src/**/*,main.py
source.exclude_dirs = tests,tools,docs,.venv,.data,.git,.kivyhome,__pycache__,.pytest_cache
source.exclude_patterns = docs/*,docs/evidence/*,tests/*,tools/*,*.md,requirements*.txt
requirements = python3,kivy==2.3.0,pyjnius,cython==0.29.33

# 版本锁定（不要用最新版）：
#   buildozer==1.5.0
#   python-for-android: pin 到 buildozer 1.5.0 兼容的 commit（见 docs/R4-PACKAGING.md）
#   Python 3.11（Kivy 2.3.0 支持 3.8~3.12）

orientation = landscape
fullscreen = 1
android.minapi = 23
android.api = 33
android.ndk = 25b
android.ndk_api = 23
android.permissions = VIBRATE
android.archs = arm64-v8a
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
