#!/bin/bash
# 1 回のコマンドの中でサーバを立てて、引数のコマンドを走らせる
cd "$(dirname "$0")/w" && python3 -m http.server 8099 >/dev/null 2>&1 &
SP=$!; sleep 1; cd "$(dirname "$0")"; "$@"; R=$?; kill $SP; exit $R
