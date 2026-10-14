# 横から: 膜の輪郭（塗り）と骨・軟骨の点（展示の姿勢）
import numpy as np, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
from matplotlib.collections import PolyCollection
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k'])
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
skin,body,out,title=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
view=sys.argv[5] if len(sys.argv)>5 else 'side'
d=np.load(body); S=np.load(skin); v=S['v']/k; f=S['f']
if view=='side': X=lambda p:-p[...,2]; Y=lambda p:-p[...,0]; xl,yl=(-42,125),(-80,-5)
else: X=lambda p:p[...,1]; Y=lambda p:-p[...,2]; xl,yl=(-70,25),(-42,122)
fig,a=plt.subplots(figsize=(11,6) if view=='side' else (6,8))
tri=v[f]; a.add_collection(PolyCollection(np.stack([X(tri),Y(tri)],-1),facecolor=(0.55,0.7,0.95,1),edgecolor='none'))
ca,cb,own=ct2m(d['cart__a']),ct2m(d['cart__b']),d['cart__bone']
for n in bn:
    if n+'__v' not in d.files: continue
    M=Mp[bn.index(n)]; x=(ct2m(d[n+'__v'])[::4]@M[:3,:3].T+M[:3,3])/k
    a.scatter(X(x),Y(x),s=0.08,c='tab:orange' if n=='hyoid' else '#7a1f2b',lw=0)
    m=own==n
    if m.any():
        p=(np.concatenate([ca[m],cb[m]])@M[:3,:3].T+M[:3,3])/k; a.scatter(X(p),Y(p),s=0.4,c='tab:blue',lw=0)
a.set_xlim(*xl); a.set_ylim(*yl); a.set_aspect('equal'); a.axis('off'); a.set_title(title,fontsize=12)
plt.tight_layout(); plt.savefig(out,dpi=90)
