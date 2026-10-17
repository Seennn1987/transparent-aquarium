"""page_check の道具が使うブラウザの起動。

Mac（既定）: Playwright で、`tools/record-specimen/record.mjs` と同じ Chrome（環境変数 CHROME_CHANNEL、既定 "chrome"）を開く。
クラウドの Chromium（SwiftShader）で撮るときは、PAGE_CHECK_CHROMIUM にその実行ファイルのパスを入れる（例 /opt/pw-browsers/chromium）。
ページは共有の配信（`cd 水槽 && npm start`、http://127.0.0.1:8080/）から読む。
"""
import os

SWIFTSHADER = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-proxy-server']
BASE = os.environ.get('PAGE_CHECK_BASE', 'http://127.0.0.1:8080')


async def launch(p):
    exe = os.environ.get('PAGE_CHECK_CHROMIUM')
    if exe:
        return await p.chromium.launch(executable_path=exe, args=SWIFTSHADER)
    return await p.chromium.launch(channel=os.environ.get('CHROME_CHANNEL', 'chrome'), args=['--ignore-gpu-blocklist', '--no-proxy-server'])
