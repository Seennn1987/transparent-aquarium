import zipfile, io, numpy as np, sys, time
from PIL import Image
Z=zipfile.ZipFile(sys.argv[1]); names=sorted(n for n in Z.namelist() if n.lower().endswith(('.jpg','.jpeg')))
NZ,Y1,X0,X1=752,700,400,764
V=np.zeros((NZ,Y1,X1-X0),np.uint8); t=time.time()
for i in range(NZ):
    acc=None
    for j in range(4*i-1,4*i+3):
        if j<0 or j>=len(names): continue
        a=np.asarray(Image.open(io.BytesIO(Z.read(names[j]))).convert('L'))[:Y1*4,X0*4:X1*4].astype(np.uint16)
        a=(a[0::2,0::2]+a[1::2,0::2]+a[0::2,1::2]+a[1::2,1::2])//4      # 2x mean
        a=np.maximum.reduce([a[0::2,0::2],a[1::2,0::2],a[0::2,1::2],a[1::2,1::2]])  # 2x max
        acc=a if acc is None else np.maximum(acc,a)
    V[i]=acc
    if i%50==0: print(i,round(time.time()-t),flush=True)
np.savez_compressed('vol4max.npz',v=V); print('done',V.shape)
