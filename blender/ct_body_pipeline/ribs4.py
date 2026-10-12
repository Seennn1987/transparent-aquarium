import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
from skimage.segmentation import watershed
B=np.load('B.npy'); V=np.load('ct_ms50726_vol4.npz')['v']
C=np.load('axis5_s.npy')*2+0.5; tr=cKDTree(C); J=np.load('J.npy'); s=np.arange(len(C))*0.1
vid=(np.searchsorted(J,s)+1).astype(np.int16)+100
P=np.argwhere((B>101)&(B<=126)); d,ii=tr.query(P); trunk=s[ii]<104.0
D0,D1=float(__import__('sys').argv[1]),float(__import__('sys').argv[2])
far=P[(d>D0)&trunk]; band=P[(d>D0)&(d<D1)&trunk]; bi=ii[(d>D0)&(d<D1)&trunk]
lo=far.min(0)-1; sh=far.max(0)-lo+2
F=np.zeros(sh,bool); F[tuple((far-lo).T)]=True
sl=tuple(slice(a,a+b) for a,b in zip(lo,sh))
I=nd.gaussian_filter(V[sl].astype(np.float32),0.6)
E=nd.distance_transform_edt(F)
elev=-(I/I[F].max()+0.5*E/E.max())
mk=np.zeros(sh,np.int16); mk[tuple((band-lo).T)]=vid[bi]
L=watershed(elev,mk,mask=F,connectivity=1)
print('unreached',(F&(L==0)).sum())
un=F&(L==0)
if un.any():
    q=np.argwhere(L>0); _,jj=cKDTree(q).query(np.argwhere(un)); L[un]=L[tuple(q[jj].T)]
B[tuple(far.T)]=L[tuple((far-lo).T)]
np.save('B_r4.npy',B)
# check image: lateral (project along x) and ventral (along y?) using label colors
rng=np.random.default_rng(3); col=rng.integers(60,255,(400,3)).astype(np.uint8); col[0]=0
from PIL import Image
for ax,nm in ((2,'lat'),(1,'top')):
    sub=np.where((B>101)&(B<=130),B,0)
    # take label at max depth (first nonzero along axis)
    nz=sub!=0; idx=nz.argmax(ax); lab=np.take_along_axis(sub,np.expand_dims(idx,ax),ax).squeeze(ax)
    Image.fromarray(col[lab]).save(f'r4_{nm}.png')
