import numpy as np, scipy.ndimage as nd
from scipy.interpolate import splprep, splev
P=np.load('axis5.npy').astype(float)
# smooth & resample at 0.1 mm (half-res vox 0.208mm)
tck,u=splprep(P.T,s=len(P)*1.5)
L=np.cumsum(np.r_[0,np.linalg.norm(np.diff(P,axis=0),axis=1)])[-1]*0.208
n=int(L/0.1); uu=np.linspace(0,1,n); C=np.array(splev(uu,tck)).T; T=np.array(splev(uu,tck,der=1)).T; T/=np.linalg.norm(T,axis=1)[:,None]
np.save('axis5_s.npy',C); np.save('axis5_t.npy',T)
M=np.load('Mc.npy')  # full res
Cf=C*2+0.5; Tf=T
pts=np.argwhere(M).astype(np.float32)
from scipy.spatial import cKDTree
tr=cKDTree(Cf)
d,idx=tr.query(pts,distance_upper_bound=40)   # within 4 mm of axis
ok=np.isfinite(d)
area=np.bincount(idx[ok],minlength=len(C))
# body-only: within 1.6 mm
ok2=d<16; area2=np.bincount(idx[ok2],minlength=len(C))
np.save('prof.npy',np.stack([area,area2]))
print('length mm',L,len(C))
