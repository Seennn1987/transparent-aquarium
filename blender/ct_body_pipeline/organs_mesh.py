# 臓器のラベル（organs.py、展示の姿勢）を面にし、体軸の骨（椎骨）に重みを付けて、静止の姿勢へ戻す
#   重み: 体軸に沿った位置 u で、前後の椎骨 2 個に直線で配る（臓器は椎骨と一緒に動く。肋骨の呼吸では動かない）
#   出力: organs_rigged.npz（臓器ごとに <名前>__v（CT の mm、静止）、__f、__w_idx、__w_val、names = 骨の名前）
import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
from skimage import measure
import pyfqmr
z=np.load('organs_lab.npz'); L=z['lab']; names=[str(n) for n in z['names']]; lo=z['lo']; VOX=float(z['vox'])
c=np.load('organs_cav.npz'); us=c['us']; AP=c['AP']; arc=c['arc']; ks=c['ks']
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k'])
def m2ct(m): m=np.asarray(m,float)/k; return np.stack([-m[...,2],m[...,0],-m[...,1]],-1)
vnames=[f'v{kk:02d}' for kk in ks]; vid=[bn.index(n) for n in vnames]
kt=cKDTree(AP)
out={}; bones=sorted(set(vnames)); bidx={n:i for i,n in enumerate(bones)}
FACES={'contents':16000,'intestine':20000}
for j,n in enumerate(names,1):
    m=L==j
    if m.sum()<20: print('skip',n); continue
    F=nd.gaussian_filter(np.pad(m,3).astype(np.float32),1.0)
    v,f,_,_=measure.marching_cubes(F,0.5)
    e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1); _,cnt=np.unique(e,axis=0,return_counts=True)
    if (cnt!=2).any():     # 管どうしが点で触れる所は、面が閉じない。少しぼかし直して離す
        F=nd.gaussian_filter(np.pad(m,3).astype(np.float32),1.4); v,f,_,_=measure.marching_cubes(F,0.5)
        e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1); _,cnt=np.unique(e,axis=0,return_counts=True)
        print(n,'marching cubes non-manifold edges after re-blur',int((cnt!=2).sum()))
    v=lo+(v-3)*VOX
    v0,f0=v,f
    for ag in (7,5,3):
        sp=pyfqmr.Simplify(); sp.setMesh(v0.astype(np.float64),f0.astype(np.int32)); sp.simplify_mesh(target_count=FACES.get(n,4000),aggressiveness=ag,preserve_border=True,verbose=False)
        v,f,_=sp.getMesh()
        e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1); _,cnt=np.unique(e,axis=0,return_counts=True)
        if (cnt==2).all(): break
    else:
        v,f=v0,f0                                   # 間引くと閉じなくなるときは、間引かない
    e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1); _,cnt=np.unique(e,axis=0,return_counts=True); bad=int((cnt!=2).sum())
    # 外向きに（体積が正）
    vol=np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6
    if vol<0: f=f[:,::-1]
    _,ai=kt.query(v); uu=us[ai]
    t=np.clip(np.interp(uu,arc,np.arange(len(arc))),0,len(arc)-1); i0=np.floor(t).astype(int); i1=np.minimum(i0+1,len(arc)-1); w1=t-i0; w0=1-w1
    Mv=w0[:,None,None]*Mp[np.array(vid)[i0]]+w1[:,None,None]*Mp[np.array(vid)[i1]]
    vr=np.einsum('vij,vj->vi',np.linalg.inv(Mv),np.c_[v,np.ones(len(v))])[:,:3]
    # 保存は soft_rigged.npz と同じ向き（generate_chameleon_ct_body.build_skin が読むときに反転して外向きになる）
    out[n+'__v']=m2ct(vr).astype(np.float32); out[n+'__f']=f[:,::-1].astype(np.int32)
    out[n+'__w_idx']=np.stack([[bidx[vnames[a]] for a in i0],[bidx[vnames[b]] for b in i1]],1).astype(np.int16)
    out[n+'__w_val']=np.stack([w0,w1],1).astype(np.float32)
    print(n,'verts',len(v),'faces',len(f),'volume mm3',round(abs(vol)/k**3,1),'non-manifold edges',bad)
out['names']=np.array(bones); out['organs']=np.array([n for n in names if n+'__v' in out])
np.savez_compressed('organs_rigged.npz',**out)
