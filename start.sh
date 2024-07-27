#! /usr/bin/env sh
set -e

nginx -g "daemon off;" &
python3 app.py