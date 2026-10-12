import numpy as np, scipy.ndimage as nd, sys
B=np.load(sys.argv[1])
objs=nd.find_objects(B)
tot=0; rows=[]
for l in range(102,127):
    sl=objs[l-1]; m=B[sl]==l
    lab,n=nd.label(m,np.ones((3,3,3))); sz=np.bincount(lab.ravel())[1:]
    big=sz.max(); fr=sz[sz<big]
    rows.append((l,n,int(big),int(fr.sum()),int((fr>200).sum())))
    tot+=fr.sum()
for r in rows: print(r)
print('fragment voxels',tot)
