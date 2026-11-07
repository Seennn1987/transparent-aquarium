"""焼き込み（shape88）の段ごとに裏返った面の数と場所（x）を出す（記録 144）: shape_debug.py <glb の名前>"""
import sys,os,asyncio,json,re
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import browser
from playwright.async_api import async_playwright
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','bake_shape88.py')).read()
BQ=re.search(r"BAKE_Q = '([^']*)'",src).group(1)
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page()
        await pg.goto(f'{browser.BASE}/scenes/specimen/chameleon.html?walk=1&still=1&tune=0&shape=88&shapeDebug=1&glb={sys.argv[1]}'+os.environ.get('CH_BAKE_Q','')+BQ)
        await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=300000)
        d=await pg.evaluate('window.chameleonPage.model.userData.shapeDebug')
        for tag,n,h in d: print(tag,n,{k:v for k,v in sorted(h.items()) if v>=3})
        await b.close()
asyncio.run(main())
