"""手足の膜が骨についているか（記録 143）: limbskin.py <クエリ> [時刻…]
各脚の上の骨・下の骨に重み 0.5 以上の膜の頂点と、その骨の線分との距離（mm）の中央値・最大"""
import sys,os,asyncio,json
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import browser
from playwright.async_api import async_playwright
JS='''async (ts)=>{const THREE=await import('three');const P=window.chameleonPage,m=P.model,h=m.parent;const V=THREE.Vector3;const MM=1.04/23.1;
let sk=null;m.traverse(o=>{if(o.name==='CH_Skin')sk=o});const bs=sk.skeleton.bones;const out=[];
const pos=sk.geometry.attributes.position,si=sk.geometry.attributes.skinIndex,sw=sk.geometry.attributes.skinWeight;
for(const t of ts){P.walkTo(t);P.walkFeet(t);m.updateMatrixWorld(true);sk.skeleton.update();const J=n=>m.getObjectByName(n).getWorldPosition(new V());
 const segs={};for(const k of ['fL','fR','hL','hR']){const g=k[0]==='f'?'hand':'foot';segs[k+'_upper']=[J(k+'_upper'),J(k+'_lower')];segs[k+'_lower']=[J(k+'_lower'),J(k+'_'+g)]}
 const d={};const v=new V();
 for(let i=0;i<pos.count;i++){let bi=-1,bw=0;for(let c=0;c<4;c++){const w=sw.getComponent(i,c);if(w>bw){bw=w;bi=si.getComponent(i,c)}}const n=bs[bi].name;if(bw<0.5||!segs[n])continue;
  v.fromBufferAttribute(pos,i);sk.applyBoneTransform(i,v);v.applyMatrix4(sk.matrixWorld);const [a,b]=segs[n];const ab=b.clone().sub(a);const u=Math.max(0,Math.min(1,v.clone().sub(a).dot(ab)/ab.lengthSq()));const q=a.clone().addScaledVector(ab,u);
  (d[n]??=[]).push(q.distanceTo(v)/MM*(1/h.getWorldScale(new V()).x))}
 const r={t};for(const n in d){const s=d[n].sort((x,y)=>x-y);r[n]=[s.length,+s[Math.floor(s.length/2)].toFixed(2),+s[s.length-1].toFixed(2)]}out.push(r)}
return out}'''
async def main():
    q=sys.argv[1]; ts=[float(x) for x in sys.argv[2:]] or [0,1.1,1.85,3.75,5.15]
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page(viewport={'width':400,'height':400})
        await pg.goto(browser.BASE+'/scenes/specimen/chameleon.html?walk=1&still=1'+(q if 'glb=' in q else '&glb=root102_baked'+q)); await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=300000)
        for r in await pg.evaluate(JS,ts): print(json.dumps(r,ensure_ascii=False))
        await b.close()
asyncio.run(main())
