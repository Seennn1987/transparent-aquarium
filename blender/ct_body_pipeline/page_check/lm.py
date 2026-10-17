import asyncio, sys, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium',args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--no-proxy-server'])
        pg=await b.new_page(viewport={'width':800,'height':956})
        await pg.goto(sys.argv[1]); await pg.wait_for_function('document.body.dataset.ready',timeout=300000)
        r=await pg.evaluate('''()=>{const c=window.chameleonPage; const out={}; const W=c.renderer.domElement.width, H=c.renderer.domElement.height;
          for (const n of ["fL_upper","fR_upper","hL_upper","hR_upper","head","v20","v26","v10"]) { const o=c.model.getObjectByName(n); if(!o) continue; const p=new o.position.constructor(); o.getWorldPosition(p); p.project(c.camera); out[n]=[(p.x+1)/2*W,(1-p.y)/2*H]; }
          out.size=[W,H]; return out;}''')
        print(json.dumps(r)); await b.close()
asyncio.run(main())
