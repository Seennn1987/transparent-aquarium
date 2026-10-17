import browser
import asyncio, sys, numpy as np, base64, json
from playwright.async_api import async_playwright
url,out=sys.argv[1],sys.argv[2]
READ='''(which)=>{const r=window.chameleonPage[which](); const u=new Uint8Array(r.data.buffer); let s=''; for(let i=0;i<u.length;i+=32768){s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));} return {w:r.width,h:r.height,b64:btoa(s)};}'''
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p)
        pg=await b.new_page(viewport={'width':800,'height':956}); msgs=[]; pg.on('pageerror',lambda e: msgs.append(str(e))); pg.on('console',lambda m: msgs.append(m.text))
        await pg.goto(url); await pg.wait_for_function('document.body.dataset.ready || document.body.dataset.error',timeout=300000)
        print(msgs, await pg.evaluate('document.querySelector("#status").textContent'))
        names=await pg.evaluate('Object.keys(window.chameleonPage.organs)'); print(names)
        async def grab(which):
            r=await pg.evaluate(READ,which); return np.frombuffer(base64.b64decode(r['b64']),np.float32).reshape(r['h'],r['w'],4)[::-1]
        await pg.evaluate('window.chameleonPage.calibrateOrgans.on=true'); await pg.wait_for_timeout(6000)
        save={'paths':await grab('paths'),'film':await grab('film')}
        saved={n: await pg.evaluate(f'window.chameleonPage.organs["{n}"].value.toArray()') for n in names}
        for g in range(0,len(names),3):
            grp=names[g:g+3]
            js='(()=>{const o=window.chameleonPage.organs; for(const n in o) o[n].value.set(0,0,0); '+''.join(f'o["{n}"].value.setComponent({i},1);' for i,n in enumerate(grp))+'})()'
            await pg.evaluate(js); await pg.wait_for_timeout(6000)
            a=await grab('organ')
            for i,n in enumerate(grp): save['org_'+n]=a[...,i]
        js='(()=>{const o=window.chameleonPage.organs; const s='+json.dumps(saved)+'; for(const n in s) o[n].value.fromArray(s[n]);})()'
        await pg.evaluate(js)
        np.savez_compressed(out,**save); print('saved',list(save))
        await b.close()
asyncio.run(main())
