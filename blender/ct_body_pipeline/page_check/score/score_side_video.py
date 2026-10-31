# 使い方: python score_side_video.py <joints の json（page_check の meas3.js の出力）> [1 歩の秒数] [-v]
"""採点 v2（記録 127）: 横から見た実物（Wimberly ら 2021、エボシ成体、床、0.1 秒ごと 33 コマの 1 歩）と同じ横の面で、
動画で確かに読める量だけを比べる（肩・股の目印は体の外形から読むので、骨の付け根からの位置は使わない。2 次元の骨の長さが 0.09〜0.33 L とばらつくため）。
項目（前脚・後ろ脚、1 歩を 10 に分けた時刻ごと）: 肘（膝）の高さ、手首（足首）の高さ、肩（股）の高さ（足場の上、÷ 吻端–股関節 L）、肘（膝）の 2 次元の角度、
手のひら（足のひら）の前後（肩・股から）、着いているか。合格の幅: 高さ 0.04 L、前後 0.06 L、角度 20°、またはその時刻の実物のコマどうしの幅の大きい方"""
import json,sys,numpy as np
R=json.load(open('/Users/shoui/transparent-aquarium/画像サンプル収集/エボシカメレオン/収集_2026-10-26/関節の動き/場面1_ZA_304-310s.json'))['コマ']
A=[a for a in sys.argv[2:] if a!='-v']; rows=json.load(open(sys.argv[1])); T=float(A[0]) if A else 95/36.4; L=123.3; verbose='-v' in sys.argv
def ang2(a,b,c):
    u=np.array(a,float)-np.array(b,float); v=np.array(c,float)-np.array(b,float); return float(np.degrees(np.arccos(np.clip(u@v/np.linalg.norm(u)/np.linalg.norm(v),-1,1))))
real={}
for c in R:
    k=c['計算']; s=k['尺度_px']
    for limb,root,mid,dist,end,ph,gk in [('前','肩','肘','手首','手のひら','手前前脚の位相','手前前脚の下'),('後','股関節','膝','足首','足のひら','手前後脚の位相','手前後脚の下')]:
        leg=c['手前前脚' if limb=='前' else '手前後脚']; p=k.get(ph); g=c['地面の上の縁y'].get(gk)
        if p is None or g is None or not c.get(root) or not leg.get(mid) or not leg.get(dist): continue
        b=int(min(9,p*10)); d=real.setdefault((limb,b),{})
        for nm,val in [(mid+'の高さ',(g-leg[mid][1])/s),(dist+'の高さ',(g-leg[dist][1])/s),(root+'の高さ',(g-c[root][1])/s),(mid+'の角度',ang2(c[root],leg[mid],leg[dist])),
                       (end+'の前後',-(leg[end][0]-c[root][0])/s if leg.get(end) else None),('着いている',1.0 if leg.get('着地') else 0.0)]:
            if val is not None: d.setdefault(nm,[]).append(val)
mod={}
for k,limb in [('fL','前'),('hL','後')]:
    st=[r[k]['st'] for r in rows]; ts=[r['t'] for r in rows]; t0=[ts[i] for i in range(1,len(rows)) if st[i] and not st[i-1]][0]
    mid,dist,end,root=('肘','手首','手のひら','肩') if limb=='前' else ('膝','足首','足のひら','股関節')
    for r in rows:
        p=((r['t']-t0)%T)/T; b=int(min(9,p*10)); x=r[k]; h=x['hgt']/L
        kn=np.array(x['knee'])/L; an=np.array(x['ankle'])/L; gr=np.array(x['grip'])/L
        d=mod.setdefault((limb,b),{})
        for nm,val in [(mid+'の高さ',h+kn[1]),(dist+'の高さ',h+an[1]),(root+'の高さ',h),(mid+'の角度',ang2([0,0],kn[:2],an[:2])),(end+'の前後',gr[0]),('着いている',float(x['st']))]:
            d.setdefault(nm,[]).append(val)
res=[]
for key in sorted(real):
    for nm,vals in real[key].items():
        if key not in mod or nm not in mod[key]: continue
        rv=np.mean(vals); sp=(max(vals)-min(vals))/2; mv=np.mean(mod[key][nm])
        tol=max(20 if '角度' in nm else 0.04 if '高さ' in nm else 0.5 if '着いて' in nm else 0.06, sp)
        res.append((key[0],key[1],nm,rv,mv,tol,abs(mv-rv)<=tol))
n=sum(r[6] for r in res)
grp={}
for r in res:
    g=r[2]; grp.setdefault(g,[0,0]); grp[g][0]+=r[6]; grp[g][1]+=1
print(' '.join(f'{g} {a}/{b}' for g,(a,b) in grp.items()))
if verbose:
    for r in res:
        if not r[6]: print(f'× {r[0]}脚 時刻{r[1]/10:.1f} {r[2]:8s} 実物 {r[3]:+.3f} モデル {r[4]:+.3f} 幅 {r[5]:.3f}')
print(f'合格 {n}/{len(res)}（{100*n/len(res):.0f}%）')
