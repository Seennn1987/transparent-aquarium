import browser
"""標本ページを、横（左）・背中・腹・正面（頭の先から）の 4 方向で撮る。

  python views.py <URL> <接頭辞>    → <接頭辞>_side.png, _dorsal.png, _ventral.png, _front.png

ページの glb の座標（展示の姿勢、chameleon.html の既定の向き）: 背が −X、腹が +X、頭が −Y、左が +Z。
カメラはページの既定と同じ距離で、骨の外接箱の中心を見る。背中と腹は頭を画面の上にする（X 線の背腹像と同じ向き）。
"""
import asyncio, sys
from playwright.async_api import async_playwright

VIEWS = {  # 名前: (中心からカメラへの向き, 画面の上)
    'side': ([0, 0, 1], [0, 1, 0]),
    'dorsal': ([-1, 0, 0], [0, -1, 0]),
    'ventral': ([1, 0, 0], [0, -1, 0]),
    'front': ([0, -1, 0], [-1, 0, 0]),
}
SET = '''([d, up]) => {
  const P = window.chameleonPage, c = P.camera, V = c.position.constructor;
  if (!P._centre) {
    const w = new V(), lo = new V(Infinity, Infinity, Infinity), hi = new V(-Infinity, -Infinity, -Infinity);
    P.model.updateMatrixWorld(true);
    P.model.traverse((o) => { if (o.isBone) { o.getWorldPosition(w); lo.min(w); hi.max(w); } });
    P._centre = lo.clone().add(hi).multiplyScalar(0.5);
    P._dist = c.position.distanceTo(P._centre);
  }
  c.up.set(...up);
  c.position.copy(P._centre).addScaledVector(new V(...d), P._dist);
  c.lookAt(P._centre);
  c.updateMatrixWorld(true);
  return [P._centre.toArray(), P._dist];
}'''
url, pre = sys.argv[1], sys.argv[2]


async def main():
    async with async_playwright() as p:
        b = await browser.launch(p)
        pg = await b.new_page(viewport={'width': 800, 'height': 956}); msgs = []; pg.on('pageerror', lambda e: msgs.append(str(e)))
        await pg.goto(url); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error', timeout=300000)
        await pg.add_style_tag(content='#status,.home-link{visibility:hidden!important}')
        await pg.wait_for_timeout(3000)
        for name, (d, up) in VIEWS.items():
            info = await pg.evaluate(SET, [d, up])
            await pg.wait_for_timeout(2500)
            await pg.screenshot(path=f'{pre}_{name}.png')
        print(info, msgs); await b.close()
asyncio.run(main())
