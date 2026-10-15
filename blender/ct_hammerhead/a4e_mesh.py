# A4: 最終の座標の骨の体積から、マーチングキューブで面を作り、PLY に書く（Blender 座標: x=吻→尾, y=左右, z=背が上。単位 m）
import hh_paths; hh_paths.cd_work()
import numpy as np, sys, os
from skimage.measure import marching_cubes
VX=0.735; U0,V0=-180.0,-150.0
OUT=hh_paths.MESH
os.makedirs(OUT,exist_ok=True)
def to_blender(verts_zvu):       # verts in (iz, iv, iu) index units
    z=verts_zvu[:,0]*VX; v=V0+verts_zvu[:,1]*VX; u=U0+verts_zvu[:,2]*VX
    return np.stack([z,u,-v],1)/1000.0
def write_ply(path,V,Fc):
    with open(path,'wb') as f:
        f.write(f'ply\nformat binary_little_endian 1.0\nelement vertex {len(V)}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(Fc)}\nproperty list uchar int vertex_indices\nend_header\n'.encode())
        f.write(V.astype('<f4').tobytes())
        # skimage の marching_cubes の面は内向き（符号つき体積が負）なので、外向きに並べ替える（標本ページの道のりの計算は面の向きを使う）
        fa=np.empty(len(Fc),dtype=[('n','u1'),('i','<i4',3)]); fa['n']=3; fa['i']=Fc[:,::-1]; f.write(fa.tobytes())
def mesh_field(field,level,origin=(0,0,0)):
    v,f,_,_=marching_cubes(field,level=level,allow_degenerate=False)
    return v+np.array(origin),f
which=sys.argv[1]
if which in ('skel','spine'):
    F=np.load('a4_skel_field.npy' if which=='skel' else 'a4_spine_field.npy',mmap_mode='r'); NZ=F.shape[0]; Vs=[];Fs=[];n=0
    for k0 in range(0,NZ-1,160):
        k1=min(k0+161,NZ); blk=np.asarray(F[k0:k1]).astype(np.float32)
        if blk.max()<250: continue
        v,f=mesh_field(blk,250.0,(k0,0,0)); Vs.append(v); Fs.append(f+n); n+=len(v)
    V=to_blender(np.concatenate(Vs)); Fc=np.concatenate(Fs)
    write_ply(f'{OUT}/HH_skeleton.ply' if which=='skel' else f'{OUT}/HH_bone.ply',V,Fc); print(which,'verts',len(V),'faces',len(Fc))
else:
    for name in ('pect_L','pect_R','girdle','pelv_L','pelv_R','dfin1','dfin2','anal'):
        d=np.load(f'a4_{name}.npz'); v,f=mesh_field(d['field'],0.5,tuple(d['origin']))
        write_ply(f'{OUT}/HH_{name}.ply',to_blender(v),f); print(name,len(v),len(f))
