[app]
title = GTALSIK AI
package.name = gtalsikai
package.domain = org.haadi
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,html
version = 1.0
requirements = python3,kivy,flask,flask-sqlalchemy,google-genai,google-auth,google-api-core,googleapis-common-protos,protobuf,requests,urllib3,chardet,idna,certifi,werkzeug,sqlalchemy,jinja2,itsdangerous,click,blinker,markupsafe,rsa,cachetools,pyasn1,pyasn1-modules
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 31
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True
android.skip_update = True
android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/25.2.9519653

[buildozer]
log_level = 2
warn_on_root = 0
