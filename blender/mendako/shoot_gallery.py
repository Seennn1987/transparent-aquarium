"""
ギャラリー（水槽/scenes/specimen/index.html）を、手元の Chrome で撮る。先に `cd 水槽 && npm start` で配信しておく。

  .venv/bin/python -I blender/mendako/shoot_gallery.py <出力フォルダ> [名前=クエリ ...]

  例: shoot_gallery.py docs/mendako jar_2x="tune=0" dish_2x="specimen=hammerhead&tune=0"
環境変数: SIZE（既定 1400x1050）、SCALE（画素の倍率、既定 2）、WAIT（読み込みを待つ ms、既定 14000）
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8080/scenes/specimen/index.html")


async def main(out, shots):
    w, h = map(int, os.environ.get("SIZE", "1400x1050").split("x"))
    scale = float(os.environ.get("SCALE", 2))
    wait = int(os.environ.get("WAIT", 14000))
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", args=["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--hide-scrollbars"])
        pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        for name, query in shots:
            await pg.goto(f"{BASE}?{query}")
            await pg.wait_for_timeout(wait)
            path = os.path.join(out, f"{name}.png")
            await pg.screenshot(path=path)
            print(path)
        await b.close()


if __name__ == "__main__":
    out = sys.argv[1]
    shots = [a.split("=", 1) for a in sys.argv[2:]] or [["gallery", "tune=0"]]
    asyncio.run(main(out, shots))
