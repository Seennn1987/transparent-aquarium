# 膜の自己検証: 展示の姿勢の膜（skin_posed.npz）の内側を光線の偶奇で 3 方向から求め、骨のはみ出し・面の不整合を数える
import numpy as np, scipy.ndimage as nd, json, time
t0=time.time()
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k']); MM=k
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
S=np.load('skin_posed.npz'); sv=S['v'].astype(np.float64); sf=S['f']
VOX=0.2*MM
lo=sv.min(0)-3*VOX; hi=sv.max(0)+3*VOX; shape=tuple(np.ceil((hi-lo)/VOX).astype(int)+1)
print('grid',shape)
tri=sv[sf]
def parity(ax):
    a,b=[i for i in range(3) if i!=ax]
    cnt=np.zeros(shape,np.int16)
    P0,P1,P2=tri[:,0],tri[:,1],tri[:,2]
    mn=np.floor((np.minimum(np.minimum(P0,P1),P2)-lo)/VOX).astype(int); mx=np.ceil((np.maximum(np.maximum(P0,P1),P2)-lo)/VOX).astype(int)
    hits=[]
    for t in range(len(tri)):
        ia=np.arange(mn[t,a],mx[t,a]+1); ib=np.arange(mn[t,b],mx[t,b]+1)
        if len(ia)==0 or len(ib)==0: continue
        A,B=np.meshgrid(lo[a]+ia*VOX,lo[b]+ib*VOX,indexing='ij'); A=A.ravel(); B=B.ravel()
        p0,p1,p2=P0[t],P1[t],P2[t]
        d=(p1[a]-p0[a])*(p2[b]-p0[b])-(p2[a]-p0[a])*(p1[b]-p0[b])
        if abs(d)<1e-14: continue
        l1=((A-p0[a])*(p2[b]-p0[b])-(p2[a]-p0[a])*(B-p0[b]))/d; l2=((p1[a]-p0[a])*(B-p0[b])-(A-p0[a])*(p1[b]-p0[b]))/d
        m=(l1>=0)&(l2>=0)&(l1+l2<=1)
        if not m.any(): continue
        z=p0[ax]+l1[m]*(p1[ax]-p0[ax])+l2[m]*(p2[ax]-p0[ax])
        hits.append(np.stack([np.repeat(0,m.sum()), ((A[m]-lo[a])/VOX).round().astype(int), ((B[m]-lo[b])/VOX).round().astype(int), ((z-lo[ax])/VOX).astype(int)],1))
    H=np.concatenate(hits)
    # 各光線（a,b）で、z の小さい順に越えた数の偶奇
    flip=np.zeros(shape,np.int8)
    idx=[0,0,0]; 
    sl=np.zeros(3,int)
    I=np.zeros((len(H),3),int); I[:,a]=H[:,1]; I[:,b]=H[:,2]; I[:,ax]=np.clip(H[:,3]+1,0,shape[ax]-1)
    np.add.at(flip,tuple(I.T),1)
    return (np.cumsum(flip,axis=ax)%2).astype(bool)
z0=np.load('diag_inside.npz'); inside=z0['inside']
from scipy.spatial import cKDTree
kd=cKDTree(sv)
d=np.load('chameleon_body_ct.npz')
rows=[]
for n in bn:
    if n+'__v' not in d.files: continue
    v=ct2m(d[n+'__v']); M=Mp[bn.index(n)]; vp=v@M[:3,:3].T+M[:3,3]
    g=np.clip(((vp-lo)/VOX).round().astype(int),0,np.array(shape)-1)
    out=~inside[tuple(g.T)]
    dist=kd.query(vp,workers=-1)[0]/MM
    o=np.where(out,dist,0)
    rows.append((n,len(vp),float((o>0.1).mean()),float(o.max())))
    np.save('diag_out_%s.npy'%n,np.c_[vp,o].astype(np.float32))
rows.sort(key=lambda r:-r[3])
for n,nv,fr,mx in rows[:25]: print('%-10s verts %6d outside>0.1mm %5.1f%%  max %.2f mm'%(n,nv,100*fr,mx))
json.dump([[n,fr,mx] for n,nv,fr,mx in rows],open('diag_bone_out.json','w'))
