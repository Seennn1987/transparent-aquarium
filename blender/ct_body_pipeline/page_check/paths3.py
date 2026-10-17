import asyncio, sys, numpy as np, base64
from playwright.async_api import async_playwright
url,out=sys.argv[1],sys.argv[2]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-proxy-server'])
        pg=await b.new_page(viewport={'width':800,'height':956})
        msgs=[]; pg.on('pageerror',lambda e: msgs.append(str(e)))
        await pg.goto(url)
        await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error',timeout=300000)
        import os
        if os.environ.get('MINCOS'):
            await pg.evaluate("async()=>{const m=await import('/scenes/specimen/src/chameleon-material.js'); m.chameleonFilm.minCos.value=%s;}"%os.environ['MINCOS'])
        await pg.wait_for_timeout(5000)
        js='''()=>{const r=window.chameleonPage[window.__which||'paths'](); const u=new Uint8Array(r.data.buffer); let s=''; for(let i=0;i<u.length;i+=32768){s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));} return {w:r.width,h:r.height,b64:btoa(s)};}'''
        r=await pg.evaluate(js)
        await pg.evaluate('window.__which="film"'); rf=await pg.evaluate(js)
        f=np.frombuffer(base64.b64decode(rf['b64']),np.float32).reshape(rf['h'],rf['w'],4)[::-1]; np.save(out.replace('.npy','_film.npy'),f)
        a=np.frombuffer(base64.b64decode(r['b64']),np.float32).reshape(r['h'],r['w'],4)[::-1]
        np.save(out,a); await pg.screenshot(path=out.replace('.npy','.png'),timeout=300000)
        print(r['w'],r['h'],msgs)
        await b.close()
asyncio.run(main())
