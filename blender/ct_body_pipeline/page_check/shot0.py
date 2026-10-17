import browser
import asyncio, sys
from playwright.async_api import async_playwright
url,out=sys.argv[1],sys.argv[2]
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p)
        pg=await b.new_page(viewport={'width':800,'height':956})
        await pg.goto(url); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error',timeout=300000)
        await pg.evaluate('window.chameleonPage.organs.hyoid_cartilage.value.set(0,0,0)')
        await pg.wait_for_timeout(8000); await pg.screenshot(path=out); await b.close()
asyncio.run(main())
