# 膜の中の部品（臓器・内臓の塊）を姿勢で動かし、膜（diag_inside）の外に出る頂点の割合
import numpy as np
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k'])
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
z=np.load('diag_inside.npz'); I=z['inside']; lo=z['lo']; VOX=float(z['vox'])
S=np.load('chameleon_body_soft.npz')
parts=sorted({f.split('__')[0] for f in S.files})
for p in parts:
    v=ct2m(S[p+'__v']); wi=S[p+'__w_idx']; wv=S[p+'__w_val']; names=[str(x) for x in S[p+'__names']]
    Ms=np.array([Mp[bn.index(n)] for n in names])
    M=np.einsum('vk,vkij->vij',wv,Ms[wi]); x=np.einsum('vij,vj->vi',M,np.c_[v,np.ones(len(v))])[:,:3]
    g=((x-lo)/VOX).round().astype(int); ok=(g>=0).all(1)&(g<np.array(I.shape)).all(1)
    ins=np.zeros(len(x),bool); ins[ok]=I[tuple(g[ok].T)]
    print('%-18s verts %6d outside the skin %.2f%%'%(p,len(x),100*(~ins).mean()))
