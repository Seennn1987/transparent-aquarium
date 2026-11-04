"""歩く間の関節を書き出す（記録 139 で作業フォルダから移した）: walk_measure.py <クエリ> <出力の名前> [秒]
出力: <名前>_joints.json（0.05 秒ごと、脚ごとに 着いているか・膝/肘・足首/手首・つかむ点（股/肩から、mm、前・上・横）・股/肩の枝からの高さ）、<名前>_belly.json（1 秒ごとの腹の最下点の枝からの高さ mm）
"""
import sys,os,asyncio,json
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import browser
from playwright.async_api import async_playwright
JS='''(TE)=>{const P=window.chameleonPage,m=P.model;const V=P.camera.position.constructor;const MM=1.04/23.1;const h=m.parent;
const F=new V(0,-1,0),U=new V(-1,0,0),Lf=new V(0,0,1);const PAIR={fL:'fR',fR:'fL',hL:'hR',hR:'hL'};
const J=n=>{const b=m.getObjectByName(n);return b?h.worldToLocal(b.getWorldPosition(new V())):null};
const ang=(a,b,c)=>{const u=a.clone().sub(b),v=c.clone().sub(b);return +(Math.acos(Math.max(-1,Math.min(1,u.dot(v)/u.length()/v.length())))*180/Math.PI).toFixed(1)};
const out=[];let over=0,miss=0;const belly=[];
for(let t=0;t<=TE+1e-6;t+=0.05){const f=P.walkFeet(+t.toFixed(2));m.updateMatrixWorld(true);const row={t:+t.toFixed(2)};
 const head=J('head');row.head=[+(head.dot(F)/MM).toFixed(2),+(head.dot(U)/MM).toFixed(2),+(head.dot(Lf)/MM).toFixed(2)];
 for(const k of ['fL','fR','hL','hR']){over=Math.max(over,(f[k]?.over??0)/MM);miss=Math.max(miss,(f[k]?.miss??0)/MM);const g=k[0]==='f'?'hand':'foot';const up=J(k+'_upper'),lo=J(k+'_lower'),tip=J(k+'_'+g);const ends=['med','lat'].map(s=>J(k+'_'+g+'_'+s+'_end')||J(k+'_'+g+'_'+s+'2')).filter(Boolean);
  const grip=ends.length?ends.reduce((a,b)=>a.clone().add(b)).multiplyScalar(1/ends.length):tip;
  const lat=up.clone().sub(J(PAIR[k]+'_upper'));lat.addScaledVector(U,-lat.dot(U)).normalize();const fw=U.clone().cross(lat);if(fw.dot(F)<0)fw.negate();
  const rel=p=>[+(p.clone().sub(up).dot(fw)/MM).toFixed(2),+(p.clone().sub(up).dot(U)/MM).toFixed(2),+(p.clone().sub(up).dot(lat)/MM).toFixed(2)];
  row[k]={st:f[k]?.stance?1:0,joint:ang(up,lo,tip),knee:rel(lo),ankle:rel(tip),grip:rel(grip),upF:+(up.dot(F)/MM).toFixed(2),upU:+(up.dot(U)/MM).toFixed(2),upL:+(up.dot(Lf)/MM).toFixed(2),hgt:+(f[k].hgt||0).toFixed(2),gripW:[+(grip.dot(F)/MM).toFixed(2),+(grip.dot(U)/MM).toFixed(2),+(grip.dot(Lf)/MM).toFixed(2)]};}
 if(Math.round(t*20)%20===0){const b=P.walkBelly(+t.toFixed(2));belly.push(b.lowestMM)}
 out.push(row)}
return JSON.stringify({rows:out,over,miss,belly})}'''
async def main():
    q=sys.argv[1]; tag=sys.argv[2]; TE=float(sys.argv[3]) if len(sys.argv)>3 else 5.2
    async with async_playwright() as p:
        b=await browser.launch(p); pg=await b.new_page(viewport={'width':400,'height':400})
        logs=[]; pg.on('console',lambda m: logs.append(m.text))
        await pg.goto(browser.BASE+'/scenes/specimen/chameleon.html?walk=1&still=1&glb=root102_baked'+q)
        await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error',timeout=300000)
        err=await pg.evaluate('document.body.dataset.error')
        if err: print('エラー',err,logs[-5:]); return
        d=json.loads(await pg.evaluate(JS,TE)); await b.close()
    json.dump(d['rows'],open(f'{tag}_joints.json','w')); json.dump(d['belly'],open(f'{tag}_belly.json','w'))
    print(f"届かず {d['over']:.2f} ずれ {d['miss']:.2f}")
asyncio.run(main())
