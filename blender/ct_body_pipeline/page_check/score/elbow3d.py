"""モデルの肘・手首と胴の幅を、体の向き（前・上・横）で測る: elbow3d.py <クエリ> <出力json>"""
import sys,asyncio,json
sys.path.insert(0,'/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_body_pipeline/page_check')
import browser
from playwright.async_api import async_playwright
JS='''async (ts)=>{const THREE=await import('three');const P=window.chameleonPage,m=P.model,h=m.parent;const V=THREE.Vector3;const MM=1.04/23.1;
const fw=new V(0,-1,0),up=new V(-1,0,0),lf=new V(0,0,1);
const meshes=[];m.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o)});
const out=[];
for(const t of ts){P.walkTo(t);P.walkFeet(t);m.updateMatrixWorld(true);
 const J=n=>{const b=m.getObjectByName(n);return h.worldToLocal(b.getWorldPosition(new V()))};
 const sL=J('fL_upper'),sR=J('fR_upper'),mid=sL.clone().add(sR).multiplyScalar(0.5);
 const B=p=>{const d=p.clone().sub(mid);return [d.dot(fw)/MM,d.dot(up)/MM,d.dot(lf)/MM]};
 // 胴の幅: 肩の前後 ±3 mm の輪切りで、手足の骨に重みの大きい頂点を除いた皮の左右の端
 let wl=-1e9,wr=1e9,top=-1e9,bot=1e9;const v=new V();
 for(const me of meshes){const pos=me.geometry.attributes.position,sw=me.geometry.attributes.skinWeight,si=me.geometry.attributes.skinIndex;if(!sw)continue;const bones=me.skeleton.bones;
  for(let i=0;i<pos.count;i+=1){let limb=0;for(let k=0;k<4;k++){const n=bones[si.getComponent(i,k)].name;if(/^[fh][LR]_/.test(n))limb+=sw.getComponent(i,k)}if(limb>0.3)continue;
   v.fromBufferAttribute(pos,i);me.applyBoneTransform(i,v);v.applyMatrix4(me.matrixWorld);h.worldToLocal(v);const b=B(v);if(Math.abs(b[0])>3)continue;wl=Math.max(wl,b[2]);wr=Math.min(wr,b[2]);top=Math.max(top,b[1]);bot=Math.min(bot,b[1])}}
 const r={t};for(const k of ['fL','fR']){r[k]={sh:B(J(k+'_upper')),el:B(J(k+'_lower')),wr:B(J(k+'_hand')),st:P.walkFeet(t)[k]?.stance?1:0}}
 r.wall=[wl,wr];r.topbot=[top,bot];out.push(r)}
return out}'''
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page(viewport={'width':400,'height':400})
        await pg.goto('http://127.0.0.1:8080/scenes/specimen/chameleon.html?walk=1&still=1&glb=root102_baked'+sys.argv[1]); await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=300000)
        d=await pg.evaluate(JS,[round(i*0.1,2) for i in range(27)]); await b.close()
    json.dump(d,open(sys.argv[2],'w'))
    for r in d[::3]:
        f=r['fL']; print(f"t {r['t']:.1f} 着地{f['st']} 胴の左右 {r['wall'][0]:+.1f}/{r['wall'][1]:+.1f} 高さ {r['topbot'][0]:+.1f}/{r['topbot'][1]:+.1f}  肩 {f['sh'][0]:+.1f},{f['sh'][1]:+.1f},{f['sh'][2]:+.1f}  肘 {f['el'][0]:+.1f},{f['el'][1]:+.1f},{f['el'][2]:+.1f}  手首 {f['wr'][0]:+.1f},{f['wr'][1]:+.1f},{f['wr'][2]:+.1f}")
asyncio.run(main())
