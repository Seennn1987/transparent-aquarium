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
ins=[parity(ax) for ax in range(3)]
print('parity done',f'{time.time()-t0:.0f}s')
agree=(ins[0]==ins[1])&(ins[1]==ins[2])
inside=(ins[0].astype(int)+ins[1]+ins[2])>=2
print('voxels inside',int(inside.sum()),'disagreeing (holes / self-intersection)',int((~agree).sum()), 'share %.4f'%((~agree).sum()/max(inside.sum(),1)))
np.savez_compressed('diag_inside.npz',inside=inside,disagree=~agree,lo=lo,vox=VOX)
