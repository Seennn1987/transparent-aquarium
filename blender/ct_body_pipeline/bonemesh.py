import numpy as np, scipy.ndimage as nd, json
from skimage import measure
B=np.load('B.npy'); names=json.load(open('bone_names.json'))
ids=[i for i in np.unique(B) if i>0]
objs=nd.find_objects(B)
out={}; tot=0
for i in ids:
    sl=objs[i-1]
    if sl is None: continue
    sl=tuple(slice(max(0,a.start-3),min(n,a.stop+3)) for a,n in zip(sl,B.shape))
    sub=(B[sl]==i).astype(np.float32)
    F=nd.gaussian_filter(np.pad(sub,2),0.8)
    if F.max()<0.5: continue
    v,f,_,_=measure.marching_cubes(F,0.5)
    v=(v-2+np.array([a.start for a in sl]))*0.104   # mm, (z,y,x) CT
    nm=names[str(i)]; out[nm+'__v']=v.astype(np.float32); out[nm+'__f']=f.astype(np.int32); tot+=len(f)
np.savez_compressed('bones_raw.npz',**out); print('bones',len(out)//2,'faces',tot)
