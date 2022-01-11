#!/usr/bin/env bash
tox -e mypy | grep -E "($(git diff main --stat | head -n -1 | grep -E -o '/[^/]*\|' | cut -f 1 -d ' ' | cut -f 2 -d '/' | sed ':a;N;$!ba;s/\n/|/g'))"
