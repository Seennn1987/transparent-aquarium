#!/bin/sh
# Stop the desktop pet. Leaves the copy in ~/Applications in place.
set -eu

existing=$(ps -ax -o pid=,command= | awk '/Contents\/MacOS\/Desktop Pet/ && !/awk/ { print $1 }')
if [ -n "$existing" ]; then
	kill $existing 2>/dev/null || true
	echo "終了しました。"
else
	echo "動いていません。"
fi
