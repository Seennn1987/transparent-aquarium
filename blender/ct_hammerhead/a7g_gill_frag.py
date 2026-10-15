# A7g: エラのまわりの骨のかけら（小さな塊も含む）を面にして見る（HH_gillfrag.ply）
import hh_paths; hh_paths.cd_work()
import numpy as np
from scipy import ndimage as nd
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
d=np.load('a7_gill_field.npz'); F=d['field'].astype(np.float32); o=d['origin']; G=float(d['step'])
zz=o[0]+np.arange(F.shape[0])*G; vv=o[1]+np.arange(F.shape[1])*G; uu=o[2]+np.arange(F.shape[2])*G
Z,V,U=np.meshgrid(zz,vv,uu,indexing='ij')
spine=(np.abs(U)<9)&(V<9)
F[spine]=-1000; F[Z<118]=-1000
m=F>250; lab,n=nd.label(m); sz=nd.sum(m,lab,range(1,n+1)); ok=np.zeros(n+1,bool); ok[1:]=sz>=8
F[~ok[lab]]=-1000
v,f,_,_=marching_cubes(np.pad(F,1,constant_values=-1000),250,allow_degenerate=False); v-=1
P=np.stack([o[0]+v[:,0]*G,o[2]+v[:,2]*G,-(o[1]+v[:,1]*G)],1)/1000
write_ply(f'{OUT}/HH_gillfrag.ply',P,f); print(len(v),len(f))
