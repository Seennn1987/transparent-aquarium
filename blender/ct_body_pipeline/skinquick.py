# 膜（展示の姿勢）の陰影図（画家のアルゴリズム、平らな陰影）と、骨の点。横・上・下・前
import numpy as np, matplotlib, sys; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
from matplotlib.collections import PolyCollection
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k'])
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
S=np.load(sys.argv[1]); v=S['v']/k; f=S['f']
# モデル座標: x = 前後?、y = 上、z = 左右? 範囲で決める
ext=v.max(0)-v.min(0); print('extent mm',ext)
q=np.array([1.,1.,-0.6]); q/=np.linalg.norm(q)
views={'右から':(np.array([0,1.,0]),np.array([-1.,0,0])),'左から':(np.array([0,-1.,0]),np.array([-1.,0,0])),'背から':(np.array([-1.,0,0]),np.array([0,0,-1.])),
       '腹から':(np.array([1.,0,0]),np.array([0,0,-1.])),'前から':(np.array([0,0,-1.]),np.array([-1.,0,0])),
       '斜め前':(np.array([-0.5,0.6,-0.62])/np.linalg.norm([-0.5,0.6,-0.62]),np.array([-1.,0,0]))}
sel=sys.argv[3].split(',') if len(sys.argv)>3 else list(views)
fig,ax=plt.subplots(1,len(sel),figsize=(float(sys.argv[5]) if len(sys.argv)>5 else 9*len(sel),8))
ax=np.atleast_1d(ax)
tri=v[f]; n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=np.linalg.norm(n,axis=1,keepdims=True)+1e-12
for a,nm in zip(ax,sel):
    vd,up=views[nm]; up=up-vd*(up@vd); up/=np.linalg.norm(up); rt=np.cross(up,vd)
    X=tri@rt; Y=tri@up; Z=tri@vd
    face=(n@vd)>0
    o=np.argsort(Z[face].mean(1))
    sh=np.clip(0.25+0.75*(n[face]@vd),0,1)[o]
    a.add_collection(PolyCollection(np.stack([X[face][o],Y[face][o]],-1),facecolors=plt.cm.gray(0.2+0.75*sh),edgecolor='none',antialiased=False))
    a.set_aspect('equal'); a.autoscale()
    if len(sys.argv)>4:
        c=[float(x) for x in sys.argv[4].split(',')]; a.set_xlim(c[0],c[1]); a.set_ylim(c[2],c[3]); a.set_title(nm); a.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=55)
