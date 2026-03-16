#!/usr/bin/env bash
DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
cd "$DIR"
exec venv/bin/python3 main.py
