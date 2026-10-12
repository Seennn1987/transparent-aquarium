import numpy as np, scipy.ndimage as nd
from skimage.segmentation import watershed
from scipy.spatial import cKDTree
W=np.load('W2.0.npy')
spinebits=[7,10,14,20,21,37,39,49,61,71,72,82,90,95,99]
Ah=np.isin(W,[5]+spinebits)
M=np.load('Mc.npy')
Af=np.zeros(M.shape,bool)
up=Ah.repeat(2,0).repeat(2,1).repeat(2,2)
sz=[min(a,b) for a,b in zip(M.shape,up.shape)]
Af[:sz[0],:sz[1],:sz[2]]=up[:sz[0],:sz[1],:sz[2]]
Af=nd.binary_dilation(Af,iterations=1)&M
del up
C=np.load('axis5_s.npy')*2+0.5; J=np.load('J.npy'); s=np.arange(len(C))*0.1; vid=(np.searchsorted(J,s)+1).astype(np.int16)
tr=cKDTree(C)
pts=np.argwhere(Af); d,i=tr.query(pts)
near=d<=21
far=np.zeros(M.shape,bool); far[tuple(pts[~near].T)]=True
for er in (1,2):
    fe=nd.binary_erosion(far,iterations=er)
    lab,n=nd.label(fe); print('erosion',er,'pieces',n, 'largest',np.sort(np.bincount(lab.ravel())[1:])[-5:])
fp=np.argwhere(fe); fl=lab[tuple(fp.T)]; fd,fi=tr.query(fp)
order=np.lexsort((fd,fl)); first=np.r_[True,fl[order][1:]!=fl[order][:-1]]
pv=np.zeros(n+1,np.int16); pv[fl[order][first]]=vid[fi[order][first]]
pmin=np.zeros(n+1); pmin[fl[order][first]]=fd[order][first]; pv[pmin>45]=0
mk=np.zeros(M.shape,np.int16); mk[tuple(pts[near].T)]=vid[i[near]]
sel=fe&(pv[lab]>0); mk[sel]=pv[lab][sel]
del lab,fe
L=watershed(np.zeros(M.shape,np.uint8),mk,mask=Af)
print('unassigned',(Af&(L==0)).sum())
np.save('vertLf.npy',L.astype(np.int16))
from PIL import Image
rng=np.random.default_rng(5); col=rng.integers(60,255,(int(L.max())+1,3)); col[0]=0
idx=np.argmax(L>0,axis=2); lb=np.take_along_axis(L,idx[...,None],2)[...,0]
Image.fromarray(col[lb].astype(np.uint8)).resize((lb.shape[1]*3//2,lb.shape[0]*3//2),Image.NEAREST).save('vert3_lat.png')
