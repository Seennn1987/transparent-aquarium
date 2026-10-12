import numpy as np, scipy.ndimage as nd
from skimage.segmentation import watershed
from PIL import Image
m=np.load('m2.npy'); D=np.load('D2.npy')
for t in (1.5,2.0):
    K=D>=t
    mk,n=nd.label(K); s=nd.sum(K,mk,range(1,n+1))
    small=np.isin(mk,np.nonzero(s<8)[0]+1); mk[small]=0
    mk,n=nd.label(mk>0); print('t',t,'markers',n)
    W=watershed(-D,mk,mask=m)
    s=np.bincount(W.ravel())[1:]
    print(' sizes>200:',(s>200).sum(),' >1000:',(s>1000).sum(), ' largest',sorted(s)[-8:])
    np.save(f'W{t}.npy',W.astype(np.int32))
    rng=np.random.default_rng(1); col=rng.integers(60,255,(n+1,3)); col[0]=0
    # lateral projection colored by front-most label along x
    idx=np.argmax(W>0,axis=2); lab=np.take_along_axis(W,idx[...,None],2)[...,0]
    Image.fromarray(col[lab].astype(np.uint8)).resize((700,752),Image.NEAREST).save(f'seg{t}.png')
