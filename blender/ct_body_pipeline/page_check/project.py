import browser
"""views.py の 4 方向と ?view=photo06 のカメラで、glb の座標（モデルの中、展示の姿勢）の点を画面の画素（800×956 の左上から）へ写す。

  python project.py <URL> <点.json> <出力.json>     点.json は {名前: [x, y, z]}
"""
import asyncio, json, sys
from playwright.async_api import async_playwright
from views import VIEWS, SET

url, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
P = json.load(open(src))


async def main():
    async with async_playwright() as p:
        b = await browser.launch(p)
        pg = await b.new_page(viewport={'width': 800, 'height': 956})
        await pg.goto(url); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error', timeout=300000)
        res = {}
        for name, (d, up) in VIEWS.items():
            await pg.evaluate(SET, [d, up])
            res[name] = await pg.evaluate(PROJ, P)
        # 写真 06 の向き（?view=photo06、ページの既定のカメラ）
        await pg.goto(url + ('&' if '?' in url else '?') + 'view=photo06'); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error', timeout=300000)
        res['photo06'] = await pg.evaluate(PROJ, P)
        json.dump(res, open(out, 'w'), indent=1); print(res); await b.close()
PROJ = '''(P) => { const c = window.chameleonPage.camera, V = c.position.constructor, o = {};
              c.updateMatrixWorld(true);
              for (const [k, p] of Object.entries(P)) { const v = new V(...p).applyMatrix4(window.chameleonPage.model.matrixWorld).project(c); o[k] = [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; }
              return o; }'''
asyncio.run(main())
