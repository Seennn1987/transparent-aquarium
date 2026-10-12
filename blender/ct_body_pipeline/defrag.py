import numpy as np, scipy.ndimage as nd, sys
from scipy.spatial import cKDTree
B=np.load(sys.argv[1]); V=np.load('ct_ms50726_vol4.npz')['v']
# 標識の円板（V>=130 の大きな塊）とその周りは骨から外す
dl,n=nd.label(V>=130); sz=np.bincount(dl.ravel()); sz[0]=0; disc=dl==np.argmax(sz)
disc=nd.binary_dilation(disc,iterations=2); print('disc removed',int((disc&(B>0)).sum())); B[disc]=0
LAB=list(range(102,127))
for it in range(4):
    moved=0; objs=nd.find_objects(B)
    for l in LAB:
        if objs[l-1] is None: continue
        sl=tuple(slice(max(0,a.start-2),min(n_,a.stop+2)) for a,n_ in zip(objs[l-1],B.shape))
        sub=B[sl]; m=sub==l; lab,n=nd.label(m,np.ones((3,3,3)))
        if n<2: continue
        sz=np.bincount(lab.ravel()); sz[0]=0; main=np.argmax(sz)
        for c in range(1,n+1):
            if c==main: continue
            cm=lab==c; ring=nd.binary_dilation(cm,np.ones((3,3,3)))&~cm
            nb=sub[ring]; nb=nb[(nb>0)&(nb!=l)]
            if len(nb)==0: continue
            sub[cm]=np.bincount(nb).argmax(); moved+=1
        B[sl]=sub
    print('iter',it,'moved',moved)
    if moved==0: break
np.save(sys.argv[2],B)
