#! /usr/bin/env sh
set -e

nginx-debug -g "daemon off;" &
python3 app.py --ignore-docker