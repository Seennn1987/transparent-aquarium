import numpy as np, scipy.ndimage as nd, sys
from scipy.spatial import cKDTree
from skimage.segmentation import watershed
T=int(sys.argv[1]) if len(sys.argv)>1 else 48
B=np.load('B_r4.npy'); X=np.load('ct_ms50726_vol4max.npz')['v']; IN=np.load('intruder.npy')
C=np.load('axis5_s.npy')*2+0.5; tr=cKDTree(C); J=np.load('J.npy'); s=np.arange(len(C))*0.1
vid=(np.searchsorted(J,s)+1).astype(np.int16)+100
P=np.argwhere((B>101)&(B<=126)); d,ii=tr.query(P); trunk=s[ii]<104.0
far=P[(d>20)&trunk]
lo=far.min(0)-4; hi=far.max(0)+5; sl=tuple(slice(a,b) for a,b in zip(lo,hi)); sh=hi-lo
Bc=B[sl]; Xc=X[sl]
other=(Bc>0)&~((Bc>101)&(Bc<=126))
dother=nd.distance_transform_edt(~other)
cand=(Xc>=T)&(Bc==0)&~IN[sl]&(dother>3)
cq=np.argwhere(cand); dc,ic=tr.query(cq+lo); ok=(dc>20)&(s[ic]<104.0)
cand[:]=False; cq=cq[ok]; cand[tuple(cq.T)]=True
F=np.zeros(sh,bool); F[tuple((far-lo).T)]=True
U=F|cand; lab,n=nd.label(U,np.ones((3,3,3)))
keep=np.zeros(n+1,bool); keep[np.unique(lab[F])]=True; keep[0]=False
add=cand&keep[lab]
# remove 1-voxel noise bumps: open the added set slightly, keep what stays connected to ribs
add=add&nd.binary_opening(add|F,np.ones((2,2,2)))
U=F|add; lab,n=nd.label(U,np.ones((3,3,3))); keep=np.zeros(n+1,bool); keep[np.unique(lab[F])]=True; keep[0]=False
U=U&keep[lab]
print('far',F.sum(),'added',(U&~F).sum())
band=P[(d>20)&(d<30)&trunk]; bi=ii[(d>20)&(d<30)&trunk]
I=nd.gaussian_filter(Xc.astype(np.float32),0.6); E=nd.distance_transform_edt(U)
elev=-(I/I[U].max()+0.5*E/E.max())
mk=np.zeros(sh,np.int16); mk[tuple((band-lo).T)]=vid[bi]
L=watershed(elev,mk,mask=U,connectivity=1)
un=U&(L==0)
if un.any():
    q=np.argwhere(L>0); _,jj=cKDTree(q).query(np.argwhere(un)); L[un]=L[tuple(q[jj].T)]
Bc=B[sl]; Bc[U]=L[U]; B[sl]=Bc
np.save('B_r5.npy',B); print('saved')
