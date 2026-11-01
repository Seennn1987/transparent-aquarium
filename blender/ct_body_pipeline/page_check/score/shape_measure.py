"""形の物差しのモデル側: shape.py <クエリ> <出力json>。歩くページの t=0 の姿勢で、皮と骨から寸法を測る（mm）"""
import sys,asyncio,json,os
sys.path.insert(0,'/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_body_pipeline/page_check')
import browser
from playwright.async_api import async_playwright
JS='''async ()=>{const THREE=await import('three');const P=window.chameleonPage,m=P.model,h=m.parent;const V=THREE.Vector3;const MM=1.04/23.1;
if(location.search.includes('walk=1')){P.walkTo(0);P.walkFeet(0)}m.updateMatrixWorld(true);
let skin=null;m.traverse(o=>{if(o.name==='CH_Skin')skin=o});skin.skeleton.update();
const J=n=>h.worldToLocal(m.getObjectByName(n).getWorldPosition(new V()));
const bones=skin.skeleton.bones;const pos=skin.geometry.attributes.position,si=skin.geometry.attributes.skinIndex,sw=skin.geometry.attributes.skinWeight;
const verts=[];const v=new V();
for(let i=0;i<pos.count;i++){v.fromBufferAttribute(pos,i);skin.applyBoneTransform(i,v);const w=v.clone().applyMatrix4(skin.matrixWorld);const p=h.worldToLocal(w);
 let top='',tw=0,limb=0,head=0;for(let k=0;k<4;k++){const n=bones[si.getComponent(i,k)].name,ww=sw.getComponent(i,k);if(ww>tw){tw=ww;top=n}if(/^[fh][LR]_/.test(n))limb+=ww;if(n==='head'||n==='hyoid')head+=ww}
 verts.push([p.x/MM,p.y/MM,p.z/MM,limb,head,top])}
const pt=n=>{const p=J(n);return [p.x/MM,p.y/MM,p.z/MM]};
const names=['fL_upper','fL_lower','fL_hand','fR_upper','hL_upper','hL_lower','hL_foot','hR_upper','head','v01','v02','v22','v23','v24','v25'];
const B={};for(const n of names)B[n]=pt(n);
const sp=[];for(let k=1;k<=78;k++){const n='v'+String(k).padStart(2,'0');const b=m.getObjectByName(n);if(b)sp.push([n,pt(n)])}
return {verts,B,spine:sp}}'''
async def main():
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page()
        await pg.goto(os.environ.get('BASE','http://127.0.0.1:8080/scenes/specimen/chameleon.html?walk=1&still=1&glb=root102_baked')+sys.argv[1]); await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=300000)
        d=await pg.evaluate(JS); await b.close()
    json.dump(d,open(sys.argv[2],'w'))
asyncio.run(main())
