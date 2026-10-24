"""
メンダコの標本ページ（水槽/scenes/specimen/mendako.html）を、手元の Chrome で向きごとに撮る。先に `cd 水槽 && npm start`。

  .venv/bin/python -I blender/mendako/shoot_mendako.py <出力フォルダ> <名前> [向き,向き,...] [追加のクエリ]

  向きの既定: display,front,oblique,top,oral。出力は <出力フォルダ>/<名前>_<向き>.png
環境変数: SIZE（既定 1400x1050）、SCALE（画素の倍率、既定 1）
"""

import asyncio
import os
import sys

from playwright.async_api import async_playwright

BASE = os.environ.get("BASE", "http://127.0.0.1:8080/scenes/specimen/mendako.html")


async def main(out, name, views, extra):
    w, h = map(int, os.environ.get("SIZE", "1400x1050").split("x"))
    scale = float(os.environ.get("SCALE", 1))
    os.makedirs(out, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", args=["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--hide-scrollbars"])
        pg = await b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        for v in views:
            await pg.goto(f"{BASE}?view={v}{('&' + extra) if extra else ''}")
            await pg.wait_for_selector("body[data-ready], body[data-error]", timeout=60000)
            await pg.wait_for_timeout(1500)
            st = await pg.text_content("#status")
            path = os.path.join(out, f"{name}_{v}.png")
            await pg.locator("#scene").screenshot(path=path)
            print(path, st)
        if errors:
            print("エラー:", errors[:5])
        await b.close()


if __name__ == "__main__":
    out, name = sys.argv[1], sys.argv[2]
    views = (sys.argv[3] if len(sys.argv) > 3 else "display,front,oblique,top,oral").split(",")
    extra = sys.argv[4] if len(sys.argv) > 4 else ""
    asyncio.run(main(out, name, views, extra))
