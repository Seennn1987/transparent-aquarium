import browser
import asyncio, sys
from playwright.async_api import async_playwright
url,pre=sys.argv[1],sys.argv[2]
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p)
        pg=await b.new_page(viewport={'width':800,'height':956}); msgs=[]; pg.on('pageerror',lambda e: msgs.append(str(e)))
        await pg.goto(url); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error',timeout=300000)
        await pg.evaluate("(()=>{const L=window.chameleonPage.look; for(const k of ['skin','film','organs','viscera']) if(L[k]) L[k].value=0;})()")
        await pg.wait_for_timeout(5000); await pg.screenshot(path=pre+'_f.png')
        for name,steps in (('90',29),('180',29)):
            await pg.mouse.move(100,500); await pg.mouse.down()
            for i in range(1,steps): await pg.mouse.move(100+i*10,500)
            await pg.mouse.up(); await pg.wait_for_timeout(5000); await pg.screenshot(path=pre+f'_{name}.png')
        print(msgs); await b.close()
asyncio.run(main())
