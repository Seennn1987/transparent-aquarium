import browser
"""標本ページを、glb の座標の点に寄って撮る。  python zoom.py <URL> <出力.png> <x,y,z> <向き dx,dy,dz> <上 ux,uy,uz> <距離（ページ既定の何倍）>
向きは中心からカメラへの向き（views.py と同じ。背 −X、腹 +X、頭 −Y、左 +Z）。"""
import asyncio, sys
from playwright.async_api import async_playwright
url, out = sys.argv[1], sys.argv[2]
c, d, up = [[float(v) for v in a.split(',')] for a in sys.argv[3:6]]; k = float(sys.argv[6])
JS = '''([c, d, up, k]) => { const P = window.chameleonPage, cam = P.camera, V = cam.position.constructor;
  const dist = cam.position.distanceTo(P.orbit.target || new V(...c)) * k; const t = new V(...c);
  cam.up.set(...up); cam.position.copy(t).addScaledVector(new V(...d).normalize(), dist); cam.lookAt(t); cam.updateMatrixWorld(true); }'''
async def main():
    async with async_playwright() as p:
        b = await browser.launch(p); pg = await b.new_page(viewport={'width': 800, 'height': 956})
        await pg.goto(url); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error', timeout=300000)
        await pg.add_style_tag(content='#status,.home-link{visibility:hidden!important}')
        await pg.evaluate(JS, [c, d, up, k]); await pg.wait_for_timeout(3000); await pg.screenshot(path=out); await b.close()
asyncio.run(main())
