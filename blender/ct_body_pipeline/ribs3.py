import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
from skimage.segmentation import watershed
B=np.load('B.npy')
C=np.load('axis5_s.npy')*2+0.5; tr=cKDTree(C); J=np.load('J.npy'); s=np.arange(len(C))*0.1; vid=(np.searchsorted(J,s)+1).astype(np.int16)+100
P=np.argwhere((B>101)&(B<=126)); d,ii=tr.query(P); trunk=s[ii]<103.5
far=P[(d>22)&trunk]; band=P[(d>22)&(d<40)&trunk]; bi=ii[(d>22)&(d<40)&trunk]
lo=far.min(0)-1; sh=far.max(0)-lo+2
F=np.zeros(sh,bool); F[tuple((far-lo).T)]=True
mk=np.zeros(sh,np.int16); mk[tuple((band-lo).T)]=vid[bi]
L=watershed(np.zeros(sh,np.uint8),mk,mask=F)
un=F&(L==0); print('unreached',un.sum())
lab,n=nd.label(un,structure=np.ones((3,3,3)))
if n:
    q=np.argwhere(L>0); qt=cKDTree(q); up=np.argwhere(un); ul=lab[tuple(up.T)]; dd,jj=qt.query(up)
    order=np.lexsort((dd,ul)); first=np.r_[True,ul[order][1:]!=ul[order][:-1]]
    cl=np.zeros(n+1,np.int16); cl[ul[order][first]]=L[tuple(q[jj[order][first]].T)]
    L[tuple(up.T)]=cl[ul]
B[tuple(far.T)]=L[tuple((far-lo).T)]
np.save('B.npy',B); print('done')
