#!/bin/sh
# Compile the desktop pet, install it in ~/Applications, and start it.
# It does not register a login item. Quit from the menu bar, or run stop.sh.
set -eu

here=$(cd "$(dirname "$0")" && pwd)
app="$HOME/Applications/Desktop Pet.app"

if ! command -v swiftc >/dev/null; then
	echo "swiftc がありません。Xcode コマンドラインツールを入れてください: xcode-select --install" >&2
	exit 1
fi

build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
swiftc -O -target "$(uname -m)-apple-macos13.0" -o "$build/Desktop Pet" \
	"$here/ChameleonPose.swift" "$here/Pet.swift" -framework Cocoa

existing=$(ps -ax -o pid=,command= | awk '/Contents\/MacOS\/Desktop Pet/ && !/awk/ { print $1 }')
if [ -n "$existing" ]; then
	kill $existing 2>/dev/null || true
	sleep 0.3
fi

rm -rf "$app"
mkdir -p "$app/Contents/MacOS"
cp "$build/Desktop Pet" "$app/Contents/MacOS/Desktop Pet"
cp "$here/Info.plist" "$app/Contents/Info.plist"
codesign --force --sign - "$app" >/dev/null 2>&1 || true

open "$app"
echo "起動しました。メニューバーのカメレオンから終了できます。"
echo "ログ: /tmp/desktop-pet.log"
