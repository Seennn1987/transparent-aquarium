# 肋骨ごとの輪の腹の端（軟骨の最も腹の点）: 展示の姿勢の体軸の枠（diag と同じ）で u と腹への深さ
import numpy as np, json, sys
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
from scipy.spatial import cKDTree
d=np.load(sys.argv[1] if len(sys.argv)>1 else 'chameleon_body_ct.npz')
kp=cKDTree(Cp)
ca,cb,own=ct2m(d['cart__a']),ct2m(d['cart__b']),d['cart__bone']
res={}
for i in range(1,22):
    for sl in 'LR':
        n=f'rib{i:02d}_{sl}'
        if n not in bn: continue
        M=Mof(n); pts=[]
        if n+'__v' in d.files: pts.append(ct2m(d[n+'__v']))
        m=own==n
        if m.any(): pts += [ca[m],cb[m]]
        x=np.concatenate(pts)@M[:3,:3].T+M[:3,3]
        j=kp.query(x)[1]; q=x-Cp[j]; vd=-(q*Dp[j]).sum(1)/MM
        b=np.argmax(vd); res[n]=(float(arc[j[b]]),float(vd[b]))
json.dump(res,open('ribbottom.json','w'))
for i in range(1,22):
    r=[res.get(f'rib{i:02d}_{s}') for s in 'LR']; r=[x for x in r if x]
    if r: print(i,'u %.1f ventral %.1f'%(np.mean([x[0] for x in r]),np.mean([x[1] for x in r])))
