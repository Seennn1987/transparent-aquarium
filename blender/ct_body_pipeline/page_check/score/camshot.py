"""モデルを好きな向きから撮る: camshot.py URL 出力 時刻 前 上 横 [視野角]（肩と股の間の点からの向き、肩–股の長さの倍数）
横から 0.6 0.6 -5 18、上から 0.4 6 0.01 18、斜め前 3.0 1.2 -1.6 20（記録 139 で作業フォルダから移した）"""
import sys,os,asyncio
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import browser
from playwright.async_api import async_playwright
JS='''async ([t,f,u,l,fov])=>{const THREE=await import('three');const P=window.chameleonPage,m=P.model,h=m.parent,c=P.camera;const V=THREE.Vector3;if(location.search.includes('walk=1')){P.walkTo(t);P.walkFeet(t)}
m.updateMatrixWorld(true);const J=n=>m.getObjectByName(n).getWorldPosition(new V());
const hp=J('hL_upper').add(J('hR_upper')).multiplyScalar(0.5),sp=J('fL_upper').add(J('fR_upper')).multiplyScalar(0.5);const S=hp.distanceTo(sp);
const fw=new V(0,-1,0).transformDirection(h.matrixWorld),up=new V(-1,0,0).transformDirection(h.matrixWorld),lf=new V(0,0,1).transformDirection(h.matrixWorld);
const tgt=sp.clone().lerp(hp,0.35);c.position.copy(tgt).addScaledVector(fw,f*S).addScaledVector(up,u*S).addScaledVector(lf,l*S);c.up.copy(up);c.fov=fov;c.near=0.05*S;c.far=200*S;c.updateProjectionMatrix();c.lookAt(tgt);return 1}'''
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page(viewport={'width':1200,'height':800})
        await pg.goto(sys.argv[1] + ('' if 'still=1' in sys.argv[1] else '&still=1')); await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=240000)
        await pg.add_style_tag(content='#status,#tune,#rotate{visibility:hidden!important}')
        a=[float(x) for x in sys.argv[3:7]]+[float(sys.argv[7]) if len(sys.argv)>7 else 14]
        await pg.evaluate(JS,a); await pg.wait_for_timeout(1500); await pg.screenshot(path=sys.argv[2]); await b.close()
if __name__ == "__main__": asyncio.run(main())
