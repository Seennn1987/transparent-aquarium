# A7a: 顎のまわり（最終の座標で吻端から 40〜125 mm、左右 ±60 mm、背腹 -15〜50 mm）を 0.35 mm の格子で作り直す。
#  逆写像・頭の鏡映・骨にしない塊の消し方は a4_final_volume.py と同じ
import numpy as np, json, sys
from scipy.ndimage import map_coordinates, binary_dilation
exec(open('a7_probe.py').read())
ZC=int(300)  # 元の CT の 0〜150 mm
C=np.array(C[:ZC]); L=np.asarray(np.load('skel_lab.npy',mmap_mode='r')[:ZC]); sizes=np.load('skel_sizes.npy')
DROP={2670,3867,784,827,833,1341,3064,3149,3077,3067,1546,4513,4302}
okl=np.zeros(len(sizes)+1,bool); okl[1:]=sizes>=100
for d in DROP: okl[d]=False
bad=binary_dilation((L>0)&(~okl[L])); C[bad&(C>-200)]=-200
G=0.35; Z0j,Z1j,U0j,U1j,V0j,V1j=40.0,140.0,-60.0,60.0,-15.0,50.0
zs=np.arange(Z0j,Z1j,G); us=np.arange(U0j,U1j,G); vs=np.arange(V0j,V1j,G)
out=np.zeros((len(zs),len(vs),len(us)),np.int16)
VV,UU=np.meshgrid(vs,us,indexing='ij')
for i,z in enumerate(zs):
    Z_=np.full(UU.size,z); U_=UU.ravel(); V_=VV.ravel()
    zr,y,x=inv(Z_,U_,V_); val=map_coordinates(C,[zr,y,x],order=1,cval=-1000,prefilter=False)
    hm=(Z_<142)&(U_<-6)
    zr2,y2,x2=inv(Z_[hm],-U_[hm],V_[hm]); vm=map_coordinates(C,[zr2,y2,x2],order=1,cval=-1000,prefilter=False)
    w=np.clip((-U_[hm]-6)/12,0,1); w=w*w*(3-2*w); val[hm]=w*vm+(1-w)*val[hm]
    out[i]=val.reshape(VV.shape).astype(np.int16)
np.savez_compressed('a7_jaw_fine.npz',field=out,origin=np.array([Z0j,V0j,U0j]),step=G)
print(out.shape, (out>900).sum(), (out>250).sum())
