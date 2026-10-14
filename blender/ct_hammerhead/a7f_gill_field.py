# A7f: エラのまわり（最終の座標で 100〜250 mm、左右 ±75 mm、背腹 -25〜60 mm）を 0.5 mm の格子で作る。
#  小さな塊（100 ボクセル未満）も消さずに入れ、別に「小さな塊だった所」の印も作る（エラの骨のかけらを見るため）
import numpy as np, json
from scipy.ndimage import map_coordinates, binary_dilation
exec(open('a7_probe.py').read())
z_lo=int(40/0.5); z_hi=int(300/0.5)   # 元の CT の 40〜300 mm
C=np.array(C[:z_hi]); L=np.asarray(np.load('skel_lab.npy',mmap_mode='r')[:z_hi]); sizes=np.load('skel_sizes.npy')
DROP={2670,3867,784,827,1341,3064,3149,3077,3067,1546,4513,4302}   # 833（肩帯）は残す
bad=np.zeros(len(sizes)+1,bool)
for dd in DROP: bad[dd]=True
C[binary_dilation(bad[L])&(C>-200)]=-200
small=np.zeros(len(sizes)+1,bool); small[1:]=sizes<100
SM=small[L].astype(np.float32)
G=0.5; Z0g,Z1g,U0g,U1g,V0g,V1g=100.0,250.0,-75.0,75.0,-25.0,60.0
zs=np.arange(Z0g,Z1g,G); us=np.arange(U0g,U1g,G); vs=np.arange(V0g,V1g,G)
out=np.zeros((len(zs),len(vs),len(us)),np.int16); osm=np.zeros(out.shape,np.uint8)
VV,UU=np.meshgrid(vs,us,indexing='ij')
for i,z in enumerate(zs):
    Z_=np.full(UU.size,z); U_=UU.ravel(); V_=VV.ravel()
    zr,y,x=inv(Z_,U_,V_)
    out[i]=map_coordinates(C,[zr,y,x],order=1,cval=-1000,prefilter=False).reshape(VV.shape)
    osm[i]=(map_coordinates(SM,[zr,y,x],order=0,cval=0)>0.5).reshape(VV.shape)
np.savez_compressed('a7_gill_field.npz',field=out,small=osm,origin=np.array([Z0g,V0g,U0g]),step=G)
print(out.shape,(out>250).sum(),((out>250)&(osm>0)).sum())
