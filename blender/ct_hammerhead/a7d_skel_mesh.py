# A7d: 骨格の面（HH_skeleton.ply）を、顎・歯・舌の弓を除いて作り直す（それらは a7c で細かい格子から別の部品にした）
import hh_paths; hh_paths.cd_work()
import numpy as np, sys
from scipy import ndimage as nd
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
d=np.load('a7_jaw_fine.npz'); o=d['origin']; G=float(d['step']); W=np.load('a7_jawlab.npy')
J=nd.binary_dilation(np.isin(W,(2,3,4,5,6)),iterations=3)
F=np.load('a4_skel_field.npy',mmap_mode='r'); NZ,NV,NU=F.shape; Vs=[];Fs=[];n=0
kend=int((o[0]+W.shape[0]*G)/VX)+2
for k0 in range(0,NZ-1,160):
    k1=min(k0+161,NZ); blk=np.asarray(F[k0:k1]).astype(np.float32)
    if k0<kend:
        kk,vv,uu=np.meshgrid(np.arange(k0,k1),np.arange(NV),np.arange(NU),indexing='ij')
        fz=np.round((kk*VX-o[0])/G).astype(int); fv=np.round((V0+vv*VX-o[1])/G).astype(int); fu=np.round((U0+uu*VX-o[2])/G).astype(int)
        ok=(fz>=0)&(fz<W.shape[0])&(fv>=0)&(fv<W.shape[1])&(fu>=0)&(fu<W.shape[2])
        jm=np.zeros(blk.shape,bool); jm[ok]=J[fz[ok],fv[ok],fu[ok]]
        blk[jm]=-1000; del kk,vv,uu,fz,fv,fu,ok
    if blk.max()<250: continue
    v,f=mesh_field(blk,250.0,(k0,0,0)); Vs.append(v); Fs.append(f+n); n+=len(v)
V=to_blender(np.concatenate(Vs)); Fc=np.concatenate(Fs)
write_ply(f'{OUT}/HH_skeleton.ply',V,Fc); print('skel verts',len(V),'faces',len(Fc))
