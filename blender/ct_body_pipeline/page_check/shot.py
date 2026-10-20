import browser
import asyncio, sys, os
from playwright.async_api import async_playwright
url, out, wait = sys.argv[1], sys.argv[2], float(sys.argv[3])
async def main():
    async with async_playwright() as p:
        b = await browser.launch(p)
        pg = await b.new_page(viewport={'width':800,'height':956})
        msgs=[]; pg.on('console', lambda m: msgs.append(m.text)); pg.on('pageerror', lambda e: msgs.append('ERR '+str(e)))
        await pg.goto(url)
        await pg.wait_for_function('window.specimenDebug || document.body.dataset.ready || document.body.dataset.error', timeout=240000)
        if os.environ.get('PAGE_JS'): await pg.evaluate(os.environ['PAGE_JS'])   # 試しの設定（例: 臓器の吸光度）
        await pg.wait_for_timeout(wait*1000)
        try:
            await pg.get_by_text('閉じる').click(timeout=5000)
        except Exception as e: print('noclose')
        await pg.add_style_tag(content='#tune,#tune-open,#ch-tune,#ch-tune-open,.controls,#controls,[class*=control],.home-link{visibility:hidden!important}')
        await pg.wait_for_timeout(wait*1000)
        info = await pg.evaluate('({J: window.specimenDebug?.specimen.jarScale, size: window.specimenDebug?.specimen.size})')
        await pg.screenshot(path=out, timeout=400000)
        print(info, msgs[-10:])
        await b.close()
asyncio.run(main())
