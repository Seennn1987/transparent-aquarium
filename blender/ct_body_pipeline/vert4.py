import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
L=np.load('vertLf.npy'); M=np.load('Mc.npy')
W=np.load('W2.0.npy')
spinebits=[7,10,14,20,21,37,39,49,61,71,72,82,90,95,99]
Ah=np.isin(W,[5]+spinebits)
Af=np.zeros(M.shape,bool); up=Ah.repeat(2,0).repeat(2,1).repeat(2,2); sz=[min(a,b) for a,b in zip(M.shape,up.shape)]
Af[:sz[0],:sz[1],:sz[2]]=up[:sz[0],:sz[1],:sz[2]]; Af=nd.binary_dilation(Af,iterations=1)&M; del up
U=Af&(L==0)
lab,n=nd.label(U,structure=np.ones((3,3,3))); print('unassigned comps',n)
C=np.load('axis5_s.npy')*2+0.5; J=np.load('J.npy'); s=np.arange(len(C))*0.1; vid=(np.searchsorted(J,s)+1).astype(np.int16)
tr=cKDTree(C)
up_=np.argwhere(U); ul=lab[tuple(up_.T)]; d,i=tr.query(up_)
order=np.lexsort((d,ul)); first=np.r_[True,ul[order][1:]!=ul[order][:-1]]
pv=np.zeros(n+1,np.int16); pv[ul[order][first]]=vid[i[order][first]]
L[tuple(up_.T)]=pv[ul]
print('remaining',(Af&(L==0)).sum())
np.save('vertLf.npy',L)
from PIL import Image
rng=np.random.default_rng(5); col=rng.integers(60,255,(int(L.max())+1,3)); col[0]=0
idx=np.argmax(L>0,axis=2); lb=np.take_along_axis(L,idx[...,None],2)[...,0]
Image.fromarray(col[lb].astype(np.uint8)).resize((lb.shape[1]*3//2,lb.shape[0]*3//2),Image.NEAREST).save('vert4_lat.png')
idx=np.argmax(L>0,axis=0); lb=np.take_along_axis(L,idx[None],0)[0]
Image.fromarray(col[lb].astype(np.uint8)).resize((lb.shape[1]*3//2,lb.shape[0]*3//2),Image.NEAREST).save('vert4_top.png')
