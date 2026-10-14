# A5: 体の膜の体積（a5_S.npy）から、閉じた面を作る（Blender 座標、単位 m）
import numpy as np, os
from scipy import ndimage as ndi
from skimage.measure import marching_cubes
exec(open('a4_mesh.py').read().split("which=sys.argv[1]")[0].replace("import numpy as np, sys, os","import numpy as np, sys, os"))
S=np.load(sys.argv[1] if len(sys.argv)>1 else 'a5_S.npy',mmap_mode='r'); NZ=S.shape[0]; Vs=[];Fs=[];n=0
for k0 in range(0,NZ-1,150):
    a=max(k0-3,0); b=min(k0+154,NZ)
    blk=ndi.gaussian_filter(np.asarray(S[a:b]).astype(np.float32),1.0)
    blk=np.pad(blk,((0,0),(1,1),(1,1)))
    lo=k0-a; hi=min(lo+151,blk.shape[0])
    sub=blk[lo:hi]
    if sub.max()<0.5: continue
    v,f,_,_=marching_cubes(sub,level=0.5,allow_degenerate=False)
    v=v+np.array([k0,-1,-1]); Vs.append(v); Fs.append(f+n); n+=len(v)
V=to_blender(np.concatenate(Vs)); Fc=np.concatenate(Fs)
write_ply(f'{OUT}/HH_body.ply',V,Fc); print('body verts',len(V),'faces',len(Fc))
