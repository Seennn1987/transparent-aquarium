"""モデルを同じ向きで時刻を進めながら撮る（記録 142）: camseq.py URL 出力フォルダ 始め 終わり 間隔 前 上 横 [視野角] [左右反転 0/1]
ページを 1 回だけ開き、時計を止めて（still=1）時刻ごとに撮る。名前は 000.png から"""
import sys,os,asyncio
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import browser
from playwright.async_api import async_playwright
from camshot import JS
async def main():
    url,out=sys.argv[1],sys.argv[2]; t0,t1,dt=map(float,sys.argv[3:6]); f,u,l=map(float,sys.argv[6:9]); fov=float(sys.argv[9]) if len(sys.argv)>9 else 18; flip=len(sys.argv)>10 and sys.argv[10]=='1'
    os.makedirs(out,exist_ok=True)
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page(viewport={'width':1200,'height':800})
        await pg.goto(url+('' if 'still=1' in url else '&still=1')); await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=240000)
        await pg.add_style_tag(content='#status,#tune,#rotate,.panel,[class*=panel]{visibility:hidden!important}')
        n=0; t=t0
        while t<=t1+1e-6:
            await pg.evaluate(JS,[t,f,u,l,fov]); await pg.wait_for_timeout(250); pth=f'{out}/{n:03d}.png'; await pg.screenshot(path=pth)
            if flip:
                from PIL import Image,ImageOps; ImageOps.mirror(Image.open(pth)).save(pth)
            n+=1; t=round(t+dt,4)
        await b.close(); print(n,'枚')
asyncio.run(main())
