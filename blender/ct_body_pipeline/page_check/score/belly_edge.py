"""腹の下の縁のでこぼこ（記録 139 で作り直した）: belly_edge.py 名前 クエリ [名前 クエリ …]
時刻 1.3・2.6・3.9・6.5 秒で、胴の膜（手足・頭の重み 0.1 未満）の頂点を横から見て、股関節の前 0 から肩関節の 10 mm 手前まで（肩の付け根の下りを外す）0.5 mm ごとの最も低い点を取り、
17 点の移動平均からの差の RMS と最大（mm）を出す"""
import sys,os,asyncio,json,numpy as np
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import browser
from playwright.async_api import async_playwright
JS='''async (ts)=>{const THREE=await import('three');const P=window.chameleonPage,m=P.model,h=m.parent;const V=THREE.Vector3;const MM=1.04/23.1;
const F=new V(0,-1,0),U=new V(-1,0,0);let sk=null;m.traverse(o=>{if(o.name==='CH_Skin')sk=o});const out=[];
for(const t of ts){P.walkTo(t);P.walkFeet(t);m.updateMatrixWorld(true);sk.skeleton.update();
 const J=n=>h.worldToLocal(m.getObjectByName(n).getWorldPosition(new V()));const hp=J('hL_upper').add(J('hR_upper')).multiplyScalar(0.5),sh=J('fL_upper').add(J('fR_upper')).multiplyScalar(0.5);
 const ax=sh.clone().sub(hp);const S=ax.length();ax.normalize();const dn=U.clone().addScaledVector(ax,-U.dot(ax)).normalize();
 const pos=sk.geometry.attributes.position,si=sk.geometry.attributes.skinIndex,sw=sk.geometry.attributes.skinWeight,bs=sk.skeleton.bones;const v=new V();const nb=Math.floor((S/MM-10)/0.5);const lo=new Array(nb).fill(1e9);
 for(let i=0;i<pos.count;i++){let w=0;for(let k=0;k<4;k++){const n=bs[si.getComponent(i,k)].name;if(/^[fh][LR]_|^head$|^hyoid/.test(n))w+=sw.getComponent(i,k)}if(w>0.1)continue;
  v.fromBufferAttribute(pos,i);sk.applyBoneTransform(i,v);v.applyMatrix4(sk.matrixWorld);h.worldToLocal(v);const d=v.clone().sub(hp);const x=d.dot(ax)/MM,y=d.dot(dn)/MM;const b=Math.floor(x/0.5);if(b<0||b>=nb)continue;lo[b]=Math.min(lo[b],y)}
 const xs=[],ys=[];lo.forEach((y,b)=>{if(y<1e8){xs.push(b*0.5);ys.push(y)}});out.push({t,xs,ys})}
return out}'''
async def run(q):
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page(viewport={'width':400,'height':400})
        await pg.goto(browser.BASE+'/scenes/specimen/chameleon.html?walk=1&still=1'+q)
        await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=300000)
        d=await pg.evaluate(JS,[1.3,2.6,3.9,6.5]); await b.close(); return d
for lab,q in zip(sys.argv[1::2],sys.argv[2::2]):
    res=[]
    for r in asyncio.run(run(q)):
        x=np.array(r['xs']); y=np.array(r['ys']); k=17
        pad=np.r_[np.full(k//2,y[0]),y,np.full(k//2,y[-1])]; e=y-np.convolve(pad,np.ones(k)/k,'valid')
        res.append((r['t'],np.sqrt((e**2).mean()),np.abs(e).max(),x[np.argmax(np.abs(e))]))
    print(lab,' '.join(f"t{t}: RMS {a:.2f} 最大 {b:.2f}mm（股の前 {c:.0f}mm）" for t,a,b,c in res),flush=True)
