# A5: 体の膜の体積（a5_S.npy）から、閉じた面を作る（Blender 座標、単位 m）
import hh_paths; hh_paths.cd_work()
import numpy as np, os
from scipy import ndimage as ndi
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0].replace("import numpy as np, sys, os","import numpy as np, sys, os"))
S=np.load(sys.argv[1] if len(sys.argv)>1 else 'a5_S.npy',mmap_mode='r'); NZ=S.shape[0]; Vs=[];Fs=[];n=0
for k0 in range(0,NZ-1,150):
    a=max(k0-8,0); b=min(k0+159,NZ)   # 前後に 8 断面ずつ重ねてぼかす（ぼかしを強めても、塊の継ぎ目で面がずれないように）
    blk=ndi.gaussian_filter(np.asarray(S[a:b]).astype(np.float32),float(os.environ.get('HH_MESH_SIGMA',1.0)))   # 2026-10-16 HH_MESH_SIGMA: 面を作る前のぼかし（格子の数、既定 1）
    blk=np.pad(blk,((0,0),(1,1),(1,1)))
    lo=k0-a; hi=min(lo+151,blk.shape[0])
    sub=blk[lo:hi]
    if sub.max()<0.5: continue
    v,f,_,_=marching_cubes(sub,level=0.5,allow_degenerate=False)
    v=v+np.array([k0,-1,-1]); Vs.append(v); Fs.append(f+n); n+=len(v)
Vv=np.concatenate(Vs); Fc=np.concatenate(Fs)
# 2026-10-16（プロデューサー「胴の表面に不自然な凹凸があったり、波打ったりしています」→「進めて」）: HH_MESH_TAUBIN=回数 で、面を作ったあとに
#  体積をほぼ保つならし（Taubin、λ 0.5・μ −0.53）をかける。0.735 mm の格子から作った面の木目のような段々を消す（既定 0 = かけない）
TAU=int(os.environ.get('HH_MESH_TAUBIN','0'))
if TAU:
    # 150 断面ごとの塊の継ぎ目で頂点が二重になっているので、先に一つにする（つながないと、ならしが継ぎ目で止まり、輪の筋が残る）
    key=np.round(Vv*1000).astype(np.int64); _,first,inv=np.unique(key,axis=0,return_index=True,return_inverse=True)
    Vv=Vv[first]; Fc=inv.ravel()[Fc]; Fc=Fc[(Fc[:,0]!=Fc[:,1])&(Fc[:,1]!=Fc[:,2])&(Fc[:,0]!=Fc[:,2])]
    from scipy import sparse
    nv=len(Vv); e=np.concatenate([Fc[:,[0,1]],Fc[:,[1,2]],Fc[:,[2,0]]]); e=np.concatenate([e,e[:,::-1]])
    Adj=sparse.csr_matrix((np.ones(len(e)),(e[:,0],e[:,1])),shape=(nv,nv)); Adj.data[:]=1.0
    deg=np.asarray(Adj.sum(1)).ravel(); Wm=sparse.diags(1/np.maximum(deg,1))@Adj
    for _ in range(TAU):
        for lam in (0.5,-0.53): Vv=Vv+lam*(Wm@Vv-Vv)
V=to_blender(Vv)
write_ply(f'{OUT}/HH_body.ply',V,Fc); print('body verts',len(V),'faces',len(Fc))
