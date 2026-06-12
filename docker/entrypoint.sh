#!/bin/sh
# Starts the bundled LibreTranslate (only in the ":*-translate" image) on loopback,
# then runs the app. Language models persist under /data/translate.
set -e

if [ "${BUNDLE_TRANSLATE:-false}" = "true" ]; then
  : "${LT_LOAD_ONLY:=en,es,fr,de,it,pt}"
  echo "Starting bundled LibreTranslate (languages: ${LT_LOAD_ONLY})…"
  HOME=/data/translate libretranslate --host 127.0.0.1 --port 5000 \
    --load-only "${LT_LOAD_ONLY}" &
  : "${LIBRETRANSLATE_URL:=http://127.0.0.1:5000}"
  export LIBRETRANSLATE_URL
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
