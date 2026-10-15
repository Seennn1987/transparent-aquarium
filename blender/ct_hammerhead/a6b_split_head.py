# A6: 骨格の面（HH_skeleton.ply）を、頭の軟骨（頭骨・顎・鰓弓。吻端から 200 mm より前に重心がある塊）と、
#  それ以外（ひれの骨・肩帯・尾の骨など）に分ける。参考の胚（Eames et al. 2007 Fig. 2A）では、頭の軟骨は
#  ひれの放射軟骨よりずっと濃く緑がかった青で、1 つの色の吸い方では両方を出せないため（計画書 第 9 節 A6）
import hh_paths; hh_paths.cd_work()
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
def load(p):
    f=open(p,'rb'); h=b''
    while not h.endswith(b'end_header\n'): h+=f.read(1)
    hs=h.decode(); nv=int(hs.split('element vertex ')[1].split()[0]); nf=int(hs.split('element face ')[1].split()[0])
    V=np.frombuffer(f.read(nv*12),'<f4').reshape(nv,3).copy(); F=np.frombuffer(f.read(nf*13),dtype=[('n','u1'),('i','<i4',3)])['i'].copy()
    return V,F
V,F=load(f'{OUT}/HH_skeleton.ply')
F=F[:,::-1]   # write_ply が並べ替えるので、読み込んだ面は元の向きへ戻しておく
key=np.round(V*1e6).astype(np.int64); _,inv=np.unique(key,axis=0,return_inverse=True); inv=inv.ravel()
Fm=inv[F]; n=inv.max()+1
A=coo_matrix((np.ones(len(Fm)*3),(np.r_[Fm[:,0],Fm[:,1],Fm[:,2]],np.r_[Fm[:,1],Fm[:,2],Fm[:,0]])),shape=(n,n))
nc,lab=connected_components(A,directed=False)
Vm=np.zeros((n,3)); Vm[inv]=V
fl=lab[Fm[:,0]]; cx=np.bincount(lab,weights=Vm[:,0],minlength=nc)/np.maximum(np.bincount(lab,minlength=nc),1)
head_comp=cx<0.200
fh=head_comp[fl]
for name,sel in (('HH_skel_head',fh),('HH_skel_rest',~fh)):
    Fs=Fm[sel]; used=np.unique(Fs); remap=-np.ones(n,int); remap[used]=np.arange(len(used))
    write_ply(f'{OUT}/{name}.ply',Vm[used],remap[Fs]); print(name,'faces',len(Fs))
print('components',nc,'head comps',int(head_comp.sum()))
