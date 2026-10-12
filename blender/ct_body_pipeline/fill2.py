import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
B=np.load('B.npy'); M=np.load('Mc.npy')
X=np.load('intruder.npy'); import scipy.ndimage as nd2; X=nd2.binary_dilation(X,iterations=3)
un=M&(B==0)&~X
B[X&(B==0)]=0
lab,n=nd.label(un,structure=np.ones((3,3,3))); print('comps',n)
P=np.argwhere(B>0); rng=np.random.default_rng(0); sub=P[rng.choice(len(P),min(800000,len(P)),replace=False)]
tr=cKDTree(sub); sv=B[tuple(sub.T)]
up=np.argwhere(un); ul=lab[tuple(up.T)]
d,i=tr.query(up)
# per comp: label of the nearest point overall (majority among closest)
order=np.lexsort((d,ul)); first=np.r_[True,ul[order][1:]!=ul[order][:-1]]
cl=np.zeros(n+1,np.int16); cd=np.zeros(n+1); cl[ul[order][first]]=sv[i[order][first]]; cd[ul[order][first]]=d[order][first]
cl[cd>15]=0   # farther than 1.5mm -> drop (intruder/noise)
B[tuple(up.T)]=cl[ul]
print('dropped vox',(cl[ul]==0).sum())
np.save('B.npy',B)
from PIL import Image
rng=np.random.default_rng(7); col=rng.integers(60,255,(int(B.max())+1,3)); col[0]=0
for nm,ax in (('lat',2),('top',0)):
    idx=np.argmax(B>0,axis=ax); lb=np.take_along_axis(B,np.expand_dims(idx,ax),ax).squeeze(ax)
    Image.fromarray(col[lb].astype(np.uint8)).save(f'B_{nm}.png')
