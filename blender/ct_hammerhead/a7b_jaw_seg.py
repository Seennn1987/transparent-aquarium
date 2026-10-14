# A7b: 顎のまわりの細かい体積を、頭骨・上あご（口蓋方形軟骨）・下あご（メッケル軟骨）・舌の弓・歯に分ける。
#  断面を見て置いた種（左側 u<0 の座標。右は鏡映）から、骨の殻の中を流し込んで分ける（watershed、平らな像＝殻に沿った距離）。
#  歯（800 HU 超）は殻どうしをつなぐので先に外し、あとで近い顎に付ける
import numpy as np, matplotlib, sys; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import ndimage as nd
from skimage.segmentation import watershed
d=np.load('a7_jaw_fine.npz'); F=d['field']; o=d['origin']; G=float(d['step'])
def idx(z,u,v): return int(round((z-o[0])/G)),int(round((v-o[1])/G)),int(round((u-o[2])/G))
M=F>230
T=(F>800); T[:,:idx(0,0,10)[1]]=False
M2=M&~nd.binary_dilation(T,iterations=1)
SEEDS={1:[(56,-30,5),(70,-20,0),(90,0,-8),(80,-10,10),(100,-15,-5)],                  # 頭骨
       2:[(62,-15,22),(71,-37,14),(83,-38,13),(95,-41,12),(104,-40,9),(110,-33,6),(116,-33,6)],   # 上あご
       3:[(65,0,31),(74,-15,31),(86,-18,31),(98,-20,29),(110,-22,27),(118,-35,18),(122,-25,22)],   # 下あご
       4:[(107,-18,20),(113,-20,18),(118,-22,18)]}                                  # 舌の弓（角舌軟骨）
mk=np.zeros(F.shape,np.int32); zz=np.arange(F.shape[0]); 
r=int(2.0/G)
for l,pts in SEEDS.items():
    for z,u,v in pts:
        for uu in ((u,-u) if abs(u)>3 else (u,)):
            k,j,i=idx(z,uu,v); sl=(slice(k-r,k+r+1),slice(j-r,j+r+1),slice(i-r,i+r+1))
            mk[sl][M2[sl]]=l
if 'dorsal' not in sys.argv:
    dv=idx(0,0,2)[1]; mk[:, :dv][M2[:, :dv]]=1          # 背側（v<2）はすべて頭骨
W=watershed(np.zeros(F.shape,np.uint8),markers=mk,mask=M2,connectivity=1)
# 顎の前の端は 58 mm（歯の列は 60 mm から）。それより前へ流れ込んだ所（頭の翼の腹側の軟骨）は頭骨に戻す
kz=idx(58,0,0)[0]; Wf=W[:kz]; Wf[(Wf==2)|(Wf==3)|(Wf==4)]=1
# 歯: いちばん近い顎（上あご 2・下あご 3）に付ける。歯の値は 5（上の歯）・6（下の歯）
jaw=(W==2)|(W==3); dist,ind=nd.distance_transform_edt(~jaw,return_indices=True)
tz,tv,tu=np.nonzero(T); near=W[ind[0][tz,tv,tu],ind[1][tz,tv,tu],ind[2][tz,tv,tu]]
W2=W.copy(); W2[tz,tv,tu]=np.where(near==2,5,6)
# 歯の根元（650〜800 HU）も歯に含める: 800 HU 超の点から 1.4 mm 以内で 650 HU を超え、つながっている所。顎の殻（90% 点で約 500 HU）はほぼ入らない
for tl in (5,6):
    seed=W2==tl; R=nd.binary_dilation(seed,iterations=4)&(F>650); lb,_=nd.label(R); ks=np.unique(lb[seed]); ks=ks[ks>0]
    W2[np.isin(lb,ks)&(W2!=5)&(W2!=6)]=tl
np.save('a7_jawlab.npy',W2.astype(np.uint8))
for l in range(1,7): print(l,(W2==l).sum())
cols={1:(0.75,0.75,0.75),2:(0.2,0.5,1),3:(1,0.5,0.1),4:(0.2,0.8,0.2),5:(0.9,0,0.9),6:(0.8,0,0)}
fig,ax=plt.subplots(2,2,figsize=(22,13))
ext_s=[o[0],o[0]+F.shape[0]*G,o[1]+F.shape[1]*G,o[1]]; ext_t=[o[0],o[0]+F.shape[0]*G,o[2]+F.shape[2]*G,o[2]]
for a,axis,ext,order in ((ax[0,0],2,ext_s,(1,4,2,3,5,6)),(ax[0,1],1,ext_t,(1,4,3,2,6,5)),(ax[1,0],2,ext_s,(1,4,3,2,6,5))):
    img=np.ones((F.shape[0],F.shape[1] if axis==2 else F.shape[2],3))
    sel=slice(None) if a is not ax[1,0] else None
    src=W2 if a is not ax[1,0] else W2[:,:,:idx(0,-8,0)[2]]
    for l in order: img[(src==l).any(axis)]=cols[l]
    a.imshow(np.transpose(img,(1,0,2)),extent=ext,aspect='equal'); a.grid(alpha=.3)
ax[0,0].set_title('side all'); ax[0,1].set_title('top'); ax[1,0].set_title('side, left half only (u<-8)')
k=idx(90,0,0)[0]; s=W2[k]; img=np.ones(s.shape+(3,))
for l in cols: img[s==l]=cols[l]
ax[1,1].imshow(img,extent=[o[2],o[2]+s.shape[1]*G,o[1]+s.shape[0]*G,o[1]]); ax[1,1].set_title('z90')
plt.tight_layout(); plt.savefig('a7_jawseg.png',dpi=55)
