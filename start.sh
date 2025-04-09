#! /usr/bin/env sh
set -e

nginx -g "daemon off;" &
python3 run.py