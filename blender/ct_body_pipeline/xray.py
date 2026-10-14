# 展示の姿勢の膜（内側の升）と骨（姿勢の骨のボクセル）の通り道を正射影で足した、確かめ用の絵
import numpy as np, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
z=np.load(sys.argv[1]); I=z['inside']; lo=z['lo']; vox=float(z['vox'])
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; k=float(P['k'])
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
d=np.load('chameleon_body_ct.npz')
B=np.zeros(I.shape,np.float32)
for n in bn:
    if n+'__v' not in d.files: continue
    v=ct2m(d[n+'__v']); M=P['M'][bn.index(n)]; vp=v@M[:3,:3].T+M[:3,3]
    g=np.round((vp-lo)/vox).astype(int); ok=(g>=0).all(1)&(g<np.array(I.shape)).all(1); np.add.at(B,tuple(g[ok].T),1)
fig,ax=plt.subplots(1,2,figsize=(16,12))
for i,axis in enumerate((1,0)):
    sk=I.sum(axis)*0.2; bo=np.minimum(B.sum(axis),30)/30
    img=np.ones(sk.shape+(3,)); a=np.clip(sk/12,0,1)
    img=img*(1-0.55*a[...,None]*np.array([0.6,0.3,0.0]))      # 膜 = 青
    img=img*(1-0.8*bo[...,None]*np.array([0.2,0.9,0.7]))      # 骨 = 赤
    ax[i].imshow(np.transpose(img,(1,0,2)) if axis==1 else np.transpose(img,(1,0,2)),origin='lower'); ax[i].axis('off')
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=55)
