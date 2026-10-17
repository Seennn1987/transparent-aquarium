#!/bin/bash
# 引数のコマンドを page_check のフォルダで走らせる。
# Mac: ページは共有の配信（cd 水槽 && npm start、ポート 8080）から読む。ここでは配信を立てない（止めない・ほかのポートを取らない）。
# クラウド: page_check/w/ に 水槽 の写しがあるときだけ、それを 8099 で配信してから走らせる（URL は http://127.0.0.1:8099/...）。
cd "$(dirname "$0")"
if [ -d w ] && [ -n "$PAGE_CHECK_CHROMIUM" ]; then
  (cd w && python3 -m http.server 8099 >/dev/null 2>&1) & SP=$!; sleep 1
  "$@"; R=$?; kill $SP; exit $R
fi
curl -s -o /dev/null http://127.0.0.1:8080/ || { echo "8080 の配信がありません。cd 水槽 && npm start を先に"; exit 1; }
"$@"
